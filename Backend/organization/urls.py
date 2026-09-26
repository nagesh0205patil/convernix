from django.urls import path
from .views import (
    AdminApiKeyDetailView,
    AdminApiKeysView,
    AdminAuditLogsView,
    AdminAuditVerifyView,
    AdminBillingView,
    AdminComplianceTelemetryView,
    AdminDepartmentDetailView,
    AdminDepartmentsView,
    AdminIntegrationDetailView,
    AdminIntegrationsManageView,
    AdminInvoicesView,
    AdminKmsKeyView,
    AdminLegalHoldView,
    AdminMfaView,
    AdminNotificationPreferenceSerializer,
    AdminNotificationTemplateDetailView,
    AdminNotificationTemplatePreviewView,
    AdminNotificationTemplatePublishView,
    AdminNotificationTemplateRollbackView,
    AdminNotificationTemplatesView,
    AdminNotificationsView,
    AdminOnboardingView,
    AdminPaymentMethodsView,
    AdminPlansView,
    AdminPrivacyEventsView,
    AdminPrivacyNoticeView,
    AdminPrivacyRequestActionView,
    AdminPrivacyRequestsView,
    AdminPrivacyRopaView,
    AdminRetentionPolicyView,
    AdminRetentionRunView,
    AdminRolesView,
    AdminSecurityIncidentView,
    AdminSecurityPolicyView,
    AdminSecurityView,
    AdminSubscriptionUpgradeView,
    AdminSubscriptionView,
    AdminSupportAccessApprovalView,
    AdminSupportAccessRequestView,
    AdminSupportAccessSessionView,
    AdminTeamsView,
    AdminUsageMetricsView,
    AdminUsageView,
    AdminUserDetailView,
    AdminUsersView,
    AdminWhatsAppView,
    OrganizationProfileView,
    PrivacyExportDownloadView,
)

urlpatterns = [
    # Organization & WhatsApp
    path('organization/', OrganizationProfileView.as_view(), name='admin-organization-profile'),
    path('whatsapp/', AdminWhatsAppView.as_view(), name='admin-whatsapp'),

    # IAM & Users
    path('users/', AdminUsersView.as_view(), name='admin-users'),
    path('users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('roles/', AdminRolesView.as_view(), name='admin-roles'),
    path('teams/', AdminTeamsView.as_view(), name='admin-teams'),
    path('departments/', AdminDepartmentsView.as_view(), name='admin-departments'),
    path('departments/<int:pk>/', AdminDepartmentDetailView.as_view(), name='admin-department-detail'),

    # Notification Templates
    path('templates/', AdminNotificationTemplatesView.as_view(), name='admin-templates'),
    path('templates/preview/', AdminNotificationTemplatePreviewView.as_view(), name='admin-template-preview-adhoc'),
    path('templates/<int:pk>/', AdminNotificationTemplateDetailView.as_view(), name='admin-template-detail'),
    path('templates/<int:pk>/publish/', AdminNotificationTemplatePublishView.as_view(), name='admin-template-publish'),
    path('templates/<int:pk>/preview/', AdminNotificationTemplatePreviewView.as_view(), name='admin-template-preview'),
    path('templates/<int:pk>/rollback/', AdminNotificationTemplateRollbackView.as_view(), name='admin-template-rollback'),

    # Security, KMS, API Keys & MFA
    path('security/', AdminSecurityView.as_view(), name='admin-security'),
    path('security/policy/', AdminSecurityPolicyView.as_view(), name='admin-security-policy'),
    path('security/kms/', AdminKmsKeyView.as_view(), name='admin-security-kms'),
    path('security/incidents/', AdminSecurityIncidentView.as_view(), name='admin-security-incidents'),
    path('security/mfa/', AdminMfaView.as_view(), name='admin-security-mfa'),
    path('api-keys/', AdminApiKeysView.as_view(), name='admin-api-keys'),
    path('api-keys/<int:pk>/', AdminApiKeyDetailView.as_view(), name='admin-api-key-detail'),

    # Privacy & DPDP Management
    path('privacy/ropa/', AdminPrivacyRopaView.as_view(), name='admin-privacy-ropa'),
    path('privacy/notices/', AdminPrivacyNoticeView.as_view(), name='admin-privacy-notices'),
    path('privacy/events/', AdminPrivacyEventsView.as_view(), name='admin-privacy-events'),
    path('privacy/requests/', AdminPrivacyRequestsView.as_view(), name='admin-privacy-requests'),
    path('privacy/requests/<int:pk>/action/', AdminPrivacyRequestActionView.as_view(), name='admin-privacy-request-action'),
    path('privacy/retention/', AdminRetentionPolicyView.as_view(), name='admin-privacy-retention'),
    path('privacy/retention/run/', AdminRetentionRunView.as_view(), name='admin-privacy-retention-run'),
    path('privacy/holds/', AdminLegalHoldView.as_view(), name='admin-privacy-holds'),
    path('privacy/exports/<str:token>/download/', PrivacyExportDownloadView.as_view(), name='privacy-export-download'),

    # Compliance Telemetry
    path('compliance/telemetry/', AdminComplianceTelemetryView.as_view(), name='admin-compliance-telemetry'),

    # Billing & Account
    path('subscription/', AdminSubscriptionView.as_view(), name='admin-subscription'),
    path('subscription/upgrade/', AdminSubscriptionUpgradeView.as_view(), name='admin-subscription-upgrade'),
    path('plans/', AdminPlansView.as_view(), name='admin-plans'),
    path('billing/', AdminBillingView.as_view(), name='admin-billing'),
    path('payment-methods/', AdminPaymentMethodsView.as_view(), name='admin-payment-methods'),
    path('invoices/', AdminInvoicesView.as_view(), name='admin-invoices'),
    path('usage/', AdminUsageView.as_view(), name='admin-usage'),
    path('usage/metrics/', AdminUsageMetricsView.as_view(), name='admin-usage-metrics'),

    # Integrations & Notifications
    path('integrations/', AdminIntegrationsManageView.as_view(), name='admin-integrations'),
    path('integrations/<int:pk>/', AdminIntegrationDetailView.as_view(), name='admin-integration-detail'),
    path('integrations/<int:pk>/test/', AdminIntegrationDetailView.as_view(), name='admin-integration-test'),
    path('notifications/', AdminNotificationsView.as_view(), name='admin-notifications'),

    # Audit & Onboarding
    path('audit-logs/', AdminAuditLogsView.as_view(), name='admin-audit-logs'),
    path('audit-logs/verify/', AdminAuditVerifyView.as_view(), name='admin-audit-verify'),
    path('onboarding/', AdminOnboardingView.as_view(), name='admin-onboarding'),

    # Controlled Platform Support Access Elevation
    path('support/requests/', AdminSupportAccessRequestView.as_view(), name='admin-support-requests'),
    path('support/requests/<int:pk>/<str:action>/', AdminSupportAccessApprovalView.as_view(), name='admin-support-request-action'),
    path('support/session/<str:action>/', AdminSupportAccessSessionView.as_view(), name='admin-support-session-action'),
]


