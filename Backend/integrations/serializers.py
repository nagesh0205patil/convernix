from rest_framework import serializers
from .models import (
    ServiceAccount,
    ApiKey,
    WebhookEndpoint,
    WebhookDelivery,
    ConnectorInstance,
    ConnectorFieldMapping,
    ConnectorObjectMapping,
    ConnectorSyncJob,
    IntegrationApiLog,
)
from whatsapp.models import Lead, Customer, Enquiry, WhatsAppMessage
from campaigns.models import Campaign
from organization.models import NotificationTemplate


# =============================================================================
# Lead DTOs
# =============================================================================
class LeadResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    reference = serializers.CharField(source='enquiry.reference', default='')
    customer_name = serializers.CharField(source='plain_customer_name')
    phone_number = serializers.CharField(source='plain_phone_number')
    customer_email = serializers.CharField(source='plain_customer_email', allow_null=True)
    message = serializers.CharField(source='plain_message')
    team_name = serializers.CharField()
    status = serializers.CharField()
    source = serializers.CharField()
    business_number = serializers.CharField(source='business_number.number', default='')
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class LeadCreateSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=150, required=True)
    phone_number = serializers.CharField(max_length=30, required=True)
    customer_email = serializers.EmailField(required=False, allow_blank=True, default='')
    message = serializers.CharField(required=True)
    team_name = serializers.CharField(max_length=50, default='Support')
    business_number = serializers.CharField(max_length=30, required=False, allow_blank=True)


class LeadUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['new', 'assigned', 'in_progress', 'resolved'], required=False)
    team_name = serializers.CharField(max_length=50, required=False)
    assigned_to_email = serializers.EmailField(required=False, allow_blank=True)


# =============================================================================
# Contact DTOs
# =============================================================================
class ContactResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField(source='plain_name')
    whatsapp_number = serializers.CharField(source='plain_phone')
    email = serializers.CharField(source='plain_email', allow_null=True)
    organization_name = serializers.CharField(source='plain_organization', allow_null=True)
    consent_status = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ContactCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150, required=True)
    whatsapp_number = serializers.CharField(max_length=30, required=True)
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    organization_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    consent_status = serializers.ChoiceField(choices=['ACTIVE', 'WITHDRAWN'], default='ACTIVE')


class ContactUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    organization_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    consent_status = serializers.ChoiceField(choices=['ACTIVE', 'WITHDRAWN'], required=False)


# =============================================================================
# Conversation & Message DTOs
# =============================================================================
class MessageResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    whatsapp_message_id = serializers.CharField()
    direction = serializers.CharField()
    message_type = serializers.CharField()
    content = serializers.CharField(source='plain_content')
    status = serializers.CharField()
    timestamp = serializers.DateTimeField()
    customer_id = serializers.IntegerField(source='customer.id', allow_null=True)
    enquiry_reference = serializers.CharField(source='enquiry.reference', default='', allow_null=True)


class MessageSendSerializer(serializers.Serializer):
    to_phone = serializers.CharField(max_length=30, required=True)
    message = serializers.CharField(required=True)
    business_number = serializers.CharField(max_length=30, required=False, allow_blank=True)


class ConversationResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    reference = serializers.CharField()
    customer_id = serializers.IntegerField(source='customer.id')
    customer_name = serializers.CharField(source='customer.plain_name')
    customer_phone = serializers.CharField(source='customer.plain_phone')
    department = serializers.CharField(source='department.name')
    initial_message = serializers.CharField(source='plain_message')
    status = serializers.CharField()
    source = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


# =============================================================================
# Ticket DTOs
# =============================================================================
class TicketResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    reference = serializers.CharField()
    customer_name = serializers.CharField(source='customer.plain_name')
    customer_phone = serializers.CharField(source='customer.plain_phone')
    department = serializers.CharField(source='department.name')
    message = serializers.CharField(source='plain_message')
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class TicketCreateSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=150, required=True)
    customer_phone = serializers.CharField(max_length=30, required=True)
    customer_email = serializers.EmailField(required=False, allow_blank=True, default='')
    department_name = serializers.CharField(max_length=50, default='Support')
    message = serializers.CharField(required=True)


class TicketUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['new', 'assigned', 'in_progress', 'closed'], required=False)
    department_name = serializers.CharField(max_length=50, required=False)


# =============================================================================
# Campaign DTOs
# =============================================================================
class CampaignResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    message = serializers.CharField()
    status = serializers.CharField()
    target_audience = serializers.CharField()
    sent_count = serializers.IntegerField()
    delivered_count = serializers.IntegerField()
    opened_count = serializers.IntegerField()
    clicked_count = serializers.IntegerField()
    scheduled_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()


class CampaignCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=True)
    message = serializers.CharField(required=True)
    target_audience = serializers.CharField(max_length=200, default='All customers')
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)


# =============================================================================
# Notification Template DTOs
# =============================================================================
class TemplateResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    event_type = serializers.CharField()
    channel = serializers.CharField()
    status = serializers.CharField()
    current_version = serializers.IntegerField()
    created_at = serializers.DateTimeField()


# =============================================================================
# Service Account & API Key DTOs
# =============================================================================
class ServiceAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceAccount
        fields = ['id', 'name', 'description', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ServiceAccountCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=True)
    description = serializers.CharField(required=False, allow_blank=True, default='')


class ApiKeyResponseSerializer(serializers.ModelSerializer):
    service_account_id = serializers.CharField(source='service_account.id', default='', allow_null=True)

    class Meta:
        model = ApiKey
        fields = [
            'id', 'name', 'key_prefix', 'service_account_id', 'scopes',
            'ip_restrictions', 'is_active', 'expires_at', 'last_used_at',
            'revoked_at', 'created_at'
        ]
        read_only_fields = fields


class ApiKeyCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=True)
    service_account_id = serializers.UUIDField(required=False, allow_null=True)
    scopes = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    ip_restrictions = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    expires_in_days = serializers.IntegerField(required=False, default=90, min_value=1, max_value=365)


# =============================================================================
# Webhook DTOs
# =============================================================================
class WebhookEndpointResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEndpoint
        fields = [
            'id', 'name', 'url', 'status', 'event_filters', 'api_version',
            'consecutive_failures', 'disabled_reason', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class WebhookEndpointCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=True)
    url = serializers.URLField(max_length=500, required=True)
    event_filters = serializers.ListField(child=serializers.CharField(), required=False, default=lambda: ['*'])


class WebhookDeliveryResponseSerializer(serializers.ModelSerializer):
    endpoint_name = serializers.CharField(source='endpoint.name', default='')

    class Meta:
        model = WebhookDelivery
        fields = [
            'id', 'endpoint_id', 'endpoint_name', 'event_id', 'event_type',
            'attempt_number', 'http_status', 'duration_ms', 'error_category',
            'error_message', 'status', 'next_retry_at', 'delivered_at', 'created_at',
            'payload'
        ]
        read_only_fields = fields


# =============================================================================
# Connector DTOs
# =============================================================================
class ConnectorInstanceResponseSerializer(serializers.ModelSerializer):
    manifest = serializers.SerializerMethodField()

    class Meta:
        model = ConnectorInstance
        fields = [
            'id', 'connector_key', 'name', 'auth_type', 'status',
            'config', 'sync_direction', 'conflict_strategy',
            'last_health_check_at', 'health_status', 'health_message',
            'created_at', 'updated_at', 'manifest'
        ]
        read_only_fields = fields

    def get_manifest(self, obj):
        from .connectors.registry import get_connector_class
        cls = get_connector_class(obj.connector_key)
        if cls:
            m = cls.get_manifest()
            return {
                'key': m.key,
                'name': m.name,
                'category': m.category,
                'capabilities': m.capabilities,
                'supported_objects': m.supported_objects,
                'icon': m.icon,
                'description': m.description,
            }
        return {}


class ConnectorFieldMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConnectorFieldMapping
        fields = [
            'id', 'object_type', 'convernix_field', 'external_field',
            'transformation_type', 'transformation_config', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

