import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class WhatsAppConfiguration(models.Model):
    """Database-backed Meta/WhatsApp credentials for one business number."""

    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='whatsapp_configurations', null=True, blank=True)
    business_number = models.CharField('WHATSAPP_BUSINESS_NUMBER', max_length=20, unique=True)
    default_team = models.CharField('DEFAULT_TEAM', max_length=50, default='Support')
    meta_app_id = models.CharField('META_APP_ID', max_length=100, blank=True, default='')
    phone_number_id = models.CharField('WHATSAPP_PHONE_NUMBER_ID', max_length=100, blank=True, default='')
    business_account_id = models.CharField('WABA_ID', max_length=100, blank=True, default='')
    api_version = models.CharField('WHATSAPP_API_VERSION', max_length=20, default='v23.0')
    verify_token = models.CharField('WHATSAPP_VERIFY_TOKEN', max_length=255, blank=True, default='')
    webhook_secret = models.CharField('META_APP_SECRET', max_length=255, blank=True, default='')
    meta_access_token = models.TextField('WHATSAPP_ACCESS_TOKEN', blank=True, default='')
    notification_template = models.CharField(
        'WHATSAPP_TEMPLATE_NAME', max_length=150, default='new_lead_notification',
    )
    template_language = models.CharField('WHATSAPP_TEMPLATE_LANGUAGE', max_length=20, default='en')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'WhatsApp configuration'
        verbose_name_plural = 'WhatsApp configuration'

    @classmethod
    def load(cls):
        """Return the first configuration for backwards-compatible callers."""
        return cls.objects.order_by('pk').first()

    @classmethod
    def for_business_number(cls, number):
        normalized = ''.join(character for character in (number or '') if character.isdigit())
        for configuration in cls.objects.all():
            candidate = ''.join(character for character in configuration.business_number if character.isdigit())
            if candidate == normalized:
                return configuration
        # Meta test/display numbers can differ from the registered account number.
        # BusinessNumber stores the explicit display-number -> phone-number-ID link.
        for business_number in BusinessNumber.objects.exclude(phone_number_id=''):
            candidate = ''.join(character for character in business_number.number if character.isdigit())
            if candidate == normalized:
                return cls.objects.filter(phone_number_id=business_number.phone_number_id).first()
        return None

    @classmethod
    def for_webhook(cls, number, phone_number_id=''):
        if phone_number_id:
            configuration = cls.objects.filter(phone_number_id=phone_number_id).first()
            if configuration:
                return configuration
        return cls.for_business_number(number)

    def __str__(self):
        return self.business_number


class BusinessNumber(models.Model):
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='business_numbers', null=True, blank=True)
    number = models.CharField(max_length=20, unique=True)
    phone_number_id = models.CharField(max_length=100, blank=True, default='')
    forwarding_number = models.CharField(
        max_length=20, blank=True, default='',
        help_text='Recipient number for enquiries received on this business number, in E.164 format.',
    )
    label = models.CharField(max_length=150, blank=True, default='Main WhatsApp Number')
    default_team = models.CharField(max_length=50, default='Support')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.number


class Department(models.Model):
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='departments', null=True, blank=True)
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=60)
    description = models.TextField(blank=True, default='')
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_departments')
    business_hours = models.JSONField(default=dict, blank=True, help_text='Schedule e.g. {"mon": {"start": "09:00", "end": "18:00"}}')
    is_active = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'name'], name='unique_tenant_department_name'),
            models.UniqueConstraint(fields=['tenant', 'slug'], name='unique_tenant_department_slug'),
        ]

    def __str__(self):
        return f'{self.name} ({self.tenant.name if self.tenant else "Global"})'



