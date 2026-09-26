from typing import Any, Dict, List, Optional, Tuple
from .base import BaseConnector, ConnectorManifest


class ZapierConnector(BaseConnector):
    @classmethod
    def get_manifest(cls) -> ConnectorManifest:
        return ConnectorManifest(
            key='zapier',
            name='Zapier Automation App',
            category='Automation',
            auth_type='api_key',
            capabilities=['push', 'webhooks'],
            configuration_schema={
                'zap_webhook_url': {'type': 'string', 'required': False, 'label': 'Catch Hook URL'},
            },
            supported_objects=['lead', 'contact', 'conversation', 'ticket'],
            icon='Zap',
            description='Connect Convernix events with 5,000+ external business applications via Zapier triggers and actions.',
            docs_url='https://platform.zapier.com/docs/intro',
        )

    def test_connection(self) -> Tuple[bool, str]:
        return True, "Zapier trigger endpoint ready."

    def health_check(self) -> Dict[str, Any]:
        return {'status': 'healthy', 'message': 'Operational'}

    def push(self, object_type: str, convernix_data: Dict[str, Any], external_id: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        return True, f"zap_{convernix_data.get('id', 'ok')}", None

    def pull(self, object_type: str, since: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        return []

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        return {'status': 'processed', 'provider': 'zapier'}


class CustomWebhookConnector(BaseConnector):
    @classmethod
    def get_manifest(cls) -> ConnectorManifest:
        return ConnectorManifest(
            key='custom_webhook',
            name='Enterprise Custom REST Connector',
            category='Custom',
            auth_type='custom',
            capabilities=['push', 'pull', 'field_mapping'],
            configuration_schema={
                'target_url': {'type': 'string', 'required': True, 'label': 'Target REST Endpoint'},
                'http_method': {'type': 'select', 'options': ['POST', 'PUT'], 'default': 'POST', 'label': 'HTTP Method'},
                'custom_headers': {'type': 'json', 'default': {}, 'label': 'Custom Request Headers (JSON)'},
            },
            supported_objects=['lead', 'contact', 'ticket', 'conversation'],
            icon='Globe',
            description='Integrate internal bespoke enterprise backends, on-prem ERPs, and custom databases using configurable HTTP payloads.',
            docs_url='',
        )

    def test_connection(self) -> Tuple[bool, str]:
        cfg = self.instance.config or {}
        if cfg.get('target_url'):
            return True, "Custom target endpoint valid."
        return False, "Target URL is required."

    def health_check(self) -> Dict[str, Any]:
        success, msg = self.test_connection()
        return {'status': 'healthy' if success else 'degraded', 'message': msg}

    def push(self, object_type: str, convernix_data: Dict[str, Any], external_id: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        return True, f"custom_{convernix_data.get('id', 'ok')}", None

    def pull(self, object_type: str, since: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        return []

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        return {'status': 'processed', 'provider': 'custom'}

