import logging
import os
from typing import Any, Dict, List, Optional
from django.db import transaction
from django.utils import timezone

from .crypto_service import (
    clear_crypto_cache,
    decrypt_tenant_data,
    encrypt_tenant_data,
    get_or_create_tenant_key_metadata,
)
from .kms_service import get_kms_provider, KmsError

logger = logging.getLogger(__name__)


class TenantKeyService:
    """Enterprise Key Management & Rotation Service."""

    @classmethod
    @transaction.atomic
    def provision_tenant_keys(cls, tenant) -> Any:
        """
        Provision initial 256-bit DEK and search keys wrapped with KMS.
        If provisioning fails, raises KmsError to prevent tenant activation.
        """
        try:
            return get_or_create_tenant_key_metadata(tenant)
        except Exception as exc:
            logger.critical('CRITICAL: Tenant key provisioning failed for tenant=%s: %s', getattr(tenant, 'id', 'unknown'), exc)
            raise KmsError(f'Key provisioning failed for tenant {getattr(tenant, "id", "")}') from exc

    @classmethod
    @transaction.atomic
    def rotate_tenant_key(cls, tenant, actor=None) -> Dict[str, Any]:
        """
        Performs cryptographic key rotation for a tenant:
        1. Generates new 256-bit DEK v(N+1).
        2. Wraps new DEK using KMS envelope.
        3. Marks previous key version as RETIRED in history.
        4. Activates v(N+1) for all subsequent writes.
        5. Preserves v1..vN for decrypting historical records.
        6. Logs KEY_ROTATED audit event.
        """
        from organization.models import TenantKeyMetadata, TenantKeyVersionHistory, AuditLog

        meta = get_or_create_tenant_key_metadata(tenant)
        old_version = meta.key_version
        new_version = old_version + 1

        kms = get_kms_provider()
        context = {'tenant_id': tenant.id, 'slug': getattr(tenant, 'slug', '')}

        # 1. Generate new 256-bit DEK
        new_dek = os.urandom(32)
        wrapped_new_dek = kms.wrap_key(new_dek, context)

        # 2. Retire current active key in history
        TenantKeyVersionHistory.objects.filter(
            tenant=tenant,
            key_version=old_version,
        ).update(
            status='RETIRED',
            retired_at=timezone.now(),
        )

        # 3. Create new active key history record
        TenantKeyVersionHistory.objects.create(
            tenant=tenant,
            key_version=new_version,
            wrapped_dek=wrapped_new_dek,
            wrapped_search_key=meta.wrapped_search_key,
            kms_key_id=meta.kms_key_id,
            kms_provider=meta.kms_provider,
            status='ACTIVE',
            rotated_by=actor if getattr(actor, 'is_authenticated', False) else None,
        )

        # 4. Update primary metadata pointer
        meta.key_version = new_version
        meta.wrapped_dek = wrapped_new_dek
        meta.last_rotated_at = timezone.now()
        meta.save(update_fields=['key_version', 'wrapped_dek', 'last_rotated_at'])

        # 5. Invalidate runtime key cache
        clear_crypto_cache(tenant.id)

        # 6. Audit rotation
        AuditLog.objects.create(
            tenant=tenant,
            actor_name=getattr(actor, 'get_full_name', lambda: '')() or getattr(actor, 'username', 'system'),
            actor_email=getattr(actor, 'email', '') if actor else 'system',
            action='KEY_ROTATED',
            module='Security',
            resource=f'Tenant Key v{old_version} -> v{new_version}',
            status='Success',
            metadata={
                'old_version': old_version,
                'new_version': new_version,
                'algorithm': 'AES-256-GCM-KMS',
                'kms_provider': meta.kms_provider,
            }
        )

        logger.info('Tenant encryption key rotated successfully for tenant=%s (v%s -> v%s)', tenant.id, old_version, new_version)
        return {
            'tenant_id': tenant.id,
            'old_version': old_version,
            'new_version': new_version,
            'rotated_at': meta.last_rotated_at.isoformat(),
            'status': 'ACTIVE',
        }

    @classmethod
    def reencrypt_tenant_records(cls, tenant, batch_size: int = 100) -> Dict[str, int]:
        """
        Background job to safely re-encrypt historical records under the latest key version.
        Does not disrupt existing reads or writes.
        """
        from whatsapp.models import Customer, Lead, WhatsAppMessage, WhatsAppConfiguration

        reencrypted_count = 0
        meta = get_or_create_tenant_key_metadata(tenant)
        latest_prefix = f'cvx:v{meta.key_version}:'

        # 1. Customers
        for cust in Customer.objects.filter(tenant=tenant):
            updated = False
            for field in ('full_name', 'whatsapp_number', 'email', 'organization_name'):
                val = getattr(cust, field, '')
                if val and not val.startswith(latest_prefix):
                    plain = decrypt_tenant_data(tenant, val)
                    setattr(cust, field, encrypt_tenant_data(tenant, plain))
                    updated = True
            if updated:
                cust.save()
                reencrypted_count += 1

        # 2. Leads
        for lead in Lead.objects.filter(business_number__tenant=tenant):
            updated = False
            for field in ('customer_name', 'phone_number', 'customer_email', 'message'):
                val = getattr(lead, field, '')
                if val and not val.startswith(latest_prefix):
                    plain = decrypt_tenant_data(tenant, val)
                    setattr(lead, field, encrypt_tenant_data(tenant, plain))
                    updated = True
            if updated:
                lead.save()
                reencrypted_count += 1

        # 3. WhatsApp Messages
        for msg in WhatsAppMessage.objects.filter(customer__tenant=tenant):
            if msg.content and not msg.content.startswith(latest_prefix):
                plain = decrypt_tenant_data(tenant, msg.content)
                msg.content = encrypt_tenant_data(tenant, plain)
                msg.save(update_fields=['content'])
                reencrypted_count += 1

        return {'reencrypted_records': reencrypted_count}


def rotate_tenant_key(tenant, rotated_by=None):
    """Convenience top-level wrapper for TenantKeyService.rotate_tenant_key."""
    return TenantKeyService.rotate_tenant_key(tenant, actor=rotated_by)
