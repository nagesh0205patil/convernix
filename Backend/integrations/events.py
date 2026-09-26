import dataclasses
import uuid
from typing import Any, Dict, Optional
from django.utils import timezone


EVENT_LEAD_CREATED = 'lead.created'
EVENT_LEAD_UPDATED = 'lead.updated'
EVENT_LEAD_ASSIGNED = 'lead.assigned'

EVENT_CONTACT_CREATED = 'contact.created'
EVENT_CONTACT_UPDATED = 'contact.updated'

EVENT_CONVERSATION_CREATED = 'conversation.created'
EVENT_CONVERSATION_ASSIGNED = 'conversation.assigned'
EVENT_CONVERSATION_CLOSED = 'conversation.closed'

EVENT_MESSAGE_RECEIVED = 'message.received'
EVENT_MESSAGE_SENT = 'message.sent'
EVENT_MESSAGE_DELIVERED = 'message.delivered'
EVENT_MESSAGE_READ = 'message.read'
EVENT_MESSAGE_FAILED = 'message.failed'

EVENT_TICKET_CREATED = 'ticket.created'
EVENT_TICKET_UPDATED = 'ticket.updated'
EVENT_TICKET_RESOLVED = 'ticket.resolved'

EVENT_CAMPAIGN_CREATED = 'campaign.created'
EVENT_CAMPAIGN_STARTED = 'campaign.started'
EVENT_CAMPAIGN_COMPLETED = 'campaign.completed'

EVENT_WORKFLOW_STARTED = 'workflow.started'
EVENT_WORKFLOW_COMPLETED = 'workflow.completed'
EVENT_WORKFLOW_FAILED = 'workflow.failed'

ALL_DOMAIN_EVENTS = [
    EVENT_LEAD_CREATED,
    EVENT_LEAD_UPDATED,
    EVENT_LEAD_ASSIGNED,
    EVENT_CONTACT_CREATED,
    EVENT_CONTACT_UPDATED,
    EVENT_CONVERSATION_CREATED,
    EVENT_CONVERSATION_ASSIGNED,
    EVENT_CONVERSATION_CLOSED,
    EVENT_MESSAGE_RECEIVED,
    EVENT_MESSAGE_SENT,
    EVENT_MESSAGE_DELIVERED,
    EVENT_MESSAGE_READ,
    EVENT_MESSAGE_FAILED,
    EVENT_TICKET_CREATED,
    EVENT_TICKET_UPDATED,
    EVENT_TICKET_RESOLVED,
    EVENT_CAMPAIGN_CREATED,
    EVENT_CAMPAIGN_STARTED,
    EVENT_CAMPAIGN_COMPLETED,
    EVENT_WORKFLOW_STARTED,
    EVENT_WORKFLOW_COMPLETED,
    EVENT_WORKFLOW_FAILED,
]


@dataclasses.dataclass(frozen=True)
class DomainEvent:
    id: str
    event_type: str
    tenant_id: int
    payload: Dict[str, Any]
    timestamp: str
    correlation_id: str
    api_version: str = 'v1'

    @classmethod
    def create(cls, tenant_id: int, event_type: str, payload: Dict[str, Any], correlation_id: Optional[str] = None):
        return cls(
            id=str(uuid.uuid4()),
            event_type=event_type,
            tenant_id=tenant_id,
            payload=payload,
            timestamp=timezone.now().isoformat(),
            correlation_id=correlation_id or str(uuid.uuid4()),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'event': self.event_type,
            'tenant_id': self.tenant_id,
            'timestamp': self.timestamp,
            'correlation_id': self.correlation_id,
            'api_version': self.api_version,
            'data': self.payload,
        }