class DepartmentMember(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    whatsapp_number = models.CharField(max_length=20)
    active = models.BooleanField(default=True)
    notification_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ['department__name', 'name']
        constraints = [
            models.UniqueConstraint(fields=['department', 'whatsapp_number'], name='unique_department_recipient'),
        ]

    def __str__(self):
        return f'{self.department}: {self.name}'


class EncryptedCustomerManager(models.Manager):
    def find_by_phone(self, tenant, raw_phone):
        if not raw_phone or not tenant:
            return None
        from organization.services.crypto_service import compute_blind_index
        phone_hash = compute_blind_index(tenant, raw_phone, 'phone')
        return self.filter(tenant=tenant, phone_hash=phone_hash).first()

    def find_by_email(self, tenant, raw_email):
        if not raw_email or not tenant:
            return None
        from organization.services.crypto_service import compute_blind_index
        email_hash = compute_blind_index(tenant, raw_email, 'email')
        return self.filter(tenant=tenant, email_hash=email_hash).first()


class Customer(models.Model):
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='customers', null=True, blank=True)
    whatsapp_number = models.TextField(blank=True)
    phone_hash = models.CharField(max_length=64, blank=True, db_index=True)
    full_name = models.TextField(blank=True)
    organization_name = models.TextField(blank=True)
    email = models.TextField(blank=True)
    email_hash = models.CharField(max_length=64, blank=True, db_index=True)
    consent_status = models.CharField(max_length=30, default='ACTIVE', choices=[('ACTIVE', 'Active'), ('WITHDRAWN', 'Withdrawn')])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EncryptedCustomerManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'phone_hash'], name='unique_tenant_customer_phone_hash'),
        ]

    def __str__(self):
        return self.plain_name or self.plain_phone or 'Customer'

    def get_decrypted_field(self, field_name):
        val = getattr(self, field_name, '')
        if val and isinstance(val, str) and val.startswith('cvx:v') and self.tenant:
            from organization.services.crypto_service import decrypt_tenant_data
            try:
                return decrypt_tenant_data(self.tenant, val)
            except Exception:
                return val
        return val

    @property
    def plain_phone(self):
        return self.get_decrypted_field('whatsapp_number')

    @property
    def plain_name(self):
        return self.get_decrypted_field('full_name')

    @property
    def plain_email(self):
        return self.get_decrypted_field('email')

    @property
    def plain_organization(self):
        return self.get_decrypted_field('organization_name')

    def save(self, *args, **kwargs):
        if self.tenant:
            from organization.services.crypto_service import compute_blind_index, encrypt_tenant_data
            if self.whatsapp_number and not str(self.whatsapp_number).startswith('cvx:v'):
                self.phone_hash = compute_blind_index(self.tenant, self.whatsapp_number, 'phone')
                self.whatsapp_number = encrypt_tenant_data(self.tenant, self.whatsapp_number)
            if self.email and not str(self.email).startswith('cvx:v'):
                self.email_hash = compute_blind_index(self.tenant, self.email, 'email')
                self.email = encrypt_tenant_data(self.tenant, self.email)
            if self.full_name and not str(self.full_name).startswith('cvx:v'):
                self.full_name = encrypt_tenant_data(self.tenant, self.full_name)
            if self.organization_name and not str(self.organization_name).startswith('cvx:v'):
                self.organization_name = encrypt_tenant_data(self.tenant, self.organization_name)
        super().save(*args, **kwargs)


class Enquiry(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'), ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'), ('closed', 'Closed'),
    ]
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='enquiries', null=True, blank=True)
    reference = models.CharField(max_length=30, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='enquiries')
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='enquiries')
    message = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='new')
    source = models.CharField(max_length=30, default='whatsapp')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f'ENQ-{uuid.uuid4().hex[:12].upper()}'
        if self.tenant and self.message and not str(self.message).startswith('cvx:v'):
            from organization.services.crypto_service import encrypt_tenant_data
            self.message = encrypt_tenant_data(self.tenant, self.message)
        super().save(*args, **kwargs)

    @property
    def plain_message(self):
        if self.message and str(self.message).startswith('cvx:v') and self.tenant:
            from organization.services.crypto_service import decrypt_tenant_data
            try:
                return decrypt_tenant_data(self.tenant, self.message)
            except Exception:
                return self.message
        return self.message

    def __str__(self):
        return self.reference


