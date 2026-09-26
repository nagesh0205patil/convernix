from rest_framework import serializers
from .models import (
    OrganizationProfile,
    CustomRole,
    BillingProfile,
    PaymentMethod,
    Invoice,
    AuditLog,
    AdminNotificationPreference,
    UserSession,
)


class OrganizationProfileSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='tenant.name', read_only=True)
    slug = serializers.CharField(source='tenant.slug', read_only=True)
    tier = serializers.CharField(source='tenant.tier', read_only=True)
    tier_display = serializers.CharField(source='tenant.get_tier_display', read_only=True)

    class Meta:
        model = OrganizationProfile
        fields = [
            'id',
            'organization_name',
            'legal_business_name',
            'org_id',
            'slug',
            'tier',
            'tier_display',
            'industry',
            'business_email',
            'business_phone',
            'website',
            'country',
            'state',
            'city',
            'postal_code',
            'timezone',
            'default_language',
            'business_address',
            'logo_url',
            'onboarding_completed',
            'onboarding_steps',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'org_id', 'created_at', 'updated_at']

    def validate_business_email(self, value):
        if value and '@' not in value:
            raise serializers.ValidationError('Enter a valid business email address.')
        return value.strip().lower()


class CustomRoleSerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomRole
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'is_system',
            'permissions',
            'user_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_user_count(self, obj):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.filter(tenant=obj.tenant, role=obj.slug).count()


class BillingProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingProfile
        fields = [
            'id',
            'legal_company_name',
            'billing_email',
            'tax_id',
            'country',
            'state',
            'city',
            'postal_code',
            'address',
            'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = [
            'id',
            'card_brand',
            'last4',
            'exp_month',
            'exp_year',
            'is_default',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            'id',
            'invoice_number',
            'billing_period',
            'issue_date',
            'amount',
            'currency',
            'status',
            'payment_method_desc',
            'pdf_url',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'actor_name',
            'actor_email',
            'action',
            'module',
            'resource',
            'ip_address',
            'status',
            'metadata',
            'created_at',
        ]
        read_only_fields = fields


class AdminNotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminNotificationPreference
        fields = [
            'security_email',
            'security_inapp',
            'billing_email',
            'billing_inapp',
            'whatsapp_email',
            'whatsapp_inapp',
            'system_email',
            'system_inapp',
            'user_management_email',
            'user_management_inapp',
            'campaign_email',
            'campaign_inapp',
            'updated_at',
        ]
        read_only_fields = ['updated_at']


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = [
            'id',
            'device',
            'browser',
            'location',
            'ip_address',
            'is_current',
            'last_active',
        ]
        read_only_fields = ['id', 'last_active']


# =============================================================================
# New Enterprise SaaS Serializers
# =============================================================================
class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import Permission
        model = Permission
        fields = ['id', 'code', 'module', 'description']


class NotificationTemplateVersionSerializer(serializers.ModelSerializer):
    published_by_name = serializers.CharField(source='published_by.get_full_name', read_only=True)

    class Meta:
        from .models import NotificationTemplateVersion
        model = NotificationTemplateVersion
        fields = ['id', 'version', 'content', 'variables', 'change_summary', 'published_by_name', 'published_at']
        read_only_fields = ['id', 'version', 'published_at']


class NotificationTemplateSerializer(serializers.ModelSerializer):
    latest_version = serializers.SerializerMethodField()

    class Meta:
        from .models import NotificationTemplate
        model = NotificationTemplate
        fields = [
            'id', 'name', 'event_type', 'channel', 'status',
            'current_version', 'latest_version', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'current_version', 'created_at', 'updated_at']

    def get_latest_version(self, obj):
        v = obj.versions.first()
        if v:
            return NotificationTemplateVersionSerializer(v).data
        return None


class DepartmentSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)

    class Meta:
        from whatsapp.models import Department
        model = Department
        fields = [
            'id', 'name', 'slug', 'description', 'manager', 'manager_name',
            'business_hours', 'is_active', 'is_archived', 'archived_at', 'member_count'
        ]
        read_only_fields = ['id', 'archived_at']

    def get_member_count(self, obj):
        return obj.members.filter(active=True).count()


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import Feature
        model = Feature
        fields = ['id', 'code', 'name', 'description']


class PlanLimitSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import PlanLimit
        model = PlanLimit
        fields = ['metric_code', 'max_value']


