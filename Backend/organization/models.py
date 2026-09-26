from django.conf import settings
from django.db import models
from django.utils import timezone


class OrganizationProfile(models.Model):
    tenant = models.OneToOneField('users.Tenant', on_delete=models.CASCADE, related_name='profile')
    legal_business_name = models.CharField(max_length=200, blank=True, default='')
    org_id = models.CharField(max_length=64, unique=True)
    industry = models.CharField(max_length=100, default='Technology')
    business_email = models.EmailField(blank=True, default='')
    business_phone = models.CharField(max_length=30, blank=True, default='')
    website = models.CharField(max_length=255, blank=True, default='')
    country = models.CharField(max_length=100, default='India')
    state = models.CharField(max_length=100, default='Maharashtra')
    city = models.CharField(max_length=100, default='Pune')
    postal_code = models.CharField(max_length=20, default='411057')
    timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    default_language = models.CharField(max_length=50, default='English')
    business_address = models.TextField(blank=True, default='')
    logo_url = models.TextField(blank=True, default='')
    onboarding_completed = models.BooleanField(default=False)
    onboarding_steps = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.tenant.name} Profile ({self.org_id})'

    @classmethod
    def get_or_create_for_tenant(cls, tenant):
        profile = cls.objects.filter(tenant=tenant).first()
        if not profile:
            org_num = f'{tenant.id:04d}' if tenant.id else '1001'
            org_id = f'ORG-CLD-{org_num}'
            default_steps = {
                'profile': True,
                'whatsapp': tenant.business_numbers.filter(is_active=True).exists(),
                'invite_team': tenant.users.count() > 1,
                'roles': False,
                'billing': False,
            }
            profile = cls.objects.create(
                tenant=tenant,
                legal_business_name=f'{tenant.name} Solutions Pvt Ltd',
                org_id=org_id,
                business_email=f'hello@{tenant.slug}.example' if tenant.slug else 'hello@convernix.example',
                business_phone='+91 98765 43210',
                website=f'https://{tenant.slug}.example' if tenant.slug else 'https://cloudtronix.io',
                business_address='B-204, Blue Ridge Commerce Park, Pune, Maharashtra 411057',
                onboarding_steps=default_steps,
                onboarding_completed=all(default_steps.values()),
            )
        return profile


class CustomRole(models.Model):
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='custom_roles')
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80)
    description = models.TextField(blank=True, default='')
    is_system = models.BooleanField(default=False)
    permissions = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'slug'], name='unique_tenant_role_slug')
        ]
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.tenant.name})'


class BillingProfile(models.Model):
    tenant = models.OneToOneField('users.Tenant', on_delete=models.CASCADE, related_name='billing_profile')
    legal_company_name = models.CharField(max_length=200, default='Cloudtronix Solutions Pvt Ltd')
    billing_email = models.EmailField(default='billing@cloudtronix.io')
    tax_id = models.CharField(max_length=50, default='27AABCC1234D1ZQ')
    country = models.CharField(max_length=100, default='India')
    state = models.CharField(max_length=100, default='Maharashtra')
    city = models.CharField(max_length=100, default='Pune')
    postal_code = models.CharField(max_length=20, default='411057')
    address = models.TextField(default='B-204, Blue Ridge Commerce Park, Pune, Maharashtra 411057')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Billing: {self.legal_company_name}'


class PaymentMethod(models.Model):
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='payment_methods')
    card_brand = models.CharField(max_length=50, default='Visa')
    last4 = models.CharField(max_length=4, default='4242')
    exp_month = models.PositiveSmallIntegerField(default=12)
    exp_year = models.PositiveIntegerField(default=2029)
    is_default = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f'{self.card_brand} •••• {self.last4}'


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=60, unique=True)
    billing_period = models.CharField(max_length=50)
    issue_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=9999.00)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='paid')
    payment_method_desc = models.CharField(max_length=100, default='Visa •••• 4242')
    pdf_url = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issue_date', '-created_at']

    def __str__(self):
        return f'{self.invoice_number} ({self.status})'


