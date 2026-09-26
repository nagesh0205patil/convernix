import logging
import uuid
from typing import Any, Dict, Optional
from django.db import transaction
from django.utils import timezone
from .models import OutboxEvent
from .events import DomainEvent

logger = logging.getLogger(__name__)


def emit_outbox_event(tenant, event_type: str, payload: Dict[str, Any], correlation_id: Optional[str] = None) -> OutboxEvent:
    """
    Inserts a standardized domain event into the Transactional Outbox.
    Must be called within or along with the business data transaction to ensure atomicity.
    """
    if not tenant:
        raise ValueError('Outbox event requires a valid tenant.')

    domain_event = DomainEvent.create(
        tenant_id=tenant.id,
        event_type=event_type,
        payload=payload,
        correlation_id=correlation_id,
    )

    outbox_record = OutboxEvent.objects.create(
        id=domain_event.id,
        tenant=tenant,
        event_type=domain_event.event_type,
        payload=domain_event.to_dict(),
        correlation_id=domain_event.correlation_id,
        status='pending',
    )

    logger.debug('Emitted outbox event %s for tenant=%s type=%s', outbox_record.id, tenant.id, event_type)
    return outbox_record


def publish_outbox_events_batch(limit: int = 50) -> int:
    """
    Scans for pending outbox events, dispatches them to webhook & connector listeners,
    and updates their status safely without re-processing duplicates.
    """
    pending_events = OutboxEvent.objects.filter(
        status='pending'
    ).select_related('tenant').order_by('created_at')[:limit]

    processed_count = 0
    from .webhooks import dispatch_webhook_event_for_outbox

    for event in pending_events:
        try:
            # Dispatch to configured tenant webhooks
            dispatch_webhook_event_for_outbox(event)

            # Dispatch to connector sync / event handlers
            from .connectors.dispatcher import dispatch_connector_event
            dispatch_connector_event(event)

            event.status = 'published'
            event.published_at = timezone.now()
            event.save(update_fields=['status', 'published_at'])
            processed_count += 1

        except Exception as exc:
            logger.error('Failed to publish outbox event %s: %s', event.id, exc)
            event.retry_count += 1
            event.error_message = str(exc)
            if event.retry_count >= 5:
                event.status = 'failed'
            event.save(update_fields=['retry_count', 'error_message', 'status'])

    return processed_count

