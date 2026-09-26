import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class ServiceAccount(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('disabled', 'Disabled'),
        ('revoked', 'Revoked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='service_accounts')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='active', db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_service_accounts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
        ]

    def __str__(self):
        return f'{self.name} ({self.tenant.name}) [{self.status}]'

    @property
    def is_active(self):
        return self.status == 'active' and (not self.tenant or self.tenant.is_operational)


class ApiKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='integration_api_keys')
    service_account = models.ForeignKey(ServiceAccount, on_delete=models.CASCADE, related_name='api_keys', null=True, blank=True)
    name = models.CharField(max_length=120)
    key_prefix = models.CharField(max_length=32, db_index=True, help_text='Safe prefix e.g. cvx_live_ab12')
    secret_hash = models.CharField(max_length=128, db_index=True, help_text='SHA-256 hash of plaintext secret')
    scopes = models.JSONField(default=list, blank=True, help_text='List of granted scope strings e.g. ["lead:read", "lead:create"]')
    ip_restrictions = models.JSONField(default=list, blank=True, help_text='Optional list of allowed CIDR/IP addresses')
    is_active = models.BooleanField(default=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='revoked_api_keys')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_integration_api_keys')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'key_prefix']),
            models.Index(fields=['tenant', 'is_active']),
        ]

    def __str__(self):
        return f'{self.name} ({self.key_prefix}...) [{self.tenant.name}]'

    @property
    def is_valid(self):
        if not self.is_active or self.revoked_at is not None:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        if self.service_account and not self.service_account.is_active:
            return False
        if not self.tenant or not self.tenant.is_operational:
            return False
        return True


class IdempotencyRecord(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='idempotency_records')
    credential_id = models.CharField(max_length=128, db_index=True)
    idempotency_key = models.CharField(max_length=255, db_index=True)
    request_hash = models.CharField(max_length=64, db_index=True, help_text='SHA-256 of HTTP method + path + request payload')
    response_code = models.IntegerField(null=True, blank=True)
    response_body = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='in_progress', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'idempotency_key'], name='unique_tenant_idempotency_key')
        ]
        indexes = [
            models.Index(fields=['tenant', 'expires_at']),
        ]

    def __str__(self):
        return f'{self.tenant.name}:{self.idempotency_key} ({self.status})'


class OutboxEvent(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='outbox_events')
    event_type = models.CharField(max_length=100, db_index=True)
    payload = models.JSONField(default=dict)
    correlation_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending', db_index=True)
    retry_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['tenant', 'event_type']),
        ]

    def __str__(self):
        return f'{self.event_type} [{self.status}] ({self.tenant.name})'


class WebhookEndpoint(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('disabled', 'Disabled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='webhook_endpoints')
    name = models.CharField(max_length=150)
    url = models.URLField(max_length=500)
    encrypted_signing_secret = models.TextField(help_text='AES-256-GCM envelope encrypted signing secret')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='active', db_index=True)
    event_filters = models.JSONField(default=list, blank=True, help_text='Subscribed event patterns, e.g. ["lead.*", "message.sent"] or ["*"]')
    api_version = models.CharField(max_length=20, default='v1')
    consecutive_failures = models.PositiveIntegerField(default=0)
    disabled_reason = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_webhook_endpoints')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
        ]

    def __str__(self):
        return f'{self.name} -> {self.url} ({self.status})'

    def get_signing_secret(self):
        if not self.encrypted_signing_secret:
            return ''
        from organization.services.crypto_service import decrypt_tenant_data
        try:
            return decrypt_tenant_data(self.tenant, self.encrypted_signing_secret)
        except Exception:
            return self.encrypted_signing_secret

    def set_signing_secret(self, secret: str):
        from organization.services.crypto_service import encrypt_tenant_data
        self.encrypted_signing_secret = encrypt_tenant_data(self.tenant, secret)


class WebhookDelivery(models.Model):
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('retrying', 'Retrying'),
        ('failed', 'Failed'),
        ('dlq', 'Dead Letter Queue'),
    ]
    ERROR_CHOICES = [
        ('', 'None'),
        ('network', 'Network Failure'),
        ('timeout', 'Timeout'),
        ('client_error', 'Client Error (4xx)'),
        ('server_error', 'Server Error (5xx)'),
        ('ssrf_blocked', 'SSRF Blocked'),
        ('dns_error', 'DNS Resolution Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='webhook_deliveries')
    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='deliveries')
    event_id = models.CharField(max_length=64, db_index=True)
    event_type = models.CharField(max_length=100, db_index=True)
    payload = models.JSONField(default=dict)
    attempt_number = models.PositiveIntegerField(default=1)
    http_status = models.IntegerField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    error_category = models.CharField(max_length=50, blank=True, default='', choices=ERROR_CHOICES)
    error_message = models.TextField(blank=True, default='')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='retrying', db_index=True)
    next_retry_at = models.DateTimeField(null=True, blank=True, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['endpoint', 'created_at']),
            models.Index(fields=['status', 'next_retry_at']),
        ]

    def __str__(self):
        return f'Delivery {self.id}: {self.event_type} to {self.endpoint.name} [{self.status}]'


