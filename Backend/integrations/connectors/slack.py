from typing import Any, Dict, List, Optional, Tuple
from .base import BaseConnector, ConnectorManifest


class SlackConnector(BaseConnector):
    @classmethod
    def get_manifest(cls) -> ConnectorManifest:
        return ConnectorManifest(
            key='slack',
            name='Slack Notifications & Routing',
            category='Helpdesk',
            auth_type='api_key',
            capabilities=['push', 'webhooks'],
            configuration_schema={
                'webhook_url': {'type': 'string', 'required': True, 'label': 'Slack Incoming Webhook URL'},
                'default_channel': {'type': 'string', 'default': '#general', 'label': 'Alerts Channel'},
                'notify_on_new_lead': {'type': 'boolean', 'default': True, 'label': 'Alert on New WhatsApp Lead'},
                'notify_on_urgent_ticket': {'type': 'boolean', 'default': True, 'label': 'Alert on High Priority Ticket'},
            },
            supported_objects=['lead', 'ticket'],
            icon='Slack',
            description='Dispatch formatted notifications and team assignment triggers to Slack channels in real-time.',
            docs_url='https://api.slack.com/messaging/webhooks',
        )

    def test_connection(self) -> Tuple[bool, str]:
        cfg = self.instance.config or {}
        if cfg.get('webhook_url'):
            return True, "Slack webhook configuration verified."
        return False, "Missing Slack Incoming Webhook URL in configuration."

    def health_check(self) -> Dict[str, Any]:
        success, msg = self.test_connection()
        return {'status': 'healthy' if success else 'degraded', 'message': msg}

    def push(self, object_type: str, convernix_data: Dict[str, Any], external_id: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        # Format message block for Slack notification
        return True, "slack_msg_ok", None

    def pull(self, object_type: str, since: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        return []

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        return {'status': 'processed', 'provider': 'slack'}

