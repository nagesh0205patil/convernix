from django.contrib.auth.models import AbstractUser
from django.db import models


class Tenant(models.Model):
    TIER_CHOICES = [
        ('small', 'Basic'),
        ('mid', 'Standard'),
        ('large', 'Premium'),
    ]

    LIFECYCLE_PENDING = 'PENDING'
    LIFECYCLE_PROVISIONING = 'PROVISIONING'
    LIFECYCLE_TRIAL = 'TRIAL'
    LIFECYCLE_ACTIVE = 'ACTIVE'
    LIFECYCLE_PAST_DUE = 'PAST_DUE'
    LIFECYCLE_RESTRICTED = 'RESTRICTED'
    LIFECYCLE_SUSPENDED = 'SUSPENDED'
    LIFECYCLE_CANCELLED = 'CANCELLED'
    LIFECYCLE_DELETION_PENDING = 'DELETION_PENDING'
    LIFECYCLE_DELETED = 'DELETED'

    STATUS_CHOICES = [
        (LIFECYCLE_PENDING, 'Pending'),
        (LIFECYCLE_PROVISIONING, 'Provisioning'),
        (LIFECYCLE_TRIAL, 'Trial'),
        (LIFECYCLE_ACTIVE, 'Active'),
        (LIFECYCLE_PAST_DUE, 'Past Due'),
        (LIFECYCLE_RESTRICTED, 'Restricted'),
        (LIFECYCLE_SUSPENDED, 'Suspended'),
        (LIFECYCLE_CANCELLED, 'Cancelled'),
        (LIFECYCLE_DELETION_PENDING, 'Deletion Pending'),
        (LIFECYCLE_DELETED, 'Deleted'),
        # Backwards compatibility choices for legacy records:
        ('active', 'Active (Legacy)'),
        ('trial', 'Trial (Legacy)'),
        ('suspended', 'Suspended (Legacy)'),
    ]

    PERMITTED_TRANSITIONS = {
        LIFECYCLE_PENDING: {LIFECYCLE_PROVISIONING, LIFECYCLE_CANCELLED, LIFECYCLE_DELETED},
        LIFECYCLE_PROVISIONING: {LIFECYCLE_TRIAL, LIFECYCLE_ACTIVE, LIFECYCLE_PENDING, LIFECYCLE_CANCELLED},
        LIFECYCLE_TRIAL: {LIFECYCLE_ACTIVE, LIFECYCLE_PAST_DUE, LIFECYCLE_RESTRICTED, LIFECYCLE_SUSPENDED, LIFECYCLE_CANCELLED},
        LIFECYCLE_ACTIVE: {LIFECYCLE_PAST_DUE, LIFECYCLE_RESTRICTED, LIFECYCLE_SUSPENDED, LIFECYCLE_CANCELLED},
        LIFECYCLE_PAST_DUE: {LIFECYCLE_ACTIVE, LIFECYCLE_RESTRICTED, LIFECYCLE_SUSPENDED, LIFECYCLE_CANCELLED},
        LIFECYCLE_RESTRICTED: {LIFECYCLE_ACTIVE, LIFECYCLE_SUSPENDED, LIFECYCLE_CANCELLED, LIFECYCLE_DELETION_PENDING},
        LIFECYCLE_SUSPENDED: {LIFECYCLE_ACTIVE, LIFECYCLE_RESTRICTED, LIFECYCLE_CANCELLED, LIFECYCLE_DELETION_PENDING},
        LIFECYCLE_CANCELLED: {LIFECYCLE_ACTIVE, LIFECYCLE_DELETION_PENDING, LIFECYCLE_DELETED},
        LIFECYCLE_DELETION_PENDING: {LIFECYCLE_DELETED},
        LIFECYCLE_DELETED: set(),
        # Support legacy transitions:
        'active': {LIFECYCLE_ACTIVE, LIFECYCLE_SUSPENDED, LIFECYCLE_CANCELLED, LIFECYCLE_PAST_DUE, LIFECYCLE_RESTRICTED},
        'trial': {LIFECYCLE_ACTIVE, LIFECYCLE_SUSPENDED, LIFECYCLE_CANCELLED, LIFECYCLE_TRIAL},
        'suspended': {LIFECYCLE_ACTIVE, LIFECYCLE_CANCELLED, LIFECYCLE_DELETION_PENDING, LIFECYCLE_SUSPENDED},
    }

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='small')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=LIFECYCLE_ACTIVE)
    version = models.PositiveIntegerField(default=1, help_text='Optimistic concurrency control version')
    suspension_reason = models.TextField(blank=True, default='')
    suspended_at = models.DateTimeField(null=True, blank=True)
    deletion_requested_at = models.DateTimeField(null=True, blank=True)
    max_numbers = models.PositiveIntegerField(default=1)
    max_users = models.PositiveIntegerField(default=3)
    max_campaigns_monthly = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.get_tier_display()}) [{self.status}]'

    @property
    def normalized_status(self):
        return (self.status or '').upper()

    @property
    def is_operational(self):
        return self.normalized_status in (self.LIFECYCLE_ACTIVE, self.LIFECYCLE_TRIAL, 'ACTIVE', 'TRIAL')

    @property
    def is_suspended(self):
        return self.normalized_status in (self.LIFECYCLE_SUSPENDED, 'SUSPENDED')

    @property
    def is_restricted(self):
        return self.normalized_status in (self.LIFECYCLE_RESTRICTED, self.LIFECYCLE_PAST_DUE, 'RESTRICTED', 'PAST_DUE')

    @property
    def is_deleted(self):
        return self.normalized_status in (self.LIFECYCLE_DELETED, self.LIFECYCLE_DELETION_PENDING, 'DELETED')

    def can_transition_to(self, target_status):
        target = target_status.upper()
        current = self.status
        allowed = self.PERMITTED_TRANSITIONS.get(current, self.PERMITTED_TRANSITIONS.get(self.normalized_status, set()))
        return target in allowed

    def apply_tier_defaults(self):
        if self.tier == 'small':
            self.max_numbers = 1
            self.max_users = 3
            self.max_campaigns_monthly = 5
        elif self.tier == 'mid':
            self.max_numbers = 5
            self.max_users = 15
            self.max_campaigns_monthly = 50
        elif self.tier == 'large':
            self.max_numbers = 25
            self.max_users = 100
            self.max_campaigns_monthly = 500


