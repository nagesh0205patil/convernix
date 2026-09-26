from typing import Dict, List, Optional, Type
from .base import BaseConnector, ConnectorManifest
from .hubspot import HubSpotConnector
from .salesforce import SalesforceConnector
from .zoho import ZohoConnector
from .slack import SlackConnector
from .zapier import ZapierConnector, CustomWebhookConnector

CONNECTOR_REGISTRY: Dict[str, Type[BaseConnector]] = {
    'hubspot': HubSpotConnector,
    'salesforce': SalesforceConnector,
    'zoho': ZohoConnector,
    'slack': SlackConnector,
    'zapier': ZapierConnector,
    'custom_webhook': CustomWebhookConnector,
}


def get_all_manifests() -> List[ConnectorManifest]:
    return [cls.get_manifest() for cls in CONNECTOR_REGISTRY.values()]


def get_connector_class(connector_key: str) -> Optional[Type[BaseConnector]]:
    return CONNECTOR_REGISTRY.get(connector_key)


def get_connector_instance_handler(instance) -> Optional[BaseConnector]:
    cls = get_connector_class(instance.connector_key)
    if cls:
        return cls(instance)
    return None