class AuditLog(models.Model):
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='audit_logs', null=True, blank=True)
    actor_name = models.CharField(max_length=150)
    actor_email = models.EmailField(blank=True, default='')
    action = models.CharField(max_length=150)
    module = models.CharField(max_length=50)
    resource = models.CharField(max_length=255)
    ip_address = models.CharField(max_length=45, default='127.0.0.1')
    status = models.CharField(max_length=30, default='Success')
    metadata = models.JSONField(default=dict, blank=True)
    tamper_hash = models.CharField(max_length=64, blank=True, db_index=True)
    previous_hash = models.CharField(max_length=64, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.module}] {self.actor_name}: {self.action} on {self.resource}'

    def save(self, *args, **kwargs):
        if not self.tamper_hash:
            import hashlib, hmac
            from django.conf import settings
            last_log = AuditLog.objects.filter(tenant=self.tenant).exclude(pk=self.pk).order_by('-pk').first() if self.tenant else None
            prev = last_log.tamper_hash if last_log and last_log.tamper_hash else 'GENESIS-BLOCK-00000000'
            self.previous_hash = prev
            data_to_sign = f'{self.tenant_id}:{self.actor_email}:{self.action}:{self.module}:{self.resource}:{self.status}:{prev}'
            signing_key = getattr(settings, 'SECRET_KEY', 'convernix-audit-secret').encode('utf-8')
            self.tamper_hash = hmac.new(signing_key, data_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        super().save(*args, **kwargs)

    @classmethod
    def log(cls, tenant, actor_name, action, module, resource, ip_address='127.0.0.1', status='Success', metadata=None, actor_email=''):
        from organization.services.audit_service import redact_sensitive_data
        return cls.objects.create(
            tenant=tenant,
            actor_name=actor_name,
            actor_email=actor_email,
            action=action,
            module=module,
            resource=resource,
            ip_address=ip_address,
            status=status,
            metadata=redact_sensitive_data(metadata or {}),
        )

    @classmethod
    def verify_integrity(cls, tenant):
        """Verifies the cryptographic hash chain for this tenant to detect unauthorized log alterations."""
        import hashlib, hmac
        from django.conf import settings
        logs = cls.objects.filter(tenant=tenant).order_by('pk')
        signing_key = getattr(settings, 'SECRET_KEY', 'convernix-audit-secret').encode('utf-8')
        prev = 'GENESIS-BLOCK-00000000'
        for log in logs:
            if log.previous_hash and log.previous_hash != prev:
                return {'valid': False, 'tampered_log_id': log.id, 'reason': 'Previous hash chain broken'}
            data_to_sign = f'{log.tenant_id}:{log.actor_email}:{log.action}:{log.module}:{log.resource}:{log.status}:{prev}'
            expected_hash = hmac.new(signing_key, data_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
            if log.tamper_hash and log.tamper_hash != expected_hash:
                return {'valid': False, 'tampered_log_id': log.id, 'reason': 'Audit signature mismatch'}
            prev = log.tamper_hash or expected_hash
        return {'valid': True, 'count': logs.count()}


class AdminNotificationPreference(models.Model):
    tenant = models.OneToOneField('users.Tenant', on_delete=models.CASCADE, related_name='notification_preferences')
    security_email = models.BooleanField(default=True)
    security_inapp = models.BooleanField(default=True)
    billing_email = models.BooleanField(default=True)
    billing_inapp = models.BooleanField(default=True)
    whatsapp_email = models.BooleanField(default=True)
    whatsapp_inapp = models.BooleanField(default=True)
    system_email = models.BooleanField(default=True)
    system_inapp = models.BooleanField(default=True)
    user_management_email = models.BooleanField(default=True)
    user_management_inapp = models.BooleanField(default=True)
    campaign_email = models.BooleanField(default=True)
    campaign_inapp = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Notification preferences for {self.tenant.name}'


class UserSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='active_sessions')
    session_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    device = models.CharField(max_length=100, default='Desktop (Mac OS)')
    browser = models.CharField(max_length=100, default='Chrome 128')
    location = models.CharField(max_length=150, default='Pune, India')
    ip_address = models.CharField(max_length=45, default='127.0.0.1')
    is_current = models.BooleanField(default=False)
    is_revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_active = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_current', '-last_active']

    def __str__(self):
        return f'{self.user.email} - {self.device}'


# =============================================================================
# Granular RBAC Models
# =============================================================================
class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True, help_text='Canonical permission code, e.g. tenant.settings.read')
    module = models.CharField(max_length=50, help_text='Module group, e.g. Settings, IAM, WhatsApp')
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['module', 'code']

    def __str__(self):
        return self.code


