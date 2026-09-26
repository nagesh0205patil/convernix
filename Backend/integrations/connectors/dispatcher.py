import logging
from .registry import get_connector_instance_handler
from integrations.models import ConnectorInstance, OutboxEvent

logger = logging.getLogger(__name__)


def dispatch_connector_event(outbox_event: OutboxEvent):
    """
    Evaluates active connector instances for the tenant and triggers relevant synchronization or notification pushes.
    """
    tenant = outbox_event.tenant
    event_type = outbox_event.event_type
    payload = outbox_event.payload or {}
    data = payload.get('data', payload)

    active_instances = ConnectorInstance.objects.filter(
        tenant=tenant,
        status='active'
    )

    for instance in active_instances:
        handler = get_connector_instance_handler(instance)
        if not handler:
            continue

        try:
            # Map event type to object
            if event_type.startswith('lead.'):
                handler.push('lead', data)
            elif event_type.startswith('contact.'):
                handler.push('contact', data)
            elif event_type.startswith('ticket.'):
                handler.push('ticket', data)
            elif event_type.startswith('message.'):
                handler.push('conversation', data)
        except Exception as exc:
            logger.error('Error dispatching event %s to connector %s: %s', event_type, instance.name, exc)

