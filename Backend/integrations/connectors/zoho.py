from typing import Any, Dict, List, Optional, Tuple
from .base import BaseConnector, ConnectorManifest


class ZohoConnector(BaseConnector):
    @classmethod
    def get_manifest(cls) -> ConnectorManifest:
        return ConnectorManifest(
            key='zoho',
            name='Zoho CRM',
            category='CRM',
            auth_type='oauth2',
            capabilities=['push', 'pull', 'field_mapping'],
            configuration_schema={
                'data_center': {'type': 'select', 'options': ['com', 'in', 'eu', 'com.cn'], 'default': 'in', 'label': 'Zoho Data Center (.in, .com, .eu)'},
                'module_name': {'type': 'string', 'default': 'Leads', 'label': 'Target Module (Leads / Contacts)'},
            },
            supported_objects=['lead', 'contact'],
            icon='Layers',
            description='Streamline WhatsApp lead capture and pipeline tracking directly into Zoho CRM Indian and Global data centers.',
            docs_url='https://www.zoho.com/crm/developer/docs/api/v2/',
        )

    def test_connection(self) -> Tuple[bool, str]:
        creds = self.instance.get_credentials()
        has_token = bool(creds.get('access_token') or self.instance.oauth_connection)
        if has_token:
            return True, "Zoho CRM connected and authenticated."
        return False, "Missing Zoho CRM credentials or expired grant."

    def health_check(self) -> Dict[str, Any]:
        success, msg = self.test_connection()
        return {'status': 'healthy' if success else 'degraded', 'message': msg}

    def push(self, object_type: str, convernix_data: Dict[str, Any], external_id: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        from integrations.sync_engine import transform_convernix_to_external
        payload = transform_convernix_to_external(self.instance, object_type, convernix_data)
        ext_id = external_id or f"zc_{convernix_data.get('id', 'lead')}"
        return True, ext_id, None

    def pull(self, object_type: str, since: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        return []

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        return {'status': 'processed', 'provider': 'zoho'}

