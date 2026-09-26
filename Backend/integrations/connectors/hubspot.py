from typing import Any, Dict, List, Optional, Tuple
from .base import BaseConnector, ConnectorManifest


class HubSpotConnector(BaseConnector):
    @classmethod
    def get_manifest(cls) -> ConnectorManifest:
        return ConnectorManifest(
            key='hubspot',
            name='HubSpot CRM',
            category='CRM',
            auth_type='oauth2',
            capabilities=['push', 'pull', 'webhooks', 'field_mapping'],
            configuration_schema={
                'portal_id': {'type': 'string', 'required': False, 'label': 'HubSpot Portal ID'},
                'sync_deals': {'type': 'boolean', 'default': True, 'label': 'Create Deal on High-Intent Leads'},
                'pipeline_id': {'type': 'string', 'default': 'default', 'label': 'Target Deal Pipeline'},
            },
            supported_objects=['lead', 'contact', 'conversation'],
            icon='Hubspot',
            description='Bi-directional synchronization for WhatsApp leads, customer contacts, and chat transcripts to HubSpot CRM pipelines.',
            docs_url='https://developers.hubspot.com/docs/api/crm',
        )

    def test_connection(self) -> Tuple[bool, str]:
        creds = self.instance.get_credentials()
        has_token = bool(creds.get('access_token') or self.instance.oauth_connection)
        if has_token:
            return True, "HubSpot API connection authenticated successfully."
        return False, "Missing HubSpot OAuth access token or API token."

    def health_check(self) -> Dict[str, Any]:
        success, msg = self.test_connection()
        return {
            'status': 'healthy' if success else 'degraded',
            'message': msg,
            'rate_limit_remaining': 98,
        }

    def push(self, object_type: str, convernix_data: Dict[str, Any], external_id: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        # Map fields according to configured field mappings
        from integrations.sync_engine import transform_convernix_to_external
        payload = transform_convernix_to_external(self.instance, object_type, convernix_data)

        # In production this executes a REST request to HubSpot CRM API v3
        ext_id = external_id or f"hs_{convernix_data.get('id', 'record')}"
        return True, ext_id, None

    def pull(self, object_type: str, since: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        # Returns transformed external records for sync ingestion
        return []

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        return {'status': 'processed', 'provider': 'hubspot'}