class RolePermission(models.Model):
    role = models.ForeignKey(CustomRole, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='role_assignments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['role', 'permission'], name='unique_role_permission')
        ]

    def __str__(self):
        return f'{self.role.name} -> {self.permission.code}'


# =============================================================================
# Tenant-Specific Notification Templates & Versioning
# =============================================================================
class NotificationTemplate(models.Model):
    CHANNEL_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('in_app', 'In-App'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='notification_templates')
    name = models.CharField(max_length=120)
    event_type = models.CharField(max_length=80, help_text='Event trigger, e.g. new_lead, ticket_assigned')
    channel = models.CharField(max_length=30, choices=CHANNEL_CHOICES, default='whatsapp')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    current_version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'name'], name='unique_tenant_notification_template_name')
        ]

    def __str__(self):
        return f'[{self.channel}] {self.name} ({self.tenant.name})'


class NotificationTemplateVersion(models.Model):
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE, related_name='versions')
    version = models.PositiveIntegerField(default=1)
    content = models.TextField(help_text='Template body containing allowlisted variables e.g. {{lead.name}}')
    variables = models.JSONField(default=list, blank=True, help_text='Registry of variables used in this version')
    change_summary = models.TextField(blank=True, default='')
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    published_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-version']
        constraints = [
            models.UniqueConstraint(fields=['template', 'version'], name='unique_template_version_number')
        ]

    def __str__(self):
        return f'{self.template.name} v{self.version}'


# =============================================================================
# Plans, Feature Entitlements & Usage Metering
# =============================================================================
class Feature(models.Model):
    code = models.CharField(max_length=50, unique=True, help_text='Feature code e.g. INBOX, CAMPAIGNS, CUSTOM_ROLES')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')

    def __str__(self):
        return self.name


class Plan(models.Model):
    INTERVAL_CHOICES = [
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
    ]
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    tier = models.CharField(max_length=20, default='small')
    price_inr = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    billing_interval = models.CharField(max_length=20, choices=INTERVAL_CHOICES, default='monthly')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} (₹{self.price_inr}/{self.billing_interval})'


class PlanEntitlement(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='entitlements')
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, related_name='plan_entitlements')
    is_enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['plan', 'feature'], name='unique_plan_feature_entitlement')
        ]

    def __str__(self):
        return f'{self.plan.name} -> {self.feature.code}: {self.is_enabled}'


class PlanLimit(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='limits')
    metric_code = models.CharField(max_length=50, help_text='Metric e.g. users, departments, whatsapp_numbers, monthly_messages')
    max_value = models.BigIntegerField(default=0, help_text='0 = unlimited or strict positive capacity')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['plan', 'metric_code'], name='unique_plan_metric_limit')
        ]

    def __str__(self):
        return f'{self.plan.name} limit for {self.metric_code}: {self.max_value}'


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('trialing', 'Trialing'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('incomplete', 'Incomplete'),
    ]

    tenant = models.OneToOneField('users.Tenant', on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='active_subscriptions')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='active')
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.tenant.name} Subscription ({self.plan.name} - {self.status})'


