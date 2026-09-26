from django.urls import path
from .views.v1_leads import LeadListCreateView, LeadDetailView
from .views.v1_contacts import ContactListCreateView, ContactDetailView
from .views.v1_conversations import ConversationListView, ConversationDetailView, ConversationCloseView
from .views.v1_messages import MessageListView, MessageSendView
from .views.v1_tickets import TicketListCreateView, TicketDetailView
from .views.v1_campaigns import CampaignListCreateView, CampaignDetailView, CampaignExecuteView
from .views.v1_templates import TemplateListView
from .views.v1_analytics import AnalyticsOverviewView
from .views.v1_webhooks import (
    WebhookEndpointListCreateView,
    WebhookEndpointDetailView,
    WebhookRotateSecretView,
    WebhookTestPingView,
    WebhookDeliveryListView,
    WebhookReplayView,
)
from .views.v1_service_accounts import ServiceAccountListCreateView, ServiceAccountDetailView
from .views.v1_api_keys import ApiKeyListCreateView, ApiKeyRevokeView, ApiKeyRotateView
from .views.v1_connectors import (
    ConnectorMarketplaceView,
    ConnectorInstanceListCreateView,
    ConnectorInstanceDetailView,
    ConnectorTestConnectionView,
    ConnectorFieldMappingView,
)
from .views.v1_logs import IntegrationApiLogListView, IntegrationAuditLogListView

urlpatterns = [
    # Leads API
    path('leads/', LeadListCreateView.as_view(), name='v1-lead-list-create'),
    path('leads/<int:pk>/', LeadDetailView.as_view(), name='v1-lead-detail'),

    # Contacts API
    path('contacts/', ContactListCreateView.as_view(), name='v1-contact-list-create'),
    path('contacts/<int:pk>/', ContactDetailView.as_view(), name='v1-contact-detail'),

    # Conversations API
    path('conversations/', ConversationListView.as_view(), name='v1-conversation-list'),
    path('conversations/<int:pk>/', ConversationDetailView.as_view(), name='v1-conversation-detail'),
    path('conversations/<int:pk>/close/', ConversationCloseView.as_view(), name='v1-conversation-close'),

    # Messages API
    path('messages/', MessageListView.as_view(), name='v1-message-list'),
    path('messages/send/', MessageSendView.as_view(), name='v1-message-send'),

    # Tickets API
    path('tickets/', TicketListCreateView.as_view(), name='v1-ticket-list-create'),
    path('tickets/<int:pk>/', TicketDetailView.as_view(), name='v1-ticket-detail'),

    # Campaigns API
    path('campaigns/', CampaignListCreateView.as_view(), name='v1-campaign-list-create'),
    path('campaigns/<int:pk>/', CampaignDetailView.as_view(), name='v1-campaign-detail'),
    path('campaigns/<int:pk>/execute/', CampaignExecuteView.as_view(), name='v1-campaign-execute'),

    # Templates & Analytics API
    path('templates/', TemplateListView.as_view(), name='v1-template-list'),
    path('analytics/', AnalyticsOverviewView.as_view(), name='v1-analytics-overview'),

    # Webhooks API
    path('webhooks/', WebhookEndpointListCreateView.as_view(), name='v1-webhook-list-create'),
    path('webhooks/<uuid:pk>/', WebhookEndpointDetailView.as_view(), name='v1-webhook-detail'),
    path('webhooks/<uuid:pk>/rotate-secret/', WebhookRotateSecretView.as_view(), name='v1-webhook-rotate-secret'),
    path('webhooks/<uuid:pk>/test/', WebhookTestPingView.as_view(), name='v1-webhook-test'),
    path('webhooks/deliveries/', WebhookDeliveryListView.as_view(), name='v1-webhook-deliveries'),
    path('webhooks/deliveries/<uuid:pk>/replay/', WebhookReplayView.as_view(), name='v1-webhook-replay'),

    # Service Accounts & API Keys API
    path('service-accounts/', ServiceAccountListCreateView.as_view(), name='v1-service-account-list-create'),
    path('service-accounts/<uuid:pk>/', ServiceAccountDetailView.as_view(), name='v1-service-account-detail'),
    path('api-keys/', ApiKeyListCreateView.as_view(), name='v1-api-key-list-create'),
    path('api-keys/<uuid:pk>/revoke/', ApiKeyRevokeView.as_view(), name='v1-api-key-revoke'),
    path('api-keys/<uuid:pk>/rotate/', ApiKeyRotateView.as_view(), name='v1-api-key-rotate'),

    # Connectors & Marketplace API
    path('integrations/marketplace/', ConnectorMarketplaceView.as_view(), name='v1-connector-marketplace'),
    path('integrations/instances/', ConnectorInstanceListCreateView.as_view(), name='v1-connector-instance-list-create'),
    path('integrations/instances/<uuid:pk>/', ConnectorInstanceDetailView.as_view(), name='v1-connector-instance-detail'),
    path('integrations/instances/<uuid:pk>/test/', ConnectorTestConnectionView.as_view(), name='v1-connector-instance-test'),
    path('integrations/instances/<uuid:pk>/mappings/', ConnectorFieldMappingView.as_view(), name='v1-connector-field-mappings'),

    # API Logs & Audit Logs
    path('logs/api/', IntegrationApiLogListView.as_view(), name='v1-logs-api'),
    path('logs/audit/', IntegrationAuditLogListView.as_view(), name='v1-logs-audit'),
]