class PlanSerializer(serializers.ModelSerializer):
    entitlements = serializers.SerializerMethodField()
    limits = PlanLimitSerializer(many=True, read_only=True)

    class Meta:
        from .models import Plan
        model = Plan
        fields = ['id', 'code', 'name', 'tier', 'price_inr', 'billing_interval', 'is_active', 'entitlements', 'limits']

    def get_entitlements(self, obj):
        return [e.feature.code for e in obj.entitlements.filter(is_enabled=True)]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_code = serializers.CharField(source='plan.code', read_only=True)
    tier = serializers.CharField(source='plan.tier', read_only=True)
    price_inr = serializers.DecimalField(source='plan.price_inr', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        from .models import Subscription
        model = Subscription
        fields = [
            'id', 'plan_name', 'plan_code', 'tier', 'price_inr', 'status',
            'current_period_start', 'current_period_end', 'cancel_at_period_end',
            'canceled_at', 'created_at'
        ]
        read_only_fields = fields


class UsageCounterSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import UsageCounter
        model = UsageCounter
        fields = ['metric_code', 'current_value', 'period_start', 'period_end', 'updated_at']


class TenantApiKeySerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        from .models import TenantApiKey
        model = TenantApiKey
        fields = [
            'id', 'name', 'key_prefix', 'scopes', 'is_active',
            'expires_at', 'last_used_at', 'revoked_at', 'creator_name', 'created_at'
        ]
        read_only_fields = ['id', 'key_prefix', 'last_used_at', 'revoked_at', 'created_at']


class SecurityPolicySerializer(serializers.ModelSerializer):
    class Meta:
        from .models import SecurityPolicy
        model = SecurityPolicy
        fields = [
            'mfa_required', 'password_min_length', 'password_require_special',
            'session_duration_minutes', 'ip_allowlist', 'updated_at'
        ]


class TenantIntegrationSerializer(serializers.ModelSerializer):
    has_credentials = serializers.SerializerMethodField()

    class Meta:
        from .models import TenantIntegration
        model = TenantIntegration
        fields = [
            'id', 'integration_type', 'name', 'status', 'config',
            'has_credentials', 'last_sync_at', 'last_error', 'updated_at'
        ]
        read_only_fields = ['id', 'last_sync_at', 'last_error', 'updated_at']

    def get_has_credentials(self, obj):
        return bool(obj.encrypted_credentials)


class SupportAccessRequestSerializer(serializers.ModelSerializer):
    platform_user_email = serializers.EmailField(source='platform_user.email', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        from .models import SupportAccessRequest
        model = SupportAccessRequest
        fields = [
            'id', 'tenant', 'tenant_name', 'platform_user_email', 'reason',
            'ticket_reference', 'requested_scopes', 'status', 'approved_at', 'expires_at', 'created_at'
        ]
        read_only_fields = ['id', 'tenant_name', 'platform_user_email', 'status', 'approved_at', 'created_at']


class PrivacyNoticeSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import PrivacyNotice
        model = PrivacyNotice
        fields = ['id', 'version', 'language', 'title', 'notice_text', 'effective_date', 'is_published', 'created_at']
        read_only_fields = ['id', 'created_at']


class PrivacyEventSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import PrivacyEvent
        model = PrivacyEvent
        fields = ['id', 'event_id', 'event_type', 'data_principal_identifier', 'legal_basis', 'purpose', 'notice_version', 'timestamp']
        read_only_fields = ['id', 'event_id', 'timestamp']


class PrivacyRequestSerializer(serializers.ModelSerializer):
    customer_phone = serializers.SerializerMethodField()

    class Meta:
        from .models import PrivacyRequest
        model = PrivacyRequest
        fields = [
            'id', 'request_id', 'customer', 'customer_phone', 'request_type', 'status',
            'requested_changes', 'resolution_notes', 'requested_at', 'fulfilled_at'
        ]
        read_only_fields = ['id', 'request_id', 'customer_phone', 'requested_at', 'fulfilled_at']

    def get_customer_phone(self, obj):
        if obj.customer:
            from organization.services.masking_service import MaskingService
            phone = getattr(obj.customer, 'plain_phone', None) or obj.customer.whatsapp_number
            return MaskingService.mask_phone(phone)
        return ''


class RetentionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        from .models import RetentionPolicy
        model = RetentionPolicy
        fields = ['id', 'category', 'retention_days', 'action', 'is_active', 'updated_at']
        read_only_fields = ['id', 'updated_at']


class LegalHoldSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        from .models import LegalHold
        model = LegalHold
        fields = ['id', 'hold_id', 'name', 'reason', 'scope', 'resource_id', 'is_active', 'created_by_email', 'created_at', 'released_at']
        read_only_fields = ['id', 'hold_id', 'created_by_email', 'created_at', 'released_at']


class ComplianceControlSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import ComplianceControl
        model = ComplianceControl
        fields = [
            'id', 'control_id', 'control_name', 'framework', 'framework_reference',
            'implementation_description', 'owner', 'evidence_source', 'status', 'last_reviewed'
        ]


class SecurityIncidentSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import SecurityIncident
        model = SecurityIncident
        fields = [
            'id', 'incident_id', 'category', 'severity', 'status', 'title', 'description',
            'detected_at', 'contained_at', 'resolved_at', 'affected_resources',
            'containment_steps', 'investigation_findings', 'remediation_notes', 'post_incident_review'
        ]
        read_only_fields = ['id', 'incident_id', 'detected_at']


class SubprocessorInventorySerializer(serializers.ModelSerializer):
    class Meta:
        from .models import SubprocessorInventory
        model = SubprocessorInventory
        fields = [
            'id', 'name', 'purpose', 'data_categories', 'hosting_region', 'dpa_status',
            'security_certifications', 'status', 'last_reviewed'
        ]