class SubscriptionItem(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f'{self.name} x{self.quantity}'


class UsageCounter(models.Model):
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='usage_counters')
    metric_code = models.CharField(max_length=50)
    current_value = models.BigIntegerField(default=0)
    period_start = models.DateTimeField(default=timezone.now)
    period_end = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'metric_code', 'period_start'], name='unique_tenant_metric_counter_period')
        ]

    def __str__(self):
        return f'{self.tenant.name} [{self.metric_code}]: {self.current_value}'


class UsageEvent(models.Model):
    event_id = models.CharField(max_length=64, unique=True)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='usage_events')
    metric_code = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField(default=1)
    idempotency_key = models.CharField(max_length=120, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'idempotency_key'], name='unique_tenant_usage_idempotency')
        ]

    def __str__(self):
        return f'{self.tenant.name} - {self.metric_code} (+{self.quantity})'


# =============================================================================
# Billing & Transactions
# =============================================================================
class BillingCustomer(models.Model):
    tenant = models.OneToOneField('users.Tenant', on_delete=models.CASCADE, related_name='billing_customer')
    provider_customer_id = models.CharField(max_length=100, blank=True, default='')
    currency = models.CharField(max_length=10, default='INR')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Billing Customer for {self.tenant.name} ({self.provider_customer_id or "Local"})'


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'{self.description} (₹{self.amount})'


class Payment(models.Model):
    STATUS_CHOICES = [
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
        ('refunded', 'Refunded'),
    ]
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='payments')
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    payment_reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='succeeded')
    payment_method_desc = models.CharField(max_length=100, default='Visa •••• 4242')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.payment_reference} ({self.status}) - ₹{self.amount}'


class BillingEvent(models.Model):
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='billing_events')
    event_type = models.CharField(max_length=80)
    idempotency_key = models.CharField(max_length=120, unique=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.event_type} on {self.tenant.name}'


# =============================================================================
# Security, Keys & Policies
# =============================================================================
class TenantKeyMetadata(models.Model):
    tenant = models.OneToOneField('users.Tenant', on_delete=models.CASCADE, related_name='key_metadata')
    key_version = models.PositiveIntegerField(default=1)
    algorithm = models.CharField(max_length=50, default='AES-256-GCM-KMS')
    wrapped_dek = models.TextField(blank=True, default='', help_text='KMS-wrapped 256-bit DEK')
    wrapped_search_key = models.TextField(blank=True, default='', help_text='KMS-wrapped 256-bit blind index HMAC key')
    kms_key_id = models.CharField(max_length=255, default='convernix-kek-primary')
    kms_provider = models.CharField(max_length=50, default='local')
    salt = models.CharField(max_length=64, blank=True, default='')
    last_rotated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'Key metadata for {self.tenant.name} (v{self.key_version}) [{self.algorithm}]'


class TenantKeyVersionHistory(models.Model):
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='key_history')
    key_version = models.PositiveIntegerField()
    wrapped_dek = models.TextField(help_text='KMS-wrapped DEK for this version')
    wrapped_search_key = models.TextField(blank=True, default='')
    kms_key_id = models.CharField(max_length=255, default='convernix-kek-primary')
    kms_provider = models.CharField(max_length=50, default='local')
    status = models.CharField(max_length=30, default='ACTIVE', choices=[('ACTIVE', 'Active'), ('RETIRED', 'Retired'), ('REVOKED', 'Revoked')])
    created_at = models.DateTimeField(auto_now_add=True)
    retired_at = models.DateTimeField(null=True, blank=True)
    rotated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-key_version']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'key_version'], name='unique_tenant_key_version')
        ]

    def __str__(self):
        return f'{self.tenant.name} Key v{self.key_version} ({self.status})'


class TenantApiKey(models.Model):
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=100)
    key_prefix = models.CharField(max_length=24, db_index=True, help_text='Safe prefix e.g. cvx_live_ab12')
    key_hash = models.CharField(max_length=128, db_index=True, help_text='SHA-256 hash of plaintext secret')
    scopes = models.JSONField(default=list, blank=True, help_text='Granted scope permissions')
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.key_prefix}...) - Active: {self.is_active}'