class WhatsAppMessage(models.Model):
    DIRECTION_CHOICES = [('incoming', 'Incoming'), ('outgoing', 'Outgoing')]
    STATUS_CHOICES = [
        ('received', 'Received'), ('queued', 'Queued'), ('sent', 'Sent'),
        ('delivered', 'Delivered'), ('read', 'Read'), ('failed', 'Failed'),
    ]
    whatsapp_message_id = models.CharField(max_length=255, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True, related_name='messages')
    enquiry = models.ForeignKey(Enquiry, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES)
    message_type = models.CharField(max_length=30)
    content = models.TextField(blank=True)
    attachment = models.FileField(upload_to='conversation_attachments/%Y/%m/%d/', blank=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    attachment_content_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received')
    raw_payload = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    seen_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def save(self, *args, **kwargs):
        tenant = getattr(self.customer, 'tenant', None) or getattr(getattr(self.enquiry, 'customer', None), 'tenant', None)
        if tenant and self.content and not str(self.content).startswith('cvx:v'):
            from organization.services.crypto_service import encrypt_tenant_data
            self.content = encrypt_tenant_data(tenant, self.content)
        super().save(*args, **kwargs)

    @property
    def plain_content(self):
        tenant = getattr(self.customer, 'tenant', None) or getattr(getattr(self.enquiry, 'customer', None), 'tenant', None)
        if self.content and str(self.content).startswith('cvx:v') and tenant:
            from organization.services.crypto_service import decrypt_tenant_data
            try:
                return decrypt_tenant_data(tenant, self.content)
            except Exception:
                return self.content
        return self.content


class Notification(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'), ('processing', 'Processing'), ('sent', 'Sent'),
        ('delivered', 'Delivered'), ('read', 'Read'), ('failed', 'Failed'),
        ('permanently_failed', 'Permanently failed'),
    ]
    enquiry = models.ForeignKey(Enquiry, on_delete=models.CASCADE, related_name='notifications')
    recipient = models.ForeignKey(DepartmentMember, on_delete=models.PROTECT, related_name='notifications')
    recipient_number = models.CharField(max_length=20, blank=True)
    template_name = models.CharField(max_length=150, blank=True)
    whatsapp_message_id = models.CharField(max_length=255, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    http_status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    error_subcode = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    fbtrace_id = models.CharField(max_length=100, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['enquiry', 'recipient'], name='unique_enquiry_recipient_notification'),
        ]


class RoutingRule(models.Model):
    business_number = models.ForeignKey(BusinessNumber, on_delete=models.CASCADE, related_name='routing_rules')
    keyword = models.CharField(max_length=100)
    team_name = models.CharField(max_length=50)
    assigned_role = models.CharField(max_length=30, default='support')
    priority = models.PositiveSmallIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-priority', 'keyword']

    def __str__(self):
        return f'{self.business_number.number}: {self.keyword} -> {self.team_name}'


class Lead(models.Model):
    """Backward-compatible dashboard projection for enquiries."""
    STATUS_CHOICES = [
        ('new', 'New'), ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'), ('resolved', 'Resolved'),
    ]
    business_number = models.ForeignKey(BusinessNumber, on_delete=models.CASCADE, related_name='leads')
    enquiry = models.OneToOneField(Enquiry, on_delete=models.SET_NULL, null=True, blank=True, related_name='legacy_lead')
    customer_name = models.TextField(blank=True, default='')
    phone_number = models.TextField(blank=True)
    phone_hash = models.CharField(max_length=64, blank=True, db_index=True)
    customer_email = models.TextField(blank=True, null=True)
    email_hash = models.CharField(max_length=64, blank=True, db_index=True)
    message = models.TextField(blank=True)
    team_name = models.CharField(max_length=50, default='Support')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_leads')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='new')
    source = models.CharField(max_length=30, default='whatsapp')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.plain_customer_name or self.plain_phone_number} -> {self.team_name}'

    def _get_tenant(self):
        return getattr(getattr(self, 'business_number', None), 'tenant', None)

    def get_decrypted(self, field_name):
        val = getattr(self, field_name, '')
        tenant = self._get_tenant()
        if val and isinstance(val, str) and val.startswith('cvx:v') and tenant:
            from organization.services.crypto_service import decrypt_tenant_data
            try:
                return decrypt_tenant_data(tenant, val)
            except Exception:
                return val
        return val

    @property
    def plain_customer_name(self):
        return self.get_decrypted('customer_name')

    @property
    def plain_phone_number(self):
        return self.get_decrypted('phone_number')

    @property
    def plain_customer_email(self):
        return self.get_decrypted('customer_email')

    @property
    def plain_message(self):
        return self.get_decrypted('message')

    def save(self, *args, **kwargs):
        tenant = self._get_tenant()
        if tenant:
            from organization.services.crypto_service import compute_blind_index, encrypt_tenant_data
            if self.phone_number and not str(self.phone_number).startswith('cvx:v'):
                self.phone_hash = compute_blind_index(tenant, self.phone_number, 'phone')
                self.phone_number = encrypt_tenant_data(tenant, self.phone_number)
            if self.customer_email and not str(self.customer_email).startswith('cvx:v'):
                self.email_hash = compute_blind_index(tenant, self.customer_email, 'email')
                self.customer_email = encrypt_tenant_data(tenant, self.customer_email)
            if self.customer_name and not str(self.customer_name).startswith('cvx:v'):
                self.customer_name = encrypt_tenant_data(tenant, self.customer_name)
            if self.message and not str(self.message).startswith('cvx:v'):
                self.message = encrypt_tenant_data(tenant, self.message)
        super().save(*args, **kwargs)


