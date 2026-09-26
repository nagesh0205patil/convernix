import logging
from typing import Any, Dict, List, Optional
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from crm.models import (
    Customer, Lead, LeadFollower, LeadStageHistory, LeadAssignmentHistory,
    Pipeline, PipelineStage
)
from crm.services.pipeline_service import PipelineService
from crm.services.activity_service import ActivityService
from organization.models import AuditLog
from organization.services.event_service import publish_domain_event
from integrations.outbox import emit_outbox_event

logger = logging.getLogger(__name__)


class LeadService:
    @classmethod
    @transaction.atomic
    def create_lead(
        cls,
        tenant,
        customer: Customer,
        data: Dict[str, Any],
        actor_user=None,
    ) -> Lead:
        """
        Creates a new Lead associated with a Customer in a designated Pipeline and Stage.
        """
        title = data.get('title', '')
        if not title:
            cust_name = customer.display_name or customer.plain_full_name or 'Lead'
            title = f'{cust_name} - Inbound Enquiry'

        # Resolve pipeline & stage
        pipeline_id = data.get('pipeline_id')
        pipeline = None
        if pipeline_id:
            pipeline = Pipeline.objects.filter(tenant=tenant, pipeline_id=pipeline_id, is_active=True).first()
        if not pipeline:
            pipeline = PipelineService.ensure_default_pipeline(tenant)

        stage_id = data.get('stage_id')
        stage = None
        if stage_id:
            stage = PipelineStage.objects.filter(tenant=tenant, pipeline=pipeline, stage_id=stage_id, is_active=True).first()
        if not stage:
            stage = PipelineService.get_initial_stage(pipeline)

        department = data.get('department')
        department_id = data.get('department_id')
        if department_id and not department:
            from whatsapp.models import Department
            department = Department.objects.filter(tenant=tenant, pk=department_id).first()

        owner_user = data.get('owner_user')
        owner_user_id = data.get('owner_user_id')
        if owner_user_id and not owner_user:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            owner_user = User.objects.filter(pk=owner_user_id).first()

        lead = Lead.objects.create(
            tenant=tenant,
            customer=customer,
            pipeline=pipeline,
            stage=stage,
            department=department,
            owner_user=owner_user,
            source=data.get('source', 'WHATSAPP'),
            priority=data.get('priority', 'MEDIUM'),
            status='OPEN' if not stage.is_terminal else stage.classification,
            title=title,
            estimated_value=data.get('estimated_value'),
            currency=data.get('currency', 'INR'),
            win_probability=data.get('win_probability', 0),
            last_contacted_at=timezone.now(),
        )

        # Record Stage History
        LeadStageHistory.objects.create(
            tenant=tenant,
            lead=lead,
            from_stage=None,
            to_stage=stage,
            actor_user=actor_user,
            actor_name=getattr(actor_user, 'get_full_name', lambda: '')() or getattr(actor_user, 'email', 'System'),
            reason='Initial lead creation',
        )

        # If owner was assigned at creation, record assignment history
        if owner_user or department:
            LeadAssignmentHistory.objects.create(
                tenant=tenant,
                lead=lead,
                from_owner=None,
                to_owner=owner_user,
                from_department=None,
                to_department=department,
                assigned_by=actor_user,
                assignment_method='MANUAL',
                reason='Initial assignment upon lead creation',
            )

        # Log Activity
        ActivityService.log_activity(
            tenant=tenant,
            customer=customer,
            lead=lead,
            activity_type='LEAD_CREATED',
            title='New Lead Created',
            description=f'Created lead "{lead.title}" in stage {stage.name}',
            actor_user=actor_user,
        )

        # Publish domain event & outbox
        event_payload = {
            'lead_id': str(lead.lead_id),
            'customer_id': str(customer.customer_id),
            'pipeline_id': str(pipeline.pipeline_id),
            'stage_id': str(stage.stage_id),
            'stage_name': stage.name,
            'title': lead.title,
            'owner_user_id': owner_user.id if owner_user else None,
            'department_id': department.id if department else None,
            'priority': lead.priority,
            'source': lead.source,
        }
        try:
            publish_domain_event(
                event_type='crm.lead.created',
                tenant_id=tenant.id,
                data=event_payload,
            )
            emit_outbox_event(
                tenant=tenant,
                event_type='crm.lead.created',
                payload=event_payload,
            )
        except Exception as exc:
            logger.warning('Failed to emit lead created event: %s', exc)

        return lead

    @classmethod
    @transaction.atomic
    def update_lead(
        cls,
        lead: Lead,
        data: Dict[str, Any],
        actor_user=None,
        client_version: Optional[int] = None,
    ) -> Lead:
        """
        Updates basic lead attributes with optimistic locking check.
        """
        if client_version is not None and lead.version != client_version:
            raise ValidationError({'detail': 'This lead was updated by another user. Please refresh and try again.', 'code': 'CONCURRENT_MODIFICATION'})

        update_fields = ['version', 'updated_at']

        if 'title' in data:
            lead.title = data['title']
            update_fields.append('title')

        if 'priority' in data:
            lead.priority = data['priority']
            update_fields.append('priority')

        if 'estimated_value' in data:
            lead.estimated_value = data['estimated_value']
            update_fields.append('estimated_value')

        if 'currency' in data:
            lead.currency = data['currency']
            update_fields.append('currency')

        if 'win_probability' in data:
            lead.win_probability = data['win_probability']
            update_fields.append('win_probability')

        lead.version += 1
        lead.save(update_fields=list(set(update_fields)))
        return lead

    @classmethod
    @transaction.atomic
    def transition_lead_stage(
        cls,
        lead: Lead,
        target_stage: PipelineStage,
        actor_user=None,
        reason: str = '',
        client_version: Optional[int] = None,
    ) -> Lead:
        """
        Transitions a lead to another stage within its pipeline.
        Enforces optimistic locking, records stage history, and sets status (OPEN/WON/LOST).
        """
        if client_version is not None and lead.version != client_version:
            raise ValidationError({
                'detail': 'Lead stage transition rejected due to concurrent modification. Please reload.',
                'code': 'CONCURRENT_MODIFICATION'
            })

        if target_stage.pipeline_id != lead.pipeline_id:
            raise ValidationError({
                'detail': 'Cannot transition to a stage belonging to a different pipeline.',
                'code': 'INVALID_STAGE_TRANSITION'
            })

        old_stage = lead.stage
        if old_stage.stage_id == target_stage.stage_id:
            return lead

        now = timezone.now()
        duration_seconds = int((now - lead.updated_at).total_seconds()) if lead.updated_at else 0

        # Update lead
        lead.stage = target_stage
        if target_stage.is_terminal:
            lead.status = target_stage.classification  # WON or LOST
            lead.closed_at = now
        else:
            lead.status = 'OPEN'
            lead.closed_at = None

        lead.version += 1
        lead.save(update_fields=['stage', 'status', 'closed_at', 'version', 'updated_at'])

        # Create Stage History
        actor_name = getattr(actor_user, 'get_full_name', lambda: '')() or getattr(actor_user, 'email', 'System')
        LeadStageHistory.objects.create(
            tenant=lead.tenant,
            lead=lead,
            from_stage=old_stage,
            to_stage=target_stage,
            actor_user=actor_user,
            actor_name=actor_name,
            reason=reason,
            duration_seconds=max(0, duration_seconds),
        )

        # Log Activity
        activity_type = 'STAGE_CHANGED'
        if target_stage.classification == 'WON':
            activity_type = 'LEAD_WON'
        elif target_stage.classification == 'LOST':
            activity_type = 'LEAD_LOST'

        ActivityService.log_activity(
            tenant=lead.tenant,
            customer=lead.customer,
            lead=lead,
            activity_type=activity_type,
            title=f'Stage moved to {target_stage.name}',
            description=f'Transitioned from {old_stage.name} to {target_stage.name}. Reason: {reason or "Stage movement"}',
            actor_user=actor_user,
            metadata={'from_stage': old_stage.name, 'to_stage': target_stage.name, 'reason': reason},
        )

        # Audit Log
        AuditLog.log(
            tenant=lead.tenant,
            actor_name=actor_name,
            actor_email=getattr(actor_user, 'email', ''),
            action='LEAD_STAGE_CHANGED',
            module='CRM',
            resource=f'Lead #{lead.lead_id}',
            metadata={'from_stage': old_stage.name, 'to_stage': target_stage.name, 'status': lead.status},
        )

        # Publish Events
        event_payload = {
            'lead_id': str(lead.lead_id),
            'customer_id': str(lead.customer_id),
            'from_stage_id': str(old_stage.stage_id),
            'from_stage_name': old_stage.name,
            'to_stage_id': str(target_stage.stage_id),
            'to_stage_name': target_stage.name,
            'status': lead.status,
            'actor_name': actor_name,
        }
        try:
            publish_domain_event(
                event_type='crm.lead.stage_changed',
                tenant_id=lead.tenant_id,
                data=event_payload,
            )
            if target_stage.classification == 'WON':
                publish_domain_event(event_type='crm.lead.won', tenant_id=lead.tenant_id, data=event_payload)
            elif target_stage.classification == 'LOST':
                publish_domain_event(event_type='crm.lead.lost', tenant_id=lead.tenant_id, data=event_payload)

            emit_outbox_event(
                tenant=lead.tenant,
                event_type='crm.lead.stage_changed',
                payload=event_payload,
            )
        except Exception as exc:
            logger.warning('Failed to emit lead stage event: %s', exc)

        return lead

    @classmethod
    @transaction.atomic
    def assign_lead(
        cls,
        lead: Lead,
        owner_user=None,
        department=None,
        assigned_by=None,
        method: str = 'MANUAL',
        reason: str = '',
        client_version: Optional[int] = None,
    ) -> Lead:
        """
        Assigns or reassigns lead owner and/or department.
        Records assignment history, logs activity, and emits domain events.
        """
        if client_version is not None and lead.version != client_version:
            raise ValidationError({
                'detail': 'Lead assignment rejected due to concurrent modification.',
                'code': 'CONCURRENT_MODIFICATION'
            })

        old_owner = lead.owner_user
        old_dept = lead.department

        lead.owner_user = owner_user
        if department is not None:
            lead.department = department

        lead.version += 1
        lead.save(update_fields=['owner_user', 'department', 'version', 'updated_at'])

        # Record Assignment History
        LeadAssignmentHistory.objects.create(
            tenant=lead.tenant,
            lead=lead,
            from_owner=old_owner,
            to_owner=owner_user,
            from_department=old_dept,
            to_department=lead.department,
            assigned_by=assigned_by,
            assignment_method=method,
            reason=reason,
        )

        actor_name = getattr(assigned_by, 'get_full_name', lambda: '')() or getattr(assigned_by, 'email', 'System')
        new_owner_name = getattr(owner_user, 'get_full_name', lambda: '')() or getattr(owner_user, 'email', 'Unassigned')

        # Log Activity
        is_reassign = old_owner is not None
        activity_type = 'OWNER_CHANGED' if is_reassign else 'OWNER_ASSIGNED'
        title = f'Lead assigned to {new_owner_name}' if owner_user else 'Lead unassigned'
        ActivityService.log_activity(
            tenant=lead.tenant,
            customer=lead.customer,
            lead=lead,
            activity_type=activity_type,
            title=title,
            description=f'Assigned via {method}. Reason: {reason or "Ownership update"}',
            actor_user=assigned_by,
            metadata={
                'from_owner_id': old_owner.id if old_owner else None,
                'to_owner_id': owner_user.id if owner_user else None,
                'department_id': lead.department.id if lead.department else None,
            },
        )

        # Audit Log
        AuditLog.log(
            tenant=lead.tenant,
            actor_name=actor_name,
            actor_email=getattr(assigned_by, 'email', ''),
            action='LEAD_REASSIGNED' if is_reassign else 'LEAD_ASSIGNED',
            module='CRM',
            resource=f'Lead #{lead.lead_id}',
            metadata={'owner': new_owner_name, 'department': lead.department.name if lead.department else 'None'},
        )

        # Publish Events
        event_type = 'crm.lead.reassigned' if is_reassign else 'crm.lead.assigned'
        event_payload = {
            'lead_id': str(lead.lead_id),
            'customer_id': str(lead.customer_id),
            'owner_user_id': owner_user.id if owner_user else None,
            'owner_name': new_owner_name,
            'department_id': lead.department.id if lead.department else None,
            'assigned_by': actor_name,
        }
        try:
            publish_domain_event(event_type=event_type, tenant_id=lead.tenant_id, data=event_payload)
            emit_outbox_event(tenant=lead.tenant, event_type=event_type, payload=event_payload)
        except Exception:
            pass

        return lead

    @classmethod
    def add_follower(cls, lead: Lead, user) -> bool:
        _, created = LeadFollower.objects.get_or_create(tenant=lead.tenant, lead=lead, user=user)
        return created

    @classmethod
    def remove_follower(cls, lead: Lead, user) -> bool:
        deleted, _ = LeadFollower.objects.filter(tenant=lead.tenant, lead=lead, user=user).delete()
        return deleted > 0