class OAuthState(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='oauth_states')
    connector_key = models.CharField(max_length=50, db_index=True)
    state_token = models.CharField(max_length=128, unique=True, db_index=True)
    code_verifier = models.CharField(max_length=128, blank=True, default='')
    redirect_uri = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.connector_key} OAuthState for {self.tenant.name}'

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at


class OAuthConnection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='oauth_connections')
    connector_key = models.CharField(max_length=50, db_index=True)
    provider_account_id = models.CharField(max_length=150, blank=True, default='')
    provider_account_name = models.CharField(max_length=150, blank=True, default='')
    encrypted_access_token = models.TextField(help_text='AES-256-GCM encrypted access token')
    encrypted_refresh_token = models.TextField(blank=True, default='', help_text='AES-256-GCM encrypted refresh token')
    scopes = models.JSONField(default=list, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'connector_key']),
        ]

    def __str__(self):
        return f'{self.connector_key} Connection: {self.provider_account_name or self.provider_account_id} ({self.tenant.name})'

    def get_access_token(self):
        from organization.services.crypto_service import decrypt_tenant_data
        try:
            return decrypt_tenant_data(self.tenant, self.encrypted_access_token)
        except Exception:
            return self.encrypted_access_token

    def set_access_token(self, token: str):
        from organization.services.crypto_service import encrypt_tenant_data
        self.encrypted_access_token = encrypt_tenant_data(self.tenant, token)

    def get_refresh_token(self):
        if not self.encrypted_refresh_token:
            return ''
        from organization.services.crypto_service import decrypt_tenant_data
        try:
            return decrypt_tenant_data(self.tenant, self.encrypted_refresh_token)
        except Exception:
            return self.encrypted_refresh_token

    def set_refresh_token(self, token: str):
        from organization.services.crypto_service import encrypt_tenant_data
        self.encrypted_refresh_token = encrypt_tenant_data(self.tenant, token)


class ConnectorInstance(models.Model):
    AUTH_TYPE_CHOICES = [
        ('oauth2', 'OAuth 2.0'),
        ('api_key', 'API Key / Secret Token'),
        ('basic', 'Basic Authentication'),
        ('webhook', 'Custom Webhook'),
        ('custom', 'Custom Enterprise Configuration'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('error', 'Error'),
        ('disconnected', 'Disconnected'),
    ]
    SYNC_DIRECTION_CHOICES = [
        ('convernix_to_external', 'Convernix to External (Push)'),
        ('external_to_convernix', 'External to Convernix (Pull)'),
        ('bidirectional', 'Bi-directional Synchronous'),
    ]
    CONFLICT_STRATEGY_CHOICES = [
        ('convernix_authoritative', 'Convernix Authoritative'),
        ('external_authoritative', 'External System Authoritative'),
        ('latest_update', 'Latest Timestamp Wins'),
        ('manual', 'Manual Resolution Required'),
    ]
    HEALTH_CHOICES = [
        ('healthy', 'Healthy'),
        ('degraded', 'Degraded'),
        ('failing', 'Failing'),
        ('unknown', 'Unknown'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='connector_instances')
    connector_key = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=120)
    auth_type = models.CharField(max_length=30, choices=AUTH_TYPE_CHOICES, default='api_key')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='inactive', db_index=True)
    config = models.JSONField(default=dict, blank=True, help_text='Safe non-secret configuration')
    encrypted_credentials = models.TextField(blank=True, default='', help_text='AES-256-GCM encrypted tokens/passwords')
    oauth_connection = models.ForeignKey(OAuthConnection, on_delete=models.SET_NULL, null=True, blank=True, related_name='instances')
    sync_direction = models.CharField(max_length=40, choices=SYNC_DIRECTION_CHOICES, default='convernix_to_external')
    conflict_strategy = models.CharField(max_length=40, choices=CONFLICT_STRATEGY_CHOICES, default='convernix_authoritative')
    last_health_check_at = models.DateTimeField(null=True, blank=True)
    health_status = models.CharField(max_length=30, choices=HEALTH_CHOICES, default='unknown')
    health_message = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_connectors')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'connector_key', 'name'], name='unique_tenant_connector_instance_name')
        ]
        indexes = [
            models.Index(fields=['tenant', 'connector_key']),
            models.Index(fields=['tenant', 'status']),
        ]

    def __str__(self):
        return f'{self.name} [{self.connector_key}] ({self.tenant.name})'

    def get_credentials(self):
        if not self.encrypted_credentials:
            return {}
        import json
        from organization.services.crypto_service import decrypt_tenant_data
        try:
            decrypted = decrypt_tenant_data(self.tenant, self.encrypted_credentials)
            return json.loads(decrypted)
        except Exception:
            return {}

    def set_credentials(self, creds_dict: dict):
        import json
        from organization.services.crypto_service import encrypt_tenant_data
        serialized = json.dumps(creds_dict or {})
        self.encrypted_credentials = encrypt_tenant_data(self.tenant, serialized)