class AutomationRule(models.Model):
    RULE_TYPE_CHOICES = [
        ('welcome', 'Incoming Welcome Auto-responder'),
        ('keyword_routing', 'Keyword-based Department Routing'),
        ('out_of_hours', 'Out-of-hours Auto-reply'),
        ('escalation', 'Lead Escalation Trigger'),
    ]
    business_number = models.ForeignKey(BusinessNumber, on_delete=models.CASCADE, related_name='automation_rules')
    rule_type = models.CharField(max_length=30, choices=RULE_TYPE_CHOICES)
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    trigger_desc = models.CharField(max_length=255, blank=True)
    action_desc = models.CharField(max_length=255, blank=True)
    config = models.JSONField(default=dict, blank=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(fields=['business_number', 'rule_type'], name='unique_business_rule_type'),
        ]

    def __str__(self):
        return f'{self.business_number.number}: {self.name} ({self.rule_type})'

    @classmethod
    def get_or_create_defaults(cls, business_number):
        """Ensure the 4 standard automation workflows exist for the business number."""
        defaults = [
            {
                'rule_type': 'welcome',
                'name': 'Incoming Welcome Auto-responder',
                'trigger_desc': 'On first message from new customer',
                'action_desc': 'Send warm greeting and request details',
                'config': {
                    'message': 'Hello! Thanks for reaching out to us on WhatsApp. How can our team assist you today?',
                },
            },
            {
                'rule_type': 'keyword_routing',
                'name': 'Keyword-based Department Routing',
                'trigger_desc': 'Message contains "demo", "pricing", or "quote"',
                'action_desc': 'Instantly route to Sales department queue',
                'config': {
                    'routes': [
                        {'keyword': 'demo', 'team': 'Sales'},
                        {'keyword': 'pricing', 'team': 'Sales'},
                        {'keyword': 'quote', 'team': 'Sales'},
                        {'keyword': 'help', 'team': 'Support'},
                        {'keyword': 'support', 'team': 'Support'},
                        {'keyword': 'billing', 'team': 'Billing'},
                        {'keyword': 'invoice', 'team': 'Billing'},
                        {'keyword': 'career', 'team': 'HR'},
                        {'keyword': 'job', 'team': 'HR'},
                    ],
                },
            },
            {
                'rule_type': 'out_of_hours',
                'name': 'Out-of-hours Auto-reply',
                'trigger_desc': 'Inbound message outside 9 AM – 6 PM',
                'action_desc': 'Inform sender of business hours and expected SLA',
                'config': {
                    'start_hour': 9,
                    'end_hour': 18,
                    'message': 'Thank you for your message! Our office hours are Monday to Friday, 9:00 AM – 6:00 PM. We have received your inquiry and our team will get back to you shortly.',
                },
            },
            {
                'rule_type': 'escalation',
                'name': 'Lead Escalation Trigger',
                'trigger_desc': 'No agent response within 15 minutes',
                'action_desc': 'Notify department supervisor and mark Priority',
                'config': {
                    'timeout_minutes': 15,
                },
            },
        ]
        created_rules = []
        for item in defaults:
            rule, _ = cls.objects.get_or_create(
                business_number=business_number,
                rule_type=item['rule_type'],
                defaults={
                    'name': item['name'],
                    'trigger_desc': item['trigger_desc'],
                    'action_desc': item['action_desc'],
                    'config': item['config'],
                    'is_active': True,
                },
            )
            created_rules.append(rule)
        return created_rules

