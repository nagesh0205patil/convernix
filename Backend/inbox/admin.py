from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Conversation, ConversationStatus,
    Message, MessageAttachment, MessageMention,
    ConversationRead, ConversationAssignment,
    Tag, ConversationTag, WebhookEvent,
)


# ---------------------------------------------------------------------------
# Inline admins
# ---------------------------------------------------------------------------

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ('direction', 'message_type', 'status', 'meta_message_id', 'timestamp')
    readonly_fields = ('direction', 'message_type', 'status', 'meta_message_id', 'timestamp')
    ordering = ('-timestamp',)
    max_num = 20
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ConversationTagInline(admin.TabularInline):
    model = ConversationTag
    extra = 0
    raw_id_fields = ('tag',)
    readonly_fields = ('created_at',)

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser


class MessageAttachmentInline(admin.TabularInline):
    model = MessageAttachment
    extra = 0
    readonly_fields = ('filename', 'content_type', 'file_size', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# Conversation admin
# ---------------------------------------------------------------------------

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'tenant', 'contact', 'department',
        'status_badge', 'priority', 'assigned_user',
        'last_message_at', 'version', 'created_at',
    )
    list_filter = ('tenant', 'status', 'priority', 'department')
    search_fields = (
        'id', 'contact__whatsapp_number',
        'assigned_user__email', 'assigned_user__username',
    )
    ordering = ('-last_message_at', '-created_at')
    date_hierarchy = 'created_at'
    raw_id_fields = ('tenant', 'contact', 'department', 'assigned_user', 'business_number')
    readonly_fields = (
        'id', 'version', 'created_at', 'updated_at',
        'resolved_at', 'last_message_at', 'last_message_preview_display',
    )
    fieldsets = (
        ('Identification', {
            'fields': ('id', 'tenant', 'business_number', 'contact'),
        }),
        ('Routing', {
            'fields': ('department', 'assigned_user', 'priority'),
        }),
        ('State', {
            'fields': ('status', 'version', 'resolved_at'),
        }),
        ('Last Message', {
            'fields': ('last_message_at', 'last_message_preview_display'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    inlines = [ConversationTagInline, MessageInline]

    def status_badge(self, obj):
        colors = {
            ConversationStatus.OPEN: 'green',
            ConversationStatus.PENDING: 'orange',
            ConversationStatus.RESOLVED: 'blue',
            ConversationStatus.CLOSED: 'grey',
        }
        color = colors.get(obj.status, 'black')
        return format_html('<span style="color:{}">{}</span>', color, obj.get_status_display())

    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def last_message_preview_display(self, obj):
        """Show decrypted preview — only visible to superusers."""
        try:
            return obj.plain_last_message_preview or '—'
        except Exception:
            return '[decryption error]'

    last_message_preview_display.short_description = 'Last Message Preview'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            if hasattr(request.user, 'tenant') and request.user.tenant:
                qs = qs.filter(tenant=request.user.tenant)
        return qs

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# ---------------------------------------------------------------------------
# Message admin
# ---------------------------------------------------------------------------

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'conversation', 'direction', 'message_type',
        'status', 'meta_message_id', 'created_at',
    )
    list_filter = ('tenant', 'direction', 'message_type', 'status')
    search_fields = ('id', 'meta_message_id', 'conversation__id')
    ordering = ('-timestamp',)
    raw_id_fields = ('tenant', 'conversation', 'sender_user')
    readonly_fields = (
        'id', 'meta_message_id', 'direction', 'message_type',
        'status', 'timestamp', 'created_at',
        'content_display',
    )
    fieldsets = (
        ('Identification', {'fields': ('id', 'tenant', 'conversation')}),
        ('Message', {
            'fields': ('direction', 'message_type', 'meta_message_id', 'sender_user'),
        }),
        ('Content', {
            'fields': ('content_display',),
            'classes': ('collapse',),
            'description': 'Content is decrypted for display here only. Not logged.',
        }),
        ('Status', {'fields': ('status', 'error_message')}),
        ('Timestamps', {
            'fields': ('timestamp', 'created_at'),
            'classes': ('collapse',),
        }),
    )
    inlines = [MessageAttachmentInline]

    def content_display(self, obj):
        try:
            text = obj.plain_content or '—'
            # Truncate long content in admin
            if len(text) > 500:
                text = text[:500] + '…'
            return text
        except Exception:
            return '[decryption error]'

    content_display.short_description = 'Content (decrypted)'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            if hasattr(request.user, 'tenant') and request.user.tenant:
                qs = qs.filter(tenant=request.user.tenant)
        return qs

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# ---------------------------------------------------------------------------
# MessageAttachment admin
# ---------------------------------------------------------------------------

@admin.register(MessageAttachment)
class MessageAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'filename', 'content_type', 'file_size', 'created_at')
    list_filter = ('content_type',)
    search_fields = ('filename', 'message__id')
    readonly_fields = ('id', 'sha256_hash', 'created_at')
    raw_id_fields = ('message',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# ---------------------------------------------------------------------------
# ConversationRead admin
# ---------------------------------------------------------------------------

@admin.register(ConversationRead)
class ConversationReadAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'conversation', 'user', 'last_read_message_id', 'last_read_at')
    list_filter = ('tenant',)
    search_fields = ('user__email', 'conversation__id')
    raw_id_fields = ('tenant', 'conversation', 'user')
    readonly_fields = ('id', 'last_read_at')

    def has_add_permission(self, request):
        return False


# ---------------------------------------------------------------------------
# ConversationAssignment admin
# ---------------------------------------------------------------------------

@admin.register(ConversationAssignment)
class ConversationAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'tenant', 'conversation', 'action_type',
        'to_user', 'assigned_by', 'created_at',
    )
    list_filter = ('tenant', 'action_type')
    search_fields = ('conversation__id', 'to_user__email', 'assigned_by__email')
    ordering = ('-created_at',)
    raw_id_fields = ('tenant', 'conversation', 'to_user', 'from_user', 'assigned_by', 'from_department', 'to_department')
    readonly_fields = ('id', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # Immutable audit history
        return False


# ---------------------------------------------------------------------------
# Tag admin
# ---------------------------------------------------------------------------

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'name', 'color', 'created_at')
    list_filter = ('tenant',)
    search_fields = ('name',)
    raw_id_fields = ('tenant',)


# ---------------------------------------------------------------------------
# WebhookEvent admin
# ---------------------------------------------------------------------------

@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'tenant', 'event_type', 'event_id',
        'status', 'created_at',
    )
    list_filter = ('tenant', 'event_type', 'status')
    search_fields = ('event_id',)
    ordering = ('-created_at',)
    raw_id_fields = ('tenant',)
    readonly_fields = ('id', 'event_id', 'created_at', 'payload_display')
    fieldsets = (
        ('Identification', {
            'fields': ('id', 'tenant', 'event_type', 'event_id'),
        }),
        ('Processing', {
            'fields': ('status',),
        }),
        ('Payload', {
            'fields': ('payload_display',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def payload_display(self, obj):
        import json
        try:
            return json.dumps(obj.payload, indent=2)
        except Exception:
            return str(obj.payload)

    payload_display.short_description = 'Payload (JSON)'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

