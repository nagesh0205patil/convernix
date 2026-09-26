import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class ConversationStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    PENDING = 'PENDING', 'Pending'
    RESOLVED = 'RESOLVED', 'Resolved'
    CLOSED = 'CLOSED', 'Closed'


class ConversationPriority(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    URGENT = 'URGENT', 'Urgent'


class MessageDirection(models.TextChoices):
    INBOUND = 'INBOUND', 'Inbound'
    OUTBOUND = 'OUTBOUND', 'Outbound'
    INTERNAL = 'INTERNAL', 'Internal'


class MessageType(models.TextChoices):
    TEXT = 'TEXT', 'Text'
    IMAGE = 'IMAGE', 'Image'
    VIDEO = 'VIDEO', 'Video'
    AUDIO = 'AUDIO', 'Audio'
    DOCUMENT = 'DOCUMENT', 'Document'
    LOCATION = 'LOCATION', 'Location'
    CONTACT = 'CONTACT', 'Contact'
    INTERACTIVE = 'INTERACTIVE', 'Interactive'
    TEMPLATE = 'TEMPLATE', 'Template'
    SYSTEM = 'SYSTEM', 'System'
    INTERNAL_NOTE = 'INTERNAL_NOTE', 'Internal Note'


class MessageStatus(models.TextChoices):
    QUEUED = 'QUEUED', 'Queued'
    SENDING = 'SENDING', 'Sending'
    SENT = 'SENT', 'Sent'
    DELIVERED = 'DELIVERED', 'Delivered'
    READ = 'READ', 'Read'
    FAILED = 'FAILED', 'Failed'
    RECEIVED = 'RECEIVED', 'Received'


class AssignmentAction(models.TextChoices):
    CLAIM = 'CLAIM', 'Claim'
    ASSIGN = 'ASSIGN', 'Assign'
    REASSIGN = 'REASSIGN', 'Reassign'
    UNASSIGN = 'UNASSIGN', 'Unassign'
    TRANSFER = 'TRANSFER', 'Transfer'


class Conversation(models.Model):
    """
    Core Conversation entity for Convernix Inbox.
    Represents an ongoing interaction thread with a customer contact.
    """
    tenant = models.ForeignKey(
        'users.Tenant',
        on_delete=models.CASCADE,
        related_name='inbox_conversations',
        db_index=True,
    )
    contact = models.ForeignKey(
        'whatsapp.Customer',
        on_delete=models.CASCADE,
        related_name='inbox_conversations',
        db_index=True,
    )
    whatsapp_account = models.ForeignKey(
        'whatsapp.WhatsAppConfiguration',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inbox_conversations',
    )
    business_number = models.ForeignKey(
        'whatsapp.BusinessNumber',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inbox_conversations',
        db_index=True,
    )
    department = models.ForeignKey(
        'whatsapp.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inbox_conversations',
        db_index=True,
    )
    assigned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_inbox_conversations',
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=ConversationStatus.choices,
        default=ConversationStatus.OPEN,
        db_index=True,
    )
    priority = models.CharField(
        max_length=20,
        choices=ConversationPriority.choices,
        default=ConversationPriority.MEDIUM,
        db_index=True,
    )
    last_message_id = models.CharField(max_length=255, blank=True, default='')
    last_message_preview = models.TextField(blank=True, default='')
    last_message_at = models.DateTimeField(default=timezone.now, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1, help_text='Optimistic locking version')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    legacy_enquiry = models.OneToOneField(
        'whatsapp.Enquiry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inbox_conversation',
    )

    class Meta:
        ordering = ['-last_message_at']
        indexes = [
            models.Index(fields=['tenant', 'status', 'last_message_at']),
            models.Index(fields=['tenant', 'department', 'status']),
            models.Index(fields=['tenant', 'assigned_user', 'status']),
        ]

    def __str__(self):
        return f'Conversation #{self.id} [{self.status}] (Tenant: {self.tenant_id})'

    @property
    def plain_last_message_preview(self):
        if self.last_message_preview and str(self.last_message_preview).startswith('cvx:v') and self.tenant:
            from organization.services.crypto_service import decrypt_tenant_data
            try:
                return decrypt_tenant_data(self.tenant, self.last_message_preview)
            except Exception:
                return self.last_message_preview
        return self.last_message_preview

    def save(self, *args, **kwargs):
        if self.tenant and self.last_message_preview and not str(self.last_message_preview).startswith('cvx:v'):
            from organization.services.crypto_service import encrypt_tenant_data
            self.last_message_preview = encrypt_tenant_data(self.tenant, self.last_message_preview)
        super().save(*args, **kwargs)

    def can_transition_to(self, new_status: str) -> bool:
        """Enforces explicit state machine transitions."""
        valid_transitions = {
            ConversationStatus.OPEN: {ConversationStatus.PENDING, ConversationStatus.RESOLVED, ConversationStatus.CLOSED},
            ConversationStatus.PENDING: {ConversationStatus.OPEN, ConversationStatus.RESOLVED, ConversationStatus.CLOSED},
            ConversationStatus.RESOLVED: {ConversationStatus.OPEN, ConversationStatus.CLOSED},
            ConversationStatus.CLOSED: {ConversationStatus.OPEN},
        }
        return new_status in valid_transitions.get(self.status, set())


