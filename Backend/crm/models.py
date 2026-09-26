import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


class Customer(models.Model):
    """
    Customer entity representing the individual or company in Convernix CRM.
    Maintains encrypted PII (AES-256-GCM) with HMAC blind indexes for exact match searching.
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('PROSPECT', 'Prospect'),
        ('CUSTOMER', 'Customer'),
        ('CHURNED', 'Churned'),
        ('INACTIVE', 'Inactive'),
    ]

    customer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='crm_customers', db_index=True)
    display_name = models.CharField(max_length=255, blank=True, default='')
    first_name_encrypted = models.TextField(blank=True, default='')
    last_name_encrypted = models.TextField(blank=True, default='')
    phone_encrypted = models.TextField(blank=True, default='')
    phone_lookup_hash = models.CharField(max_length=64, blank=True, default='', db_index=True)
    email_encrypted = models.TextField(blank=True, default='')
    email_lookup_hash = models.CharField(max_length=64, blank=True, default='', db_index=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='ACTIVE', db_index=True)
    source = models.CharField(max_length=50, default='WHATSAPP', db_index=True)
    legacy_whatsapp_customer = models.ForeignKey(
        'whatsapp.Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='crm_customer_links'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    version = models.PositiveIntegerField(default=1, help_text='Optimistic locking version')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status', 'created_at']),
            models.Index(fields=['tenant', 'phone_lookup_hash']),
            models.Index(fields=['tenant', 'email_lookup_hash']),
            models.Index(fields=['tenant', 'deleted_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'phone_lookup_hash'],
                condition=models.Q(deleted_at__isnull=True) & ~models.Q(phone_lookup_hash=''),
                name='unique_tenant_crm_customer_phone_hash',
            ),
        ]

    def __str__(self):
        return self.display_name or self.plain_full_name or 'CRM Customer'

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.version += 1
        self.save(update_fields=['deleted_at', 'version', 'updated_at'])

    def get_decrypted(self, field_name: str) -> str:
        val = getattr(self, field_name, '')
        if not val or not self.tenant:
            return val or ''
        if isinstance(val, str) and (val.startswith('cvx:v') or val.startswith('gAAAAA')):
            from organization.services.crypto_service import decrypt_tenant_data
            try:
                return decrypt_tenant_data(self.tenant, val)
            except Exception:
                return val
        return val

    @property
    def plain_phone(self) -> str:
        return self.get_decrypted('phone_encrypted')

    @property
    def plain_email(self) -> str:
        return self.get_decrypted('email_encrypted')

    @property
    def plain_first_name(self) -> str:
        return self.get_decrypted('first_name_encrypted')

    @property
    def plain_last_name(self) -> str:
        return self.get_decrypted('last_name_encrypted')

    @property
    def plain_full_name(self) -> str:
        first = self.plain_first_name
        last = self.plain_last_name
        combined = f'{first} {last}'.strip()
        return combined or self.display_name

    @property
    def masked_phone(self) -> str:
        from organization.services.masking_service import MaskingService
        return MaskingService.mask_phone(self.plain_phone)

    @property
    def masked_email(self) -> str:
        from organization.services.masking_service import MaskingService
        return MaskingService.mask_email(self.plain_email)

    def set_plain_phone(self, phone: str):
        if not phone:
            self.phone_encrypted = ''
            self.phone_lookup_hash = ''
            return
        from organization.services.crypto_service import compute_blind_index, encrypt_tenant_data, normalize_search_term
        canonical = normalize_search_term(phone, 'phone')
        self.phone_lookup_hash = compute_blind_index(self.tenant, canonical, 'phone')
        self.phone_encrypted = encrypt_tenant_data(self.tenant, canonical)

    def set_plain_email(self, email: str):
        if not email:
            self.email_encrypted = ''
            self.email_lookup_hash = ''
            return
        from organization.services.crypto_service import compute_blind_index, encrypt_tenant_data, normalize_search_term
        canonical = normalize_search_term(email, 'email')
        self.email_lookup_hash = compute_blind_index(self.tenant, canonical, 'email')
        self.email_encrypted = encrypt_tenant_data(self.tenant, canonical)

    def set_plain_names(self, first_name: str, last_name: str = ''):
        from organization.services.crypto_service import encrypt_tenant_data
        if first_name:
            self.first_name_encrypted = encrypt_tenant_data(self.tenant, first_name.strip())
        if last_name:
            self.last_name_encrypted = encrypt_tenant_data(self.tenant, last_name.strip())
        combined = f'{first_name} {last_name}'.strip()
        if combined and not self.display_name:
            self.display_name = combined


class CustomerIdentity(models.Model):
    """
    Multiple provider identities linked to a Customer.
    Supports WHATSAPP, PHONE, EMAIL, EXTERNAL_CRM.
    """
    PROVIDER_CHOICES = [
        ('WHATSAPP', 'WhatsApp'),
        ('PHONE', 'Phone'),
        ('EMAIL', 'Email'),
        ('EXTERNAL_CRM', 'External CRM'),
        ('FACEBOOK', 'Facebook'),
        ('INSTAGRAM', 'Instagram'),
    ]

    identity_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='crm_identities', db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='identities', db_index=True)
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, db_index=True)
    identifier_encrypted = models.TextField()
    lookup_hash = models.CharField(max_length=64, db_index=True)
    is_primary = models.BooleanField(default=False)
    verified = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'provider', 'lookup_hash']),
            models.Index(fields=['customer', 'provider']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'provider', 'lookup_hash'],
                name='unique_tenant_identity_provider_hash',
            ),
        ]

    def __str__(self):
        return f'{self.provider} identity for Customer {self.customer_id}'

    @property
    def plain_identifier(self) -> str:
        if not self.identifier_encrypted or not self.tenant:
            return ''
        if str(self.identifier_encrypted).startswith('cvx:v') or str(self.identifier_encrypted).startswith('gAAAAA'):
            from organization.services.crypto_service import decrypt_tenant_data
            try:
                return decrypt_tenant_data(self.tenant, self.identifier_encrypted)
            except Exception:
                return self.identifier_encrypted
        return self.identifier_encrypted


class Pipeline(models.Model):
    """
    Configurable CRM sales/service pipeline per tenant.
    """
    pipeline_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='crm_pipelines', db_index=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'name'], name='unique_tenant_pipeline_name'),
        ]

    def __str__(self):
        return f'{self.name} ({self.tenant.name})'


class PipelineStage(models.Model):
    """
    Configurable stage within a Pipeline.
    Supports win/lost/open classification, color coding, and terminal states.
    """
    CLASSIFICATION_CHOICES = [
        ('OPEN', 'Open'),
        ('WON', 'Won'),
        ('LOST', 'Lost'),
    ]

    stage_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='crm_stages', db_index=True)
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name='stages', db_index=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_terminal = models.BooleanField(default=False)
    classification = models.CharField(max_length=20, default='OPEN', choices=CLASSIFICATION_CHOICES)
    color = models.CharField(max_length=30, default='#3b82f6')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['pipeline', 'display_order', 'created_at']
        constraints = [
            models.UniqueConstraint(fields=['pipeline', 'name'], name='unique_pipeline_stage_name'),
        ]

    def __str__(self):
        return f'{self.pipeline.name} -> {self.name}'


class Lead(models.Model):
    """
    Lead entity representing a business/service opportunity or lifecycle instance associated with a Customer.
    One Customer may have multiple Leads over time.
    """
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('WON', 'Won'),
        ('LOST', 'Lost'),
        ('ARCHIVED', 'Archived'),
    ]

    lead_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='crm_leads', db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='leads', db_index=True)
    pipeline = models.ForeignKey(Pipeline, on_delete=models.PROTECT, related_name='leads', db_index=True)
    stage = models.ForeignKey(PipelineStage, on_delete=models.PROTECT, related_name='leads', db_index=True)
    department = models.ForeignKey(
        'whatsapp.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='crm_leads', db_index=True
    )
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_crm_leads', db_index=True
    )
    source = models.CharField(max_length=50, default='WHATSAPP', db_index=True)
    priority = models.CharField(max_length=20, default='MEDIUM', choices=PRIORITY_CHOICES, db_index=True)
    status = models.CharField(max_length=20, default='OPEN', choices=STATUS_CHOICES, db_index=True)
    title = models.CharField(max_length=255)
    estimated_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default='INR')
    win_probability = models.PositiveSmallIntegerField(default=0)
    closed_at = models.DateTimeField(null=True, blank=True)
    last_contacted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    version = models.PositiveIntegerField(default=1, help_text='Optimistic locking version')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status', 'created_at']),
            models.Index(fields=['tenant', 'owner_user', 'status']),
            models.Index(fields=['tenant', 'department', 'status']),
            models.Index(fields=['tenant', 'stage']),
            models.Index(fields=['tenant', 'customer', 'status']),
            models.Index(fields=['tenant', 'deleted_at']),
        ]

    def __str__(self):
        return f'{self.title} ({self.customer.display_name or self.customer_id})'

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.version += 1
        self.save(update_fields=['deleted_at', 'version', 'updated_at'])


class LeadFollower(models.Model):
    """
    Users following / watching a specific lead.
    """
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='followers')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='crm_lead_follows')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['lead', 'user'], name='unique_crm_lead_follower'),
        ]


class LeadStageHistory(models.Model):
    """
    Audit history for lead stage transitions.
    """
    history_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='stage_history')
    from_stage = models.ForeignKey(PipelineStage, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    to_stage = models.ForeignKey(PipelineStage, on_delete=models.PROTECT, related_name='+')
    actor_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    actor_name = models.CharField(max_length=150, blank=True, default='')
    reason = models.TextField(blank=True, default='')
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']


class LeadAssignmentHistory(models.Model):
    """
    Audit history for lead ownership and department changes.
    """
    history_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='assignment_history')
    from_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    to_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    from_department = models.ForeignKey('whatsapp.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    to_department = models.ForeignKey('whatsapp.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    assignment_method = models.CharField(max_length=30, default='MANUAL')
    reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']


class CustomFieldDefinition(models.Model):
    """
    Tenant-configurable custom field schema definition for Customers or Leads.
    """
    ENTITY_TYPE_CHOICES = [
        ('CUSTOMER', 'Customer'),
        ('LEAD', 'Lead'),
    ]
    FIELD_TYPE_CHOICES = [
        ('TEXT', 'Text'),
        ('TEXTAREA', 'Text Area'),
        ('NUMBER', 'Number'),
        ('DECIMAL', 'Decimal'),
        ('BOOLEAN', 'Boolean'),
        ('DATE', 'Date'),
        ('DATETIME', 'Date Time'),
        ('EMAIL', 'Email'),
        ('PHONE', 'Phone'),
        ('URL', 'URL'),
        ('SELECT', 'Select'),
        ('MULTI_SELECT', 'Multi Select'),
    ]

    field_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='crm_custom_field_definitions', db_index=True)
    entity_type = models.CharField(max_length=20, default='CUSTOMER', choices=ENTITY_TYPE_CHOICES, db_index=True)
    field_name = models.CharField(max_length=100)
    field_label = models.CharField(max_length=150)
    field_type = models.CharField(max_length=30, choices=FIELD_TYPE_CHOICES)
    is_required = models.BooleanField(default=False)
    is_unique = models.BooleanField(default=False)
    is_searchable = models.BooleanField(default=False)
    is_sensitive_pii = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)
    is_editable = models.BooleanField(default=True)
    default_value = models.JSONField(null=True, blank=True)
    validation_rules = models.JSONField(default=dict, blank=True)
    options = models.JSONField(default=list, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['entity_type', 'display_order', 'field_label']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'entity_type', 'field_name'], name='unique_tenant_crm_field_name'),
        ]

    def __str__(self):
        return f'{self.entity_type} -> {self.field_label} ({self.field_name})'


class CustomFieldValue(models.Model):
    """
    Stored value for a CustomFieldDefinition on a Customer or Lead.
    Values marked sensitive are encrypted using AES-256-GCM.
    """
    value_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, db_index=True)
    definition = models.ForeignKey(CustomFieldDefinition, on_delete=models.CASCADE, related_name='values', db_index=True)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.CASCADE, related_name='custom_field_values', db_index=True)
    lead = models.ForeignKey(Lead, null=True, blank=True, on_delete=models.CASCADE, related_name='custom_field_values', db_index=True)
    value_text = models.TextField(blank=True, default='')
    value_encrypted = models.TextField(blank=True, default='')
    value_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'customer']),
            models.Index(fields=['tenant', 'lead']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['definition', 'customer'],
                condition=models.Q(customer__isnull=False),
                name='unique_def_customer_val',
            ),
            models.UniqueConstraint(
                fields=['definition', 'lead'],
                condition=models.Q(lead__isnull=False),
                name='unique_def_lead_val',
            ),
        ]

    def get_plain_value(self):
        if self.definition.is_sensitive_pii and self.value_encrypted and self.tenant:
            from organization.services.crypto_service import decrypt_tenant_data
            try:
                return decrypt_tenant_data(self.tenant, self.value_encrypted)
            except Exception:
                return self.value_encrypted
        if self.value_json is not None:
            return self.value_json
        return self.value_text


class Tag(models.Model):
    """
    Tenant-scoped CRM tag entity.
    """
    tag_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='crm_tags', db_index=True)
    name = models.CharField(max_length=60)
    color = models.CharField(max_length=30, default='#6366f1')
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'name'], name='unique_tenant_crm_tag_name'),
        ]

    def __str__(self):
        return f'{self.name} ({self.tenant.name})'


class CustomerTag(models.Model):
    """
    Normalized customer tag assignment.
    """
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='customer_tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='customer_assignments')
    tagged_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['customer', 'tag'], name='unique_customer_tag'),
        ]


class LeadTag(models.Model):
    """
    Normalized lead tag assignment.
    """
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='lead_tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='lead_assignments')
    tagged_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['lead', 'tag'], name='unique_lead_tag'),
        ]


class Activity(models.Model):
    """
    CRM Activity timeline entry for Customer and/or Lead.
    """
    activity_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='crm_activities', db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='activities', db_index=True)
    lead = models.ForeignKey(Lead, null=True, blank=True, on_delete=models.CASCADE, related_name='activities', db_index=True)
    activity_type = models.CharField(max_length=50, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='performed_crm_activities'
    )
    actor_name = models.CharField(max_length=150, blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'customer', 'created_at']),
            models.Index(fields=['tenant', 'lead', 'created_at']),
            models.Index(fields=['tenant', 'activity_type', 'created_at']),
        ]

    def __str__(self):
        return f'[{self.activity_type}] {self.title}'


class Note(models.Model):
    """
    User-created CRM Note attached to Customer or Lead.
    Encrypted using AES-256-GCM.
    """
    note_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='crm_notes', db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='notes', db_index=True)
    lead = models.ForeignKey(Lead, null=True, blank=True, on_delete=models.CASCADE, related_name='notes', db_index=True)
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='authored_crm_notes')
    content_encrypted = models.TextField()
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['tenant', 'customer', 'created_at']),
            models.Index(fields=['tenant', 'lead', 'created_at']),
        ]

    def __str__(self):
        return f'Note on Customer {self.customer_id} by {self.author_user.email}'

    @property
    def plain_content(self) -> str:
        if not self.content_encrypted or not self.tenant:
            return ''
        if str(self.content_encrypted).startswith('cvx:v') or str(self.content_encrypted).startswith('gAAAAA'):
            from organization.services.crypto_service import decrypt_tenant_data
            try:
                return decrypt_tenant_data(self.tenant, self.content_encrypted)
            except Exception:
                return self.content_encrypted
        return self.content_encrypted

    def set_content(self, text: str):
        if not text:
            self.content_encrypted = ''
            return
        from organization.services.crypto_service import encrypt_tenant_data
        self.content_encrypted = encrypt_tenant_data(self.tenant, text)


class CustomerMergeHistory(models.Model):
    """
    Audit log of customer merge operations preserving all prior identity links and relationships.
    """
    merge_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='customer_merges', db_index=True)
    primary_customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='merges_as_primary')
    secondary_customer_id = models.UUIDField()
    merged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    merged_data_snapshot = models.JSONField(default=dict)
    reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Merge into {self.primary_customer_id} from {self.secondary_customer_id}'