class TenantMembership(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('invited', 'Invited'),
        ('suspended', 'Suspended'),
    ]
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='memberships')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=50, default='agent')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_owner = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'tenant'], name='unique_user_tenant_membership')
        ]
        ordering = ['tenant', 'user']

    def __str__(self):
        return f'{self.user.email} in {self.tenant.name} ({self.role})'


class TenantLifecycleHistory(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='lifecycle_history')
    from_status = models.CharField(max_length=30)
    to_status = models.CharField(max_length=30)
    reason = models.TextField(blank=True, default='')
    actor = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='lifecycle_transitions')
    actor_email = models.EmailField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.tenant.name}: {self.from_status} -> {self.to_status} ({self.created_at})'


class User(AbstractUser):
    ROLE_CHOICES = [
        ('viewer', 'Viewer'), ('editor', 'Editor'),
        ('admin', 'Administrator'), ('owner', 'Owner'),
    ]
    NUMBER_ACCESS_CHOICES = [
        ('india', 'India number'), ('us', 'US number'), ('both', 'Both numbers'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    organization = models.CharField(max_length=150, blank=True, null=True)
    team_name = models.CharField(max_length=50, default='Support')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='viewer')
    number_access = models.CharField(max_length=10, choices=NUMBER_ACCESS_CHOICES, default='both')
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=64, blank=True, default='')
    mfa_recovery_codes = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


class SMTPConfiguration(models.Model):
    SECURITY_CHOICES = [('starttls', 'STARTTLS'), ('ssl', 'SSL/TLS'), ('none', 'None')]
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    enabled = models.BooleanField(default=False)
    host = models.CharField(max_length=255)
    port = models.PositiveIntegerField(default=587)
    security = models.CharField(max_length=10, choices=SECURITY_CHOICES, default='starttls')
    use_authentication = models.BooleanField(default=True)
    username_encrypted = models.TextField(blank=True, editable=False)
    password_encrypted = models.TextField(blank=True, editable=False)
    from_email = models.EmailField(verbose_name='Sender email')
    from_name = models.CharField(max_length=150, blank=True, verbose_name='Sender name')
    timeout = models.PositiveIntegerField(default=15, help_text='Connection timeout in seconds (1–120).')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'SMTP configuration'
        verbose_name_plural = 'SMTP configuration'
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name='single_smtp_configuration')]

    def __str__(self):
        return 'Invitation SMTP configuration'

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        if not 1 <= self.port <= 65535:
            errors['port'] = 'Enter a port between 1 and 65535.'
        if not 1 <= self.timeout <= 120:
            errors['timeout'] = 'Enter a timeout between 1 and 120 seconds.'
        if any(character in self.from_name for character in ('\r', '\n')):
            errors['from_name'] = 'The sender name cannot contain line breaks.'
        if self.enabled and self.use_authentication and not (self.username_encrypted and self.password_encrypted):
            errors['use_authentication'] = 'Provide both an SMTP username and password before enabling authentication.'
        if errors:
            raise ValidationError(errors)
