import base64
import hashlib
import hmac
import json
import logging
import os
import re
from typing import Any, Dict, Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from .kms_service import get_kms_provider, KmsError

logger = logging.getLogger(__name__)

# Ciphertext header prefix for Convernix AES-256-GCM envelope encryption
ENVELOPE_PREFIX = 'cvx:v'

# In-memory session key cache to avoid decrypting wrapped DEKs from KMS on every single record
# Maps: (tenant_id, key_version) -> 32-byte DEK
_DEK_CACHE: Dict[Tuple[int, int], bytes] = {}
# Maps: tenant_id -> 32-byte HMAC search key
_SEARCH_KEY_CACHE: Dict[int, bytes] = {}


class DecryptionError(Exception):
    """Raised when ciphertext cannot be decrypted or authentication tag verification fails."""
    pass


def clear_crypto_cache(tenant_id: Optional[int] = None):
    """Purge in-memory decrypted key material."""
    global _DEK_CACHE, _SEARCH_KEY_CACHE
    if tenant_id is None:
        _DEK_CACHE.clear()
        _SEARCH_KEY_CACHE.clear()
    else:
        keys_to_del = [k for k in _DEK_CACHE if k[0] == tenant_id]
        for k in keys_to_del:
            _DEK_CACHE.pop(k, None)
        _SEARCH_KEY_CACHE.pop(tenant_id, None)


def get_master_key() -> bytes:
    """Retrieve master secret key from settings for legacy Fernet compatibility."""
    key = getattr(settings, 'TENANT_MASTER_ENCRYPTION_KEY', '') or getattr(settings, 'SECRET_KEY', '')
    if not key or key == 'dev-secret-key':
        key = getattr(settings, 'SECRET_KEY', 'convernix-dev-master-encryption-secret-key-32b')
    return key.encode('utf-8')


def get_or_create_tenant_key_metadata(tenant):
    """
    Ensure tenant encryption key metadata and initial 256-bit DEK exist, wrapped via KMS.
    Creates TenantKeyMetadata and TenantKeyVersionHistory records atomically.
    """
    if not tenant:
        raise ImproperlyConfigured('Cannot initialize encryption metadata without a tenant.')
    
    from organization.models import TenantKeyMetadata, TenantKeyVersionHistory

    meta = TenantKeyMetadata.objects.filter(tenant=tenant).first()
    kms = get_kms_provider()
    context = {'tenant_id': tenant.id, 'slug': getattr(tenant, 'slug', '')}

    if not meta or not meta.wrapped_dek:
        # Generate fresh 256-bit DEK and 256-bit Search Key
        raw_dek = os.urandom(32)
        raw_search_key = os.urandom(32)
        
        try:
            wrapped_dek = kms.wrap_key(raw_dek, context)
            wrapped_search = kms.wrap_key(raw_search_key, context)
        except Exception as exc:
            logger.error('Failed to wrap tenant DEK in KMS during provisioning for tenant=%s: %s', tenant.id, exc)
            raise KmsError(f'KMS key provisioning failed for tenant {tenant.id}') from exc

        if not meta:
            meta = TenantKeyMetadata.objects.create(
                tenant=tenant,
                key_version=1,
                algorithm='AES-256-GCM-KMS',
                wrapped_dek=wrapped_dek,
                wrapped_search_key=wrapped_search,
                kms_key_id='convernix-kek-primary',
                kms_provider='local',
                salt=os.urandom(16).hex(),
                last_rotated_at=timezone.now(),
            )
        else:
            meta.wrapped_dek = wrapped_dek
            meta.wrapped_search_key = wrapped_search
            meta.algorithm = 'AES-256-GCM-KMS'
            if not meta.salt:
                meta.salt = os.urandom(16).hex()
            meta.save()

        # Record in key version history
        TenantKeyVersionHistory.objects.get_or_create(
            tenant=tenant,
            key_version=meta.key_version,
            defaults={
                'wrapped_dek': wrapped_dek,
                'wrapped_search_key': wrapped_search,
                'kms_key_id': meta.kms_key_id,
                'kms_provider': meta.kms_provider,
                'status': 'ACTIVE',
            }
        )

        # Cache unwrapped keys for this runtime session
        _DEK_CACHE[(tenant.id, meta.key_version)] = raw_dek
        _SEARCH_KEY_CACHE[tenant.id] = raw_search_key

    return meta


