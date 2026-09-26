from rest_framework import serializers
from django.contrib.auth import get_user_model
from whatsapp.models import Department, Customer, BusinessNumber
from organization.services.masking_service import MaskingService
from .models import (
    Conversation, ConversationStatus, ConversationPriority,
    Message, MessageDirection, MessageType, MessageStatus,
    MessageAttachment, MessageMention, Tag, ConversationTag
)

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'created_at']


class ContactSummarySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    organization = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ['id', 'name', 'phone', 'email', 'organization', 'consent_status', 'created_at']

    def get_name(self, obj):
        return obj.plain_name or 'Customer'

    def get_phone(self, obj):
        raw = obj.plain_phone or obj.whatsapp_number
        request = self.context.get('request')
        if request and request.user:
            tenant = getattr(request.user, 'tenant', None)
            if tenant and MaskingService.can_view_unmasked_phone(request.user, tenant):
                return raw
            if request.user.is_superuser:
                return raw
        return MaskingService.mask_phone(raw)

    def get_email(self, obj):
        raw = obj.plain_email or obj.email
        if not raw:
            return ''
        request = self.context.get('request')
        if request and request.user:
            tenant = getattr(request.user, 'tenant', None)
            if tenant and MaskingService.can_view_unmasked_email(request.user, tenant):
                return raw
            if request.user.is_superuser:
                return raw
        return MaskingService.mask_email(raw)

    def get_organization(self, obj):
        return obj.plain_organization or obj.organization_name


class UserSummarySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'team_name']

    def get_name(self, obj):
        return obj.get_full_name() or obj.username or obj.email


class DepartmentSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'slug', 'description', 'is_active']


class MessageAttachmentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = MessageAttachment
        fields = ['id', 'filename', 'content_type', 'file_size', 'download_url', 'created_at']

    def get_download_url(self, obj):
        return f'/api/inbox/attachments/{obj.id}/download/'


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSummarySerializer(source='sender_user', read_only=True)
    content = serializers.SerializerMethodField()
    attachments = MessageAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'conversation_id', 'sender', 'meta_message_id',
            'direction', 'message_type', 'content', 'status',
            'error_message', 'attachments', 'timestamp', 'created_at'
        ]

    def get_content(self, obj):
        return obj.plain_content


class ConversationListSerializer(serializers.ModelSerializer):
    contact = ContactSummarySerializer(read_only=True)
    department = DepartmentSummarySerializer(read_only=True)
    assigned_user = UserSummarySerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'tenant_id', 'contact', 'department', 'assigned_user',
            'status', 'priority', 'last_message', 'last_message_at',
            'unread_count', 'tags', 'version', 'created_at', 'updated_at'
        ]

    def get_last_message(self, obj):
        return obj.plain_last_message_preview

    def get_tags(self, obj):
        return [
            {'id': ct.tag.id, 'name': ct.tag.name, 'color': ct.tag.color}
            for ct in obj.tags.select_related('tag').all()
        ]

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return 0
        from .models import ConversationRead
        read_state = ConversationRead.objects.filter(conversation=obj, user=request.user).first()
        if not read_state:
            # All incoming messages are unread
            return obj.messages.filter(direction=MessageDirection.INBOUND).count()
        return obj.messages.filter(
            direction=MessageDirection.INBOUND,
            timestamp__gt=read_state.last_read_at,
        ).count()


class ConversationDetailSerializer(serializers.ModelSerializer):
    contact = ContactSummarySerializer(read_only=True)
    department = DepartmentSummarySerializer(read_only=True)
    assigned_user = UserSummarySerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'tenant_id', 'contact', 'department', 'assigned_user',
            'status', 'priority', 'last_message', 'last_message_at',
            'unread_count', 'is_read', 'tags', 'version', 'created_at', 'updated_at', 'resolved_at'
        ]

    def get_last_message(self, obj):
        return obj.plain_last_message_preview

    def get_tags(self, obj):
        return [
            {'id': ct.tag.id, 'name': ct.tag.name, 'color': ct.tag.color}
            for ct in obj.tags.select_related('tag').all()
        ]

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return 0
        from .models import ConversationRead
        read_state = ConversationRead.objects.filter(conversation=obj, user=request.user).first()
        if not read_state:
            return obj.messages.filter(direction=MessageDirection.INBOUND).count()
        return obj.messages.filter(
            direction=MessageDirection.INBOUND,
            timestamp__gt=read_state.last_read_at,
        ).count()

    def get_is_read(self, obj):
        return self.get_unread_count(obj) == 0


class SendMessageInputSerializer(serializers.Serializer):
    message = serializers.CharField(required=False, allow_blank=True, default='')
    files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        default=list,
    )

    def validate(self, data):
        if not data.get('message', '').strip() and not data.get('files'):
            raise serializers.ValidationError('Either a message or file attachment must be provided.')
        return data


class CreateNoteInputSerializer(serializers.Serializer):
    content = serializers.CharField(required=True, min_length=1, max_length=10000)


class AssignInputSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)


class TransferInputSerializer(serializers.Serializer):
    department_id = serializers.IntegerField(required=True)
    reason = serializers.CharField(required=False, allow_blank=True, default='')
    user_id = serializers.IntegerField(required=False, allow_null=True)


class ReadStateInputSerializer(serializers.Serializer):
    is_read = serializers.BooleanField(required=False, default=True)
    last_read_message_id = serializers.CharField(required=False, allow_blank=True, default='')


class MentionSerializer(serializers.ModelSerializer):
    message_content = serializers.SerializerMethodField()
    conversation_id = serializers.IntegerField(source='message.conversation_id')
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = MessageMention
        fields = ['id', 'conversation_id', 'message_id', 'message_content', 'sender_name', 'is_read', 'read_at', 'created_at']

    def get_message_content(self, obj):
        return obj.message.plain_content

    def get_sender_name(self, obj):
        if obj.message.sender_user:
            return obj.message.sender_user.get_full_name() or obj.message.sender_user.username
        return 'Team Member'