class SecurityPolicy(models.Model):
    tenant = models.OneToOneField('users.Tenant', on_delete=models.CASCADE, related_name='security_policy')
    mfa_required = models.BooleanField(default=False)
    password_min_length = models.PositiveSmallIntegerField(default=8)
    password_require_special = models.BooleanField(default=True)
    session_duration_minutes = models.PositiveIntegerField(default=480)
    ip_allowlist = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Security Policy for {self.tenant.name}'


class SecurityEvent(models.Model):
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='security_events')
    event_type = models.CharField(max_length=80)
    actor_email = models.EmailField(blank=True, default='')
    ip_address = models.CharField(max_length=45, default='127.0.0.1')
    user_agent = models.TextField(blank=True, default='')
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.event_type}] {self.actor_email} ({self.created_at})'


# =============================================================================
# Tenant Third-Party Integrations
# =============================================================================
class TenantIntegration(models.Model):
    INTEGRATION_TYPES = [
        ('crm', 'CRM Webhook'),
        ('webhook', 'Custom Webhook'),
        ('slack', 'Slack Notifications'),
        ('hubspot', 'HubSpot CRM'),
        ('zapier', 'Zapier Automation'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('error', 'Error'),
    ]

    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='integrations')
    integration_type = models.CharField(max_length=50, choices=INTEGRATION_TYPES)
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='inactive')
    config = models.JSONField(default=dict, blank=True, help_text='Safe non-secret configuration')
    encrypted_credentials = models.TextField(blank=True, default='', help_text='Encrypted sensitive tokens/secrets')
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'integration_type', 'name'], name='unique_tenant_integration_name')
        ]

    def __str__(self):
        return f'{self.name} ({self.get_integration_type_display()}) - {self.tenant.name}'


# =============================================================================
# Controlled Platform Support Access Elevation
# =============================================================================
class SupportAccessRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ]

    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='support_requests')
    platform_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='requested_support_access')
    reason = models.TextField(help_text='Operational justification or ticket link')
    ticket_reference = models.CharField(max_length=100)
    requested_scopes = models.JSONField(default=list, help_text='Explicit allowed scopes e.g. read_only, whatsapp_diagnostics')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_support_access')
    approved_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Support Access Request #{self.pk} for {self.tenant.name} by {self.platform_user.email} ({self.status})'


class SupportAccessSession(models.Model):
    request = models.OneToOneField(SupportAccessRequest, on_delete=models.CASCADE, related_name='session')
    session_token_hash = models.CharField(max_length=128, unique=True)
    is_active = models.BooleanField(default=True)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Support Session for Request #{self.request_id} (Active: {self.is_active})'


# =============================================================================
# Privacy & DPDP Act 2023 / ISO 27701 Models
# =============================================================================
class PrivacyNotice(models.Model):
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='privacy_notices')
    notice_version = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200)
    effective_date = models.DateField(default=timezone.now)
    purpose_description = models.TextField(help_text='Description of data processing purposes')
    data_categories = models.JSONField(default=list, help_text='Categories of personal data processed')
    language = models.CharField(max_length=20, default='en')
    is_active = models.BooleanField(default=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-notice_version']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'notice_version', 'language'], name='unique_tenant_notice_version_lang')
        ]

    def __str__(self):
        return f'{self.title} v{self.notice_version} ({self.tenant.name})'


class PrivacyEvent(models.Model):
    EVENT_CHOICES = [
        ('NOTICE_PRESENTED', 'Notice Presented'),
        ('CONSENT_RECORDED', 'Consent Recorded'),
        ('CONSENT_WITHDRAWN', 'Consent Withdrawn'),
        ('PRIVACY_REQUEST_RECEIVED', 'Privacy Request Received'),
    ]

    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='privacy_events')
    data_principal_reference = models.CharField(max_length=100, db_index=True)
    event_type = models.CharField(max_length=50, choices=EVENT_CHOICES)
    purpose = models.CharField(max_length=100)
    notice_version = models.PositiveIntegerField(default=1)
    source = models.CharField(max_length=100, default='web_chat')
    occurred_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-occurred_at']

    def __str__(self):
        return f'[{self.event_type}] {self.data_principal_reference} ({self.occurred_at})'