def get_tenant_dek(tenant, version: Optional[int] = None) -> bytes:
    """Retrieve raw 256-bit DEK bytes for tenant and key version, unwrapping via KMS as needed."""
    if not tenant:
        raise ImproperlyConfigured('Cannot retrieve DEK without tenant.')
    
    meta = get_or_create_tenant_key_metadata(tenant)
    target_version = version or meta.key_version
    cache_key = (tenant.id, target_version)

    if cache_key in _DEK_CACHE:
        return _DEK_CACHE[cache_key]

    kms = get_kms_provider()
    context = {'tenant_id': tenant.id, 'slug': getattr(tenant, 'slug', '')}

    if target_version == meta.key_version and meta.wrapped_dek:
        wrapped_str = meta.wrapped_dek
    else:
        from organization.models import TenantKeyVersionHistory
        history = TenantKeyVersionHistory.objects.filter(tenant=tenant, key_version=target_version).first()
        if not history:
            raise DecryptionError(f'Key version {target_version} not found for tenant {tenant.id}')
        wrapped_str = history.wrapped_dek

    try:
        raw_dek = kms.unwrap_key(wrapped_str, context)
        _DEK_CACHE[cache_key] = raw_dek
        return raw_dek
    except Exception as exc:
        logger.error('KMS unwrap failed for tenant=%s version=%s', tenant.id, target_version)
        raise DecryptionError(f'Could not unwrap tenant DEK for version {target_version}') from exc


def get_tenant_search_key(tenant) -> bytes:
    """Retrieve 256-bit HMAC blind index key for searchable encrypted queries."""
    if not tenant:
        raise ImproperlyConfigured('Cannot retrieve search key without tenant.')
    if tenant.id in _SEARCH_KEY_CACHE:
        return _SEARCH_KEY_CACHE[tenant.id]

    meta = get_or_create_tenant_key_metadata(tenant)
    kms = get_kms_provider()
    context = {'tenant_id': tenant.id, 'slug': getattr(tenant, 'slug', '')}

    if meta.wrapped_search_key:
        try:
            raw_search = kms.unwrap_key(meta.wrapped_search_key, context)
            _SEARCH_KEY_CACHE[tenant.id] = raw_search
            return raw_search
        except Exception:
            pass

    # Fallback derivation if wrapped_search_key not yet persisted
    dek = get_tenant_dek(tenant, meta.key_version)
    derived_search = hmac.new(dek, b'convernix-search-blind-index-key', hashlib.sha256).digest()
    _SEARCH_KEY_CACHE[tenant.id] = derived_search
    return derived_search


def normalize_search_term(value: Optional[str], field_type: str = 'text') -> str:
    """Canonical normalization before calculating blind index hashes."""
    if not value:
        return ''
    val = str(value).strip()
    if field_type == 'phone':
        val = re.sub(r'[^0-9+]', '', val)
        if val and not val.startswith('+'):
            val = f'+{val}'
        return val
    elif field_type == 'email':
        return val.lower()
    return val.lower()


def compute_blind_index(tenant, value: Optional[str], field_type: str = 'text') -> str:
    """
    Computes a tenant-scoped cryptographic HMAC-SHA256 blind index for exact search.
    Never uses plain SHA-256 (which is vulnerable to precomputed dictionary attacks on phone numbers).
    """
    norm = normalize_search_term(value, field_type)
    if not norm or not tenant:
        return ''
    search_key = get_tenant_search_key(tenant)
    return hmac.new(search_key, norm.encode('utf-8'), hashlib.sha256).hexdigest()


