import hashlib
import secrets
from datetime import timedelta
from typing import Any, List, Optional, Tuple
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from users.models import Tenant
from organization.models import SupportAccessRequest, SupportAccessSession
from organization.services.audit_service import log_admin_action
from organization.services.event_service import publish_domain_event


class SupportAccessService:
    """Controls time-limited, scoped platform technician elevation to tenant scopes."""

    @classmethod
    def request_access(
        cls,
        platform_user: Any,
        tenant: Tenant,
        reason: str,
        ticket_reference: str,
        requested_scopes: List[str],
        duration_minutes: int = 60,
    ) -> SupportAccessRequest:
        """Creates a time-bounded support access elevation request."""
        if not platform_user.is_superuser and not platform_user.is_staff:
            raise PermissionDenied('Only platform staff can request support access elevation.')

        if duration_minutes > 480:
            raise ValidationError({'duration': 'Support access duration cannot exceed 8 hours.'})

        expires_at = timezone.now() + timedelta(minutes=duration_minutes)

        req = SupportAccessRequest.objects.create(
            tenant=tenant,
            platform_user=platform_user,
            reason=reason,
            ticket_reference=ticket_reference,
            requested_scopes=requested_scopes or ['read_only'],
            status='approved',  # In auto-approval for authorized staff or can be multi-party
            approved_by=platform_user,
            approved_at=timezone.now(),
            expires_at=expires_at,
        )

        log_admin_action(
            tenant=tenant,
            actor_name=platform_user.get_full_name() or platform_user.email,
            actor_email=platform_user.email,
            action='Platform staff requested support access elevation',
            module='Security',
            resource=f'Support Access Ticket #{ticket_reference}',
            status='Success',
            metadata={'scopes': requested_scopes, 'expires_at': str(expires_at), 'reason': reason},
        )

        publish_domain_event(
            event_type='support_access.requested',
            tenant_id=tenant.id,
            data={'request_id': req.id, 'platform_user': platform_user.email, 'ticket': ticket_reference},
        )

        return req

    @classmethod
    def start_session(cls, request_instance: SupportAccessRequest) -> Tuple[SupportAccessSession, str]:
        """Starts an active support session and generates a single-use session token."""
        if request_instance.status != 'approved':
            raise ValidationError({'status': 'Support access request has not been approved.'})

        if request_instance.expires_at < timezone.now():
            request_instance.status = 'expired'
            request_instance.save(update_fields=['status'])
            raise ValidationError({'status': 'Support access request has expired.'})

        raw_token = f'cvx_sup_{secrets.token_hex(24)}'
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

        # Invalidate any prior active session for this request
        SupportAccessSession.objects.filter(request=request_instance).update(is_active=False, ended_at=timezone.now())

        session = SupportAccessSession.objects.create(
            request=request_instance,
            session_token_hash=token_hash,
            is_active=True,
            started_at=timezone.now(),
        )

        log_admin_action(
            tenant=request_instance.tenant,
            actor_name=request_instance.platform_user.get_full_name() or request_instance.platform_user.email,
            actor_email=request_instance.platform_user.email,
            action='Elevated support access session started',
            module='Security',
            resource=f'Session #{session.id}',
            status='Success',
        )

        return session, raw_token

    @classmethod
    def verify_active_support_session(cls, user: Any, tenant: Tenant) -> Optional[SupportAccessSession]:
        """Verifies if an active, unexpired support session exists for this user and tenant."""
        if not user or not user.is_authenticated or not (user.is_superuser or user.is_staff):
            return None

        session = SupportAccessSession.objects.filter(
            request__platform_user=user,
            request__tenant=tenant,
            request__status='approved',
            is_active=True,
            request__expires_at__gt=timezone.now(),
        ).select_related('request').first()

        return session

    @classmethod
    def end_session(cls, session: SupportAccessSession):
        """Terminates an elevated support session immediately."""
        session.is_active = False
        session.ended_at = timezone.now()
        session.save(update_fields=['is_active', 'ended_at'])

        log_admin_action(
            tenant=session.request.tenant,
            actor_name=session.request.platform_user.get_full_name() or session.request.platform_user.email,
            actor_email=session.request.platform_user.email,
            action='Elevated support access session ended',
            module='Security',
            resource=f'Session #{session.id}',
            status='Success',
        )