class PrivacyRequest(models.Model):
    TYPE_CHOICES = [
        ('ACCESS', 'Access & Discovery'),
        ('CORRECTION', 'Correction'),
        ('ERASURE', 'Erasure / Right to be Forgotten'),
        ('WITHDRAW_CONSENT', 'Withdraw Consent'),
        ('GRIEVANCE', 'Grievance Redressal'),
        ('OTHER', 'Other Request'),
    ]
    STATUS_CHOICES = [
        ('RECEIVED', 'Received'),
        ('VERIFYING', 'Identity Verification Pending'),
        ('IN_REVIEW', 'In Review'),
        ('ACTION_PENDING', 'Action Pending'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
    ]

    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='privacy_requests')
    request_id = models.CharField(max_length=50, unique=True)
    data_principal_reference = models.CharField(max_length=100, db_index=True)
    request_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='RECEIVED')
    is_verified = models.BooleanField(default=False)
    verification_method = models.CharField(max_length=100, blank=True, default='OTP_VERIFIED')
    assigned_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    received_date = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField(null=True, blank=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    details = models.TextField(blank=True, default='')
    resolution_notes = models.TextField(blank=True, default='')
    audit_history = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.request_id} ({self.get_request_type_display()}) - {self.status}'


class RetentionPolicy(models.Model):
    CATEGORY_CHOICES = [
        ('LEADS', 'Customer Leads'),
        ('CONVERSATIONS', 'WhatsApp Conversations & Messages'),
        ('ATTACHMENTS', 'Media Attachments'),
        ('EXPORTS', 'Temporary Data Exports'),
        ('AUDIT_LOGS', 'Administrative Audit Logs'),
        ('SECURITY_EVENTS', 'Security Incident Logs'),
        ('PRIVACY_REQUESTS', 'Data Principal Privacy Requests'),
    ]
    ACTION_CHOICES = [
        ('DELETE', 'Permanent Deletion'),
        ('ANONYMIZE', 'Cryptographic Anonymization'),
    ]

    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='retention_policies')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    retention_days = models.PositiveIntegerField(default=365)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default='ANONYMIZE')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'category'], name='unique_tenant_retention_category')
        ]

    def __str__(self):
        return f'{self.tenant.name} {self.category} -> {self.retention_days} days ({self.action})'


class LegalHold(models.Model):
    SCOPE_CHOICES = [
        ('TENANT_WIDE', 'Tenant Wide Legal Hold'),
        ('CUSTOMER', 'Specific Customer Record'),
        ('ENQUIRY', 'Specific Enquiry Record'),
    ]

    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='legal_holds')
    hold_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    reason = models.TextField(help_text='Litigation or regulatory inquiry justification')
    scope = models.CharField(max_length=30, choices=SCOPE_CHOICES, default='TENANT_WIDE')
    resource_id = models.CharField(max_length=100, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='released_holds')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.hold_id}: {self.name} (Active: {self.is_active})'


class DataExportRecord(models.Model):
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='exports')
    export_token = models.CharField(max_length=80, unique=True, db_index=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    export_type = models.CharField(max_length=50, default='PRIVACY_DSR')
    file_path = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    download_count = models.PositiveIntegerField(default=0)
    downloaded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Export {self.export_token} ({self.export_type})'


# =============================================================================
# Compliance, Incident & Subprocessor Models
# =============================================================================
class ComplianceControl(models.Model):
    FRAMEWORK_CHOICES = [
        ('ISO27001', 'ISO/IEC 27001:2022'),
        ('ISO27701', 'ISO/IEC 27701:2025'),
        ('SOC2', 'SOC 2 Trust Services Criteria'),
        ('DPDP', 'Digital Personal Data Protection Act 2023'),
        ('INTERNAL', 'Internal Security Controls'),
    ]
    STATUS_CHOICES = [
        ('IMPLEMENTED', 'Implemented'),
        ('IN_PROGRESS', 'In Progress'),
        ('UNDER_REVIEW', 'Under Review'),
    ]

    control_id = models.CharField(max_length=50, unique=True)
    control_name = models.CharField(max_length=150)
    framework = models.CharField(max_length=30, choices=FRAMEWORK_CHOICES)
    framework_reference = models.CharField(max_length=100)
    implementation_description = models.TextField()
    owner = models.CharField(max_length=100, default='Security Team')
    evidence_source = models.CharField(max_length=150)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='IMPLEMENTED')
    last_reviewed = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['framework', 'control_id']

    def __str__(self):
        return f'[{self.framework}] {self.control_id} - {self.control_name}'


