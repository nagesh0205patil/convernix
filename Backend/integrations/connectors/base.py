import abc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ConnectorManifest:
    key: str
    name: str
    category: str  # CRM, ERP, Helpdesk, Automation, Analytics, Custom
    auth_type: str  # oauth2, api_key, basic, webhook, custom
    capabilities: List[str]  # e.g. ['push', 'pull', 'webhooks', 'field_mapping']
    configuration_schema: Dict[str, Any]
    supported_objects: List[str]  # e.g. ['lead', 'contact', 'conversation', 'ticket']
    icon: str = 'Plug'
    description: str = ''
    docs_url: str = ''


class BaseConnector(abc.ABC):
    """Abstract base class for all third-party and custom Convernix connectors."""

    def __init__(self, instance):
        self.instance = instance
        self.tenant = instance.tenant

    @classmethod
    @abc.abstractmethod
    def get_manifest(cls) -> ConnectorManifest:
        pass

    @abc.abstractmethod
    def test_connection(self) -> Tuple[bool, str]:
        """Validates credentials and network connectivity to external provider."""
        pass

    @abc.abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Performs a periodic diagnostic check of provider status and limits."""
        pass

    @abc.abstractmethod
    def push(self, object_type: str, convernix_data: Dict[str, Any], external_id: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Pushes a record to the external system.
        Returns: (success, external_object_id, error_message)
        """
        pass

    @abc.abstractmethod
    def pull(self, object_type: str, since: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Pulls updated records from the external provider."""
        pass

    @abc.abstractmethod
    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Handles an inbound event dispatched by the external provider."""
        pass

    def authorize(self, auth_params: Dict[str, Any]) -> Tuple[bool, str]:
        """Initializes or saves authentication state."""
        return True, "Authorized"

    def refresh_credentials(self) -> Tuple[bool, str]:
        """Refreshes expired OAuth tokens or dynamic credentials."""
        return True, "Refreshed"

    def disconnect(self) -> Tuple[bool, str]:
        """Revokes external tokens and cleans up provider resources."""
        return True, "Disconnected"

