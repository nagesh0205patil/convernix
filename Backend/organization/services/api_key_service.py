import hashlib
import secrets
from typing import Any, List, Optional, Tuple
from django.utils import timezone
from users.models import Tenant
from organization.models import TenantApiKey
from organization.services.audit_service import log_admin_action


class ApiKeyService:
    """Cryptographic API key generation, hashing, and authorization validator."""

    PREFIX = 'cvx_live_'

    @classmethod
    def generate_api_key(
        cls,
        tenant: Tenant,
        name: str,
        scopes: List[str],
        created_by: Optional[Any] = None,
        expires_in_days: Optional[int] = None,
    ) -> Tuple[TenantApiKey, str]:
        """Generates a secure API key.

        Returns (TenantApiKey_instance, plaintext_key).
        The plaintext_key is NEVER persisted and only returned once at creation.
        """
        random_bytes = secrets.token_hex(24)
        plaintext_key = f'{cls.PREFIX}{random_bytes}'

        prefix_identifier = plaintext_key[:16]
        key_hash = hashlib.sha256(plaintext_key.encode('utf-8')).hexdigest()

        expires_at = timezone.now() + timezone.timedelta(days=expires_in_days) if expires_in_days else None

        key_instance = TenantApiKey.objects.create(
            tenant=tenant,
            name=name,
            key_prefix=prefix_identifier,
            key_hash=key_hash,
            scopes=scopes or ['*'],
            is_active=True,
            expires_at=expires_at,
            created_by=created_by,
        )

        log_admin_action(
            tenant=tenant,
            actor_name=created_by.get_full_name() or created_by.email if created_by else 'Admin',
            actor_email=created_by.email if created_by else '',
            action='Created API Key',
            module='Security',
            resource=f'{name} ({prefix_identifier}...)',
            status='Success',
            metadata={'scopes': scopes, 'expires_at': str(expires_at)},
        )

        return key_instance, plaintext_key

    @classmethod
    def validate_api_key(cls, plaintext_key: str, required_scope: Optional[str] = None) -> Optional[TenantApiKey]:
        """Validates a plaintext API key against the database hash.

        Updates last_used_at timestamp.
        """
        if not plaintext_key or not plaintext_key.startswith(cls.PREFIX):
            return None

        key_hash = hashlib.sha256(plaintext_key.encode('utf-8')).hexdigest()
        key_instance = TenantApiKey.objects.filter(key_hash=key_hash, is_active=True).select_related('tenant').first()

        if not key_instance:
            return None

        # Check expiration
        if key_instance.expires_at and key_instance.expires_at < timezone.now():
            return None

        # Check tenant status
        if not key_instance.tenant or key_instance.tenant.is_suspended or key_instance.tenant.is_deleted:
            return None

        # Check scope
        if required_scope and '*' not in key_instance.scopes and required_scope not in key_instance.scopes:
            return None

        # Touch last used
        key_instance.last_used_at = timezone.now()
        key_instance.save(update_fields=['last_used_at'])

        return key_instance

    @classmethod
    def revoke_api_key(cls, key_instance: TenantApiKey, revoked_by: Optional[Any] = None) -> TenantApiKey:
        """Revokes an API key immediately."""
        key_instance.is_active = False
        key_instance.revoked_at = timezone.now()
        key_instance.save(update_fields=['is_active', 'revoked_at'])

        log_admin_action(
            tenant=key_instance.tenant,
            actor_name=revoked_by.get_full_name() or revoked_by.email if revoked_by else 'Admin',
            actor_email=revoked_by.email if revoked_by else '',
            action='Revoked API Key',
            module='Security',
            resource=f'{key_instance.name} ({key_instance.key_prefix}...)',
            status='Success',
        )
        return key_instance