class SecurityIncident(models.Model):
    CATEGORY_CHOICES = [
        ('AUTHENTICATION', 'Authentication Failure / Brute Force'),
        ('AUTHORIZATION', 'Authorization Bypass / Privilege Escalation'),
        ('DATA_ACCESS', 'Unauthorized Data Access Attempt'),
        ('TENANT_ISOLATION', 'Cross-Tenant Access Anomaly'),
        ('MALICIOUS_REQUEST', 'Malicious Request / Injection'),
        ('SECRET_EXPOSURE', 'Credential or Key Exposure'),
        ('DATA_BREACH', 'Data Security Breach Incident'),
        ('SYSTEM_AVAILABILITY', 'System Availability / DoS'),
        ('OTHER', 'Other Security Anomaly'),
    ]
    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ]
    STATUS_CHOICES = [
        ('DETECTED', 'Detected'),
        ('TRIAGED', 'Triaged'),
        ('CONTAINED', 'Contained'),
        ('INVESTIGATING', 'Investigating'),
        ('REMEDIATED', 'Remediated'),
        ('CLOSED', 'Closed'),
    ]

    incident_id = models.CharField(max_length=50, unique=True)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='incidents', null=True, blank=True)
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='DETECTED')
    title = models.CharField(max_length=200)
    description = models.TextField()
    detected_at = models.DateTimeField(default=timezone.now)
    contained_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    assigned_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    affected_resources = models.JSONField(default=list, blank=True)
    containment_steps = models.TextField(blank=True, default='')
    investigation_findings = models.TextField(blank=True, default='')
    remediation_notes = models.TextField(blank=True, default='')
    post_incident_review = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-detected_at']

    def __str__(self):
        return f'{self.incident_id} [{self.severity}]: {self.title}'


class SubprocessorInventory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    purpose = models.CharField(max_length=255)
    data_categories = models.JSONField(default=list)
    hosting_region = models.CharField(max_length=100, default='ap-south-1 (Mumbai, India)')
    dpa_status = models.CharField(max_length=60, default='Signed / Active')
    security_certifications = models.JSONField(default=list)
    status = models.CharField(max_length=30, default='ACTIVE', choices=[('ACTIVE', 'Active'), ('REVIEW', 'Under Review'), ('RETIRED', 'Retired')])
    last_reviewed = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.hosting_region})'


class BackupRestoreVerification(models.Model):
    test_id = models.CharField(max_length=50, unique=True)
    backup_identifier = models.CharField(max_length=255)
    backup_timestamp = models.DateTimeField()
    test_timestamp = models.DateTimeField(default=timezone.now)
    duration_seconds = models.PositiveIntegerField(default=120)
    status = models.CharField(max_length=30, default='SUCCESS', choices=[('SUCCESS', 'Success'), ('FAILED', 'Failed'), ('WARNING', 'Warning')])
    tested_by = models.CharField(max_length=150, default='DevSecOps Automation')
    notes = models.TextField(blank=True, default='Automated restore test completed successfully in isolated staging sandbox.')

    class Meta:
        ordering = ['-test_timestamp']

    def __str__(self):
        return f'{self.test_id} - {self.status} ({self.test_timestamp})'


