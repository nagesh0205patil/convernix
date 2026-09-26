import logging
import uuid
from typing import Any, Dict, List, Optional
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class IncidentService:
    """Security Event and Incident Response Workflow Orchestrator."""

    @classmethod
    @transaction.atomic
    def create_incident(
        cls,
        title: str,
        description: str,
        category: str = 'AUTHENTICATION',
        severity: str = 'MEDIUM',
        tenant: Optional[Any] = None,
        affected_resources: Optional[List[str]] = None,
        actor: Optional[Any] = None,
    ) -> Any:
        """Logs and triages a new security event / incident."""
        from organization.models import SecurityIncident, AuditLog

        incident_id = f'INC-{timezone.now().strftime("%Y%m%d")}-{uuid.uuid4().hex[:6].upper()}'
        incident = SecurityIncident.objects.create(
            incident_id=incident_id,
            tenant=tenant,
            title=title,
            description=description,
            category=category,
            severity=severity,
            status='DETECTED',
            affected_resources=affected_resources or [],
            assigned_owner=actor if getattr(actor, 'is_authenticated', False) else None,
            detected_at=timezone.now(),
        )

        AuditLog.objects.create(
            tenant=tenant,
            actor_name=getattr(actor, 'username', 'system'),
            actor_email=getattr(actor, 'email', 'security@convernix.internal'),
            action='SECURITY_INCIDENT_CREATED',
            module='Security',
            resource=f'Incident #{incident_id}: {title}',
            status='Success',
            metadata={
                'incident_id': incident_id,
                'category': category,
                'severity': severity,
            }
        )

        logger.warning('SECURITY INCIDENT CREATED [%s]: %s (Severity: %s)', incident_id, title, severity)
        return incident

    @classmethod
    @transaction.atomic
    def update_incident_status(
        cls,
        incident_id: str,
        status: str,
        containment_steps: str = '',
        investigation_findings: str = '',
        remediation_notes: str = '',
        post_incident_review: str = '',
        actor: Optional[Any] = None,
    ) -> Any:
        """Progresses incident response through triage, containment, remediation, and closure."""
        from organization.models import SecurityIncident, AuditLog

        incident = SecurityIncident.objects.get(incident_id=incident_id)
        incident.status = status

        now = timezone.now()
        if status == 'CONTAINED' and not incident.contained_at:
            incident.contained_at = now
        elif status in ('REMEDIATED', 'CLOSED') and not incident.resolved_at:
            incident.resolved_at = now

        if containment_steps:
            incident.containment_steps = containment_steps
        if investigation_findings:
            incident.investigation_findings = investigation_findings
        if remediation_notes:
            incident.remediation_notes = remediation_notes
        if post_incident_review:
            incident.post_incident_review = post_incident_review

        incident.save()

        AuditLog.objects.create(
            tenant=incident.tenant,
            actor_name=getattr(actor, 'username', 'system'),
            actor_email=getattr(actor, 'email', 'security@convernix.internal'),
            action='SECURITY_INCIDENT_UPDATED',
            module='Security',
            resource=f'Incident #{incident_id} -> {status}',
            status='Success',
            metadata={'incident_id': incident_id, 'new_status': status}
        )

        return incident

