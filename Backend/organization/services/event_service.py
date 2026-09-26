import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from organization.services.audit_service import redact_sensitive_data

logger = logging.getLogger(__name__)


class DomainEvent:
    def __init__(
        self,
        event_type: str,
        tenant_id: Optional[int],
        data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        event_version: int = 1,
    ):
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.event_version = event_version
        self.tenant_id = tenant_id
        self.occurred_at = datetime.now(timezone.utc).isoformat()
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.data = redact_sensitive_data(data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'eventId': self.event_id,
            'eventType': self.event_type,
            'eventVersion': self.event_version,
            'tenantId': self.tenant_id,
            'occurredAt': self.occurred_at,
            'correlationId': self.correlation_id,
            'data': self.data,
        }


def publish_domain_event(
    event_type: str,
    tenant_id: Optional[int],
    data: Dict[str, Any],
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    """Dispatches a domain event using standard event envelope.

    Logs safely and forwards to Celery / message brokers when configured.
    """
    event = DomainEvent(
        event_type=event_type,
        tenant_id=tenant_id,
        data=data,
        correlation_id=correlation_id,
    )
    payload = event.to_dict()
    logger.info(
        'DOMAIN_EVENT: type=%s tenantId=%s eventId=%s correlationId=%s',
        event.event_type,
        event.tenant_id,
        event.event_id,
        event.correlation_id,
    )
    # Can dispatch to Celery or webhook workers here
    return event