class ConnectorFieldMapping(models.Model):
    OBJECT_TYPES = [
        ('lead', 'Lead'),
        ('contact', 'Contact'),
        ('conversation', 'Conversation'),
        ('ticket', 'Ticket'),
    ]
    TRANSFORMATION_CHOICES = [
        ('direct', 'Direct Field Mapping'),
        ('enum_map', 'Enum / Category Value Map'),
        ('default_value', 'Default Value Fallback'),
        ('date_format', 'Date/Time String Format'),
        ('number_cast', 'Numeric Value Cast'),
        ('boolean_cast', 'Boolean Flag Cast'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='connector_mappings')
    connector_instance = models.ForeignKey(ConnectorInstance, on_delete=models.CASCADE, related_name='field_mappings')
    object_type = models.CharField(max_length=50, choices=OBJECT_TYPES, db_index=True)
    convernix_field = models.CharField(max_length=100)
    external_field = models.CharField(max_length=100)
    transformation_type = models.CharField(max_length=40, choices=TRANSFORMATION_CHOICES, default='direct')
    transformation_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['object_type', 'convernix_field']
        constraints = [
            models.UniqueConstraint(fields=['connector_instance', 'object_type', 'convernix_field'], name='unique_instance_object_convernix_field')
        ]

    def __str__(self):
        return f'{self.connector_instance.name}: {self.object_type}.{self.convernix_field} -> {self.external_field}'


class ConnectorObjectMapping(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='connector_object_mappings')
    connector_instance = models.ForeignKey(ConnectorInstance, on_delete=models.CASCADE, related_name='object_mappings')
    object_type = models.CharField(max_length=50, db_index=True)
    convernix_object_id = models.CharField(max_length=100, db_index=True)
    external_object_id = models.CharField(max_length=150, db_index=True)
    external_version = models.CharField(max_length=100, blank=True, default='')
    last_synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'connector_instance', 'object_type', 'convernix_object_id'], name='unique_tenant_instance_obj_cvx_id'),
            models.UniqueConstraint(fields=['tenant', 'connector_instance', 'object_type', 'external_object_id'], name='unique_tenant_instance_obj_ext_id'),
        ]
        indexes = [
            models.Index(fields=['tenant', 'object_type', 'convernix_object_id']),
            models.Index(fields=['tenant', 'object_type', 'external_object_id']),
        ]

    def __str__(self):
        return f'{self.object_type}: {self.convernix_object_id} <=> {self.external_object_id}'


class ConnectorSyncJob(models.Model):
    JOB_TYPE_CHOICES = [
        ('push', 'Push to External'),
        ('pull', 'Pull from External'),
        ('bidirectional', 'Bi-directional Synchronization'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='connector_sync_jobs')
    connector_instance = models.ForeignKey(ConnectorInstance, on_delete=models.CASCADE, related_name='sync_jobs')
    job_type = models.CharField(max_length=30, choices=JOB_TYPE_CHOICES)
    object_type = models.CharField(max_length=50)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending', db_index=True)
    records_processed = models.PositiveIntegerField(default=0)
    records_succeeded = models.PositiveIntegerField(default=0)
    records_failed = models.PositiveIntegerField(default=0)
    error_summary = models.TextField(blank=True, default='')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['connector_instance', 'created_at']),
        ]

    def __str__(self):
        return f'SyncJob {self.id}: {self.connector_instance.name} [{self.job_type}] - {self.status}'


class ConnectorSyncRecord(models.Model):
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('skipped', 'Skipped'),
        ('conflict', 'Conflict Handled'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sync_job = models.ForeignKey(ConnectorSyncJob, on_delete=models.CASCADE, related_name='records')
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='connector_sync_records')
    object_type = models.CharField(max_length=50)
    convernix_object_id = models.CharField(max_length=100, blank=True, default='')
    external_object_id = models.CharField(max_length=150, blank=True, default='')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    conflict_strategy = models.CharField(max_length=40, blank=True, default='')
    error_message = models.TextField(blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['sync_job', 'action']),
        ]

    def __str__(self):
        return f'{self.object_type} {self.action}: cvx={self.convernix_object_id} ext={self.external_object_id}'


class IntegrationApiLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_id = models.CharField(max_length=64, db_index=True)
    tenant = models.ForeignKey('users.Tenant', on_delete=models.CASCADE, related_name='integration_api_logs', null=True, blank=True)
    service_account_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    api_key_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    endpoint = models.CharField(max_length=255, db_index=True)
    http_method = models.CharField(max_length=10)
    status_code = models.IntegerField(db_index=True)
    duration_ms = models.PositiveIntegerField(default=0)
    source_ip = models.CharField(max_length=45, default='127.0.0.1')
    user_agent = models.TextField(blank=True, default='')
    api_version = models.CharField(max_length=20, default='v1')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'created_at']),
            models.Index(fields=['tenant', 'endpoint']),
        ]

    def __str__(self):
        return f'[{self.http_method}] {self.endpoint} ({self.status_code}) - {self.request_id}'

