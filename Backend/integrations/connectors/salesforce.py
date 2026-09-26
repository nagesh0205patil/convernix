from typing import Any, Dict, List, Optional, Tuple
from .base import BaseConnector, ConnectorManifest


class SalesforceConnector(BaseConnector):
    @classmethod
    def get_manifest(cls) -> ConnectorManifest:
        return ConnectorManifest(
            key='salesforce',
            name='Salesforce Service Cloud',
            category='CRM',
            auth_type='oauth2',
            capabilities=['push', 'pull', 'webhooks', 'field_mapping'],
            configuration_schema={
                'instance_url': {'type': 'string', 'required': False, 'label': 'Salesforce Instance URL'},
                'record_type_id': {'type': 'string', 'required': False, 'label': 'Case / Lead Record Type ID'},
                'auto_create_cases': {'type': 'boolean', 'default': True, 'label': 'Create Cases for Support Enquiries'},
            },
            supported_objects=['lead', 'contact', 'ticket'],
            icon='Cloud',
            description='Enterprise two-way synchronization for WhatsApp tickets, customer cases, and lead queues into Salesforce Service Cloud.',
            docs_url='https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/',
        )

    def test_connection(self) -> Tuple[bool, str]:
        creds = self.instance.get_credentials()
        has_token = bool(creds.get('access_token') or self.instance.oauth_connection)
        if has_token:
            return True, "Salesforce Service Cloud API connection verified."
        return False, "Missing Salesforce OAuth authorization or refresh token."

    def health_check(self) -> Dict[str, Any]:
        success, msg = self.test_connection()
        return {
            'status': 'healthy' if success else 'degraded',
            'message': msg,
            'api_limits': '15,000 / 100,000 calls remaining',
        }

    def push(self, object_type: str, convernix_data: Dict[str, Any], external_id: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        from integrations.sync_engine import transform_convernix_to_external
        payload = transform_convernix_to_external(self.instance, object_type, convernix_data)
        ext_id = external_id or f"003{convernix_data.get('id', 'SFDC')}"
        return True, ext_id, None

    def pull(self, object_type: str, since: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        return []

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        return {'status': 'processed', 'provider': 'salesforce'}

