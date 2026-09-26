import logging
from typing import Any, Dict, Optional
from django.db import transaction
from crm.models import Activity, Customer, Lead
from organization.services.event_service import publish_domain_event
from integrations.outbox import emit_outbox_event

logger = logging.getLogger(__name__)


class ActivityService:
    @classmethod
    @transaction.atomic
    def log_activity(
        cls,
        tenant,
        customer: Customer,
        activity_type: str,
        title: str,
        description: str = '',
        lead: Optional[Lead] = None,
        actor_user=None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Activity:
        """
        Creates an Activity entry for a Customer / Lead timeline and publishes domain events.
        """
        actor_name = ''
        if actor_user:
            actor_name = getattr(actor_user, 'get_full_name', lambda: '')() or getattr(actor_user, 'username', '') or getattr(actor_user, 'email', 'System')
        else:
            actor_name = 'System'

        activity = Activity.objects.create(
            tenant=tenant,
            customer=customer,
            lead=lead,
            activity_type=activity_type,
            title=title,
            description=description,
            actor_user=actor_user,
            actor_name=actor_name,
            metadata=metadata or {},
        )

        event_data = {
            'activity_id': str(activity.activity_id),
            'customer_id': str(customer.customer_id),
            'lead_id': str(lead.lead_id) if lead else None,
            'activity_type': activity_type,
            'title': title,
            'actor_name': actor_name,
        }

        # Publish domain event
        try:
            publish_domain_event(
                event_type='crm.activity.created',
                tenant_id=tenant.id,
                data=event_data,
            )
        except Exception as exc:
            logger.warning('Failed to publish crm.activity.created domain event: %s', exc)

        # Emit transactional outbox
        try:
            emit_outbox_event(
                tenant=tenant,
                event_type='crm.activity.created',
                payload=event_data,
            )
        except Exception as exc:
            logger.warning('Failed to emit outbox event for activity: %s', exc)

        return activity
