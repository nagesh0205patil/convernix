import logging
import re
from typing import Optional
from users.permissions import has_tenant_permission

logger = logging.getLogger(__name__)


class MaskingService:
    """Enterprise permission-aware Data Masking & Reveal Service."""

    @staticmethod
    def mask_phone(phone: Optional[str]) -> str:
        """
        Mask phone number for users without lead.phone.view permission.
        e.g. '+919876543210' -> '+91 ******3210'
             '9876543210'    -> '******3210'
        """
        if not phone:
            return ''
        cleaned = str(phone).strip()
        if len(cleaned) <= 4:
            return '****'
        
        # Preserve country code if present (+91 or +1)
        if cleaned.startswith('+') and len(cleaned) > 6:
            prefix = cleaned[:3]  # e.g. +91 or +1 (approx)
            suffix = cleaned[-4:]
            return f'{prefix} ******{suffix}'
        
        return f'******{cleaned[-4:]}'

    @staticmethod
    def mask_email(email: Optional[str]) -> str:
        """
        Mask email address for users without lead.email.view permission.
        e.g. 'rahul.patil@example.com' -> 'r*****l@example.com'
        """
        if not email or '@' not in email:
            return ''
        parts = email.split('@', 1)
        name_part, domain_part = parts[0], parts[1]
        if len(name_part) <= 2:
            masked_name = name_part[0] + '***'
        else:
            masked_name = name_part[0] + '*****' + name_part[-1]
        return f'{masked_name}@{domain_part}'

    @classmethod
    def can_view_unmasked_phone(cls, user, tenant) -> bool:
        """Determine if authenticated user is authorized to view unmasked phone numbers."""
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return has_tenant_permission(user, tenant, 'lead.phone.view') or has_tenant_permission(user, tenant, 'customer.phone.reveal')

    @classmethod
    def can_view_unmasked_email(cls, user, tenant) -> bool:
        """Determine if authenticated user is authorized to view unmasked email addresses."""
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return has_tenant_permission(user, tenant, 'lead.email.view')

    @classmethod
    def audit_phone_reveal(cls, user, tenant, resource_id: str, ip_address: str = '127.0.0.1'):
        """Log an immutable audit trail when an authorized user reveals a masked customer phone number."""
        from organization.models import AuditLog
        AuditLog.objects.create(
            tenant=tenant,
            actor_name=getattr(user, 'get_full_name', lambda: '')() or getattr(user, 'username', 'user'),
            actor_email=getattr(user, 'email', ''),
            action='PHONE_REVEALED',
            module='DataPrivacy',
            resource=f'Customer/Lead #{resource_id}',
            ip_address=ip_address,
            status='Success',
            metadata={'action': 'unmask_phone', 'resource_id': str(resource_id)}
        )

    @classmethod
    def audit_email_reveal(cls, user, tenant, resource_id: str, ip_address: str = '127.0.0.1'):
        """Log an immutable audit trail when an authorized user reveals a masked customer email."""
        from organization.models import AuditLog
        AuditLog.objects.create(
            tenant=tenant,
            actor_name=getattr(user, 'get_full_name', lambda: '')() or getattr(user, 'username', 'user'),
            actor_email=getattr(user, 'email', ''),
            action='CUSTOMER_EMAIL_REVEALED',
            module='DataPrivacy',
            resource=f'Customer/Lead #{resource_id}',
            ip_address=ip_address,
            status='Success',
            metadata={'action': 'unmask_email', 'resource_id': str(resource_id)}
        )