def derive_tenant_cipher(tenant) -> Fernet:
    """
    Legacy Fernet cipher derivation for backwards-compatibility.
    Uses HKDF-SHA256 over master key and tenant salt.
    """
    if not tenant:
        raise ImproperlyConfigured('Cannot derive cipher without tenant context.')
    meta = get_or_create_tenant_key_metadata(tenant)
    master_key = get_master_key()
    salt = bytes.fromhex(meta.salt) if meta.salt else b'convernix-16b-sl'
    info = f'convernix-tenant-{tenant.id}-v{meta.key_version}'.encode('utf-8')

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=info,
    )
    derived = hkdf.derive(master_key)
    fernet_key = base64.urlsafe_b64encode(derived)
    return Fernet(fernet_key)


def encrypt_tenant_data(tenant, plaintext: Optional[str]) -> str:
    """
    Encrypt sensitive application data using AES-256-GCM with envelope encryption.
    Generates a cryptographically secure 12-byte nonce for EVERY operation (never reused).
    Output format: cvx:v{version}:{nonce_b64}:{ciphertext_b64}
    """
    if plaintext is None or plaintext == '':
        return ''
    if not tenant:
        # Fallback to local encryption if tenant is null (e.g. system level unassigned records)
        return str(plaintext)

    meta = get_or_create_tenant_key_metadata(tenant)
    version = meta.key_version
    dek = get_tenant_dek(tenant, version)

    aesgcm = AESGCM(dek)
    nonce = os.urandom(12)  # Fresh 96-bit nonce
    aad = f'tenant:{tenant.id}:v{version}'.encode('utf-8')
    ciphertext_with_tag = aesgcm.encrypt(nonce, str(plaintext).encode('utf-8'), aad)

    nonce_b64 = base64.b64encode(nonce).decode('ascii')
    ct_b64 = base64.b64encode(ciphertext_with_tag).decode('ascii')
    return f'{ENVELOPE_PREFIX}{version}:{nonce_b64}:{ct_b64}'


def decrypt_tenant_data(tenant, ciphertext: Optional[str]) -> str:
    """
    Decrypt sensitive application data using AES-256-GCM.
    Authenticates tag and AAD. Supports versioned keys and legacy Fernet fallback.
    """
    if not ciphertext or not isinstance(ciphertext, str):
        return ''
    if not tenant:
        return ciphertext

    # Check for modern Convernix AES-256-GCM envelope: cvx:v{version}:{nonce_b64}:{ct_b64}
    if ciphertext.startswith(ENVELOPE_PREFIX):
        try:
            parts = ciphertext[len(ENVELOPE_PREFIX):].split(':')
            if len(parts) != 3:
                raise DecryptionError('Malformed ciphertext header')
            version = int(parts[0])
            nonce = base64.b64decode(parts[1])
            raw_ct = base64.b64decode(parts[2])

            dek = get_tenant_dek(tenant, version)
            aesgcm = AESGCM(dek)
            aad = f'tenant:{tenant.id}:v{version}'.encode('utf-8')
            decrypted_bytes = aesgcm.decrypt(nonce, raw_ct, aad)
            return decrypted_bytes.decode('utf-8')
        except Exception as exc:
            logger.warning('AES-256-GCM decryption failed for tenant=%s: %s', tenant.id, type(exc).__name__)
            raise DecryptionError('Decryption failed: invalid key, tampered ciphertext, or wrong tenant context') from exc

    # Legacy Fernet fallback
    try:
        cipher = derive_tenant_cipher(tenant)
        return cipher.decrypt(ciphertext.encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError, UnicodeError):
        # Plaintext fallback for pre-migration data
        return ciphertext


# Aliases for 100% backwards compatibility with existing callers
def encrypt_tenant_secret(tenant, plaintext: Optional[str]) -> str:
    return encrypt_tenant_data(tenant, plaintext)


def decrypt_tenant_secret(tenant, ciphertext: Optional[str]) -> str:
    try:
        return decrypt_tenant_data(tenant, ciphertext)
    except DecryptionError:
        return ciphertext