class Message(models.Model):
    """
    Message model supporting WhatsApp inbound/outbound and internal team notes.
    """
    tenant = models.ForeignKey(
        'users.Tenant',
        on_delete=models.CASCADE,
        related_name='inbox_messages',
        db_index=True,
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        db_index=True,
    )
    sender_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_inbox_messages',
    )
    meta_message_id = models.CharField(max_length=255, blank=True, default='', db_index=True)
    direction = models.CharField(
        max_length=20,
        choices=MessageDirection.choices,
        db_index=True,
    )
    message_type = models.CharField(
        max_length=30,
        choices=MessageType.choices,
        default=MessageType.TEXT,
    )
    content = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=MessageStatus.choices,
        default=MessageStatus.RECEIVED,
        db_index=True,
    )
    error_message = models.TextField(blank=True, default='')
    raw_payload = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    legacy_whatsapp_message = models.OneToOneField(
        'whatsapp.WhatsAppMessage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inbox_message',
    )

    class Meta:
        ordering = ['timestamp', 'id']
        indexes = [
            models.Index(fields=['conversation', 'timestamp']),
            models.Index(fields=['tenant', 'meta_message_id']),
        ]

    def __str__(self):
        return f'Message #{self.id} [{self.direction} - {self.message_type}] (Conv: {self.conversation_id})'

    @property
    def plain_content(self):
        if self.content and str(self.content).startswith('cvx:v') and self.tenant:
            from organization.services.crypto_service import decrypt_tenant_data
            try:
                return decrypt_tenant_data(self.tenant, self.content)
            except Exception:
                return self.content
        return self.content

    def save(self, *args, **kwargs):
        if self.tenant and self.content and not str(self.content).startswith('cvx:v'):
            from organization.services.crypto_service import encrypt_tenant_data
            self.content = encrypt_tenant_data(self.tenant, self.content)
        super().save(*args, **kwargs)


class MessageAttachment(models.Model):
    """
    Secure attachment associated with an inbox message.
    """
    tenant = models.ForeignKey(
        'users.Tenant',
        on_delete=models.CASCADE,
        related_name='inbox_attachments',
        db_index=True,
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='attachments',
        db_index=True,
    )
    file = models.FileField(upload_to='inbox_attachments/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField(default=0)
    sha256_hash = models.CharField(max_length=64, blank=True, default='')
    meta_media_id = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.filename} ({self.content_type}, {self.file_size} bytes)'


class MessageMention(models.Model):
    """
    @mention in internal notes.
    """
    tenant = models.ForeignKey(
        'users.Tenant',
        on_delete=models.CASCADE,
        related_name='inbox_mentions',
        db_index=True,
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='mentions',
        db_index=True,
    )
    mentioned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inbox_mentions',
        db_index=True,
    )
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Mention: {self.mentioned_user_id} on message #{self.message_id}'


class ConversationRead(models.Model):
    """
    Per-user read tracking for conversations.
    Enforces that unread state is personal to each user rather than a single global boolean.
    """
    tenant = models.ForeignKey(
        'users.Tenant',
        on_delete=models.CASCADE,
        related_name='inbox_reads',
        db_index=True,
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='reads',
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inbox_reads',
        db_index=True,
    )
    last_read_message_id = models.CharField(max_length=255, blank=True, default='')
    last_read_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['conversation', 'user'], name='unique_conversation_user_read'),
        ]

    def __str__(self):
        return f'ReadState: user={self.user_id} conv={self.conversation_id} at {self.last_read_at}'


class ConversationAssignment(models.Model):
    """
    Immutable audit history of conversation claims, assignments, reassignments, and transfers.
    """
    tenant = models.ForeignKey(
        'users.Tenant',
        on_delete=models.CASCADE,
        related_name='inbox_assignments',
        db_index=True,
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='assignments',
        db_index=True,
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assignments_made',
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assignments_from',
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assignments_to',
    )
    action_type = models.CharField(
        max_length=30,
        choices=AssignmentAction.choices,
    )
    from_department = models.ForeignKey(
        'whatsapp.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    to_department = models.ForeignKey(
        'whatsapp.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Assignment #{self.id} [{self.action_type}] on conv #{self.conversation_id}'


class Tag(models.Model):
    """
    Tenant-specific conversation tags.
    """
    tenant = models.ForeignKey(
        'users.Tenant',
        on_delete=models.CASCADE,
        related_name='inbox_tags',
        db_index=True,
    )
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=20, default='#6366f1')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'name'], name='unique_tenant_tag_name'),
        ]
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.tenant_id})'


class ConversationTag(models.Model):
    """
    Association between Conversation and Tag.
    """
    tenant = models.ForeignKey(
        'users.Tenant',
        on_delete=models.CASCADE,
        related_name='inbox_conversation_tags',
        db_index=True,
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='tags',
        db_index=True,
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name='tagged_conversations',
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['conversation', 'tag'], name='unique_conversation_tag'),
        ]

    def __str__(self):
        return f'Conv #{self.conversation_id} tag: {self.tag.name}'


class WebhookEvent(models.Model):
    """
    Persisted Meta webhook events for deduplication and idempotency.
    """
    tenant = models.ForeignKey(
        'users.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='webhook_events',
        db_index=True,
    )
    event_id = models.CharField(max_length=255, unique=True, db_index=True)
    event_type = models.CharField(max_length=100, default='whatsapp_message')
    status = models.CharField(
        max_length=30,
        choices=[('PROCESSED', 'Processed'), ('IGNORED', 'Ignored'), ('FAILED', 'Failed')],
        default='PROCESSED',
    )
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'WebhookEvent {self.event_id} ({self.status})'

