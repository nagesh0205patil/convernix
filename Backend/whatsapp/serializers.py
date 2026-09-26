from rest_framework import serializers

from .models import AutomationRule, BusinessNumber, Enquiry, Notification, WhatsAppMessage


class NotificationSerializer(serializers.ModelSerializer):
    recipient_name = serializers.CharField(source='recipient.name', read_only=True)

    class Meta:
        model = Notification
        fields = ('recipient_name', 'status', 'error_message')


class EnquirySerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()
    team_name = serializers.CharField(source='department.name', read_only=True)
    notifications = NotificationSerializer(many=True, read_only=True)
    customer_id = serializers.IntegerField(read_only=True)
    message = serializers.SerializerMethodField()

    class Meta:
        model = Enquiry
        fields = ('id', 'reference', 'customer_id', 'customer_name', 'phone_number', 'customer_email',
                  'organization_name', 'team_name', 'message', 'status', 'created_at', 'notifications')

    def get_customer_name(self, instance):
        customer = getattr(instance, 'customer', None)
        if not customer:
            return ''
        return getattr(customer, 'plain_name', None) or customer.full_name or ''

    def get_organization_name(self, instance):
        customer = getattr(instance, 'customer', None)
        if not customer:
            return ''
        return getattr(customer, 'plain_organization', None) or customer.organization_name or ''

    def get_phone_number(self, instance):
        customer = getattr(instance, 'customer', None)
        if not customer:
            return ''
        raw_phone = getattr(customer, 'plain_phone', None) or customer.whatsapp_number or ''
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            from organization.services.masking_service import MaskingService
            tenant = customer.tenant or getattr(instance, 'tenant', None)
            if MaskingService.can_view_unmasked_phone(request.user, tenant):
                return raw_phone
            return MaskingService.mask_phone(raw_phone)
        return raw_phone

    def get_customer_email(self, instance):
        customer = getattr(instance, 'customer', None)
        if not customer:
            return ''
        raw_email = getattr(customer, 'plain_email', None) or customer.email or ''
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            from organization.services.masking_service import MaskingService
            tenant = customer.tenant or getattr(instance, 'tenant', None)
            if MaskingService.can_view_unmasked_email(request.user, tenant):
                return raw_email
            return MaskingService.mask_email(raw_email)
        return raw_email

    def get_message(self, instance):
        return getattr(instance, 'plain_message', None) or instance.message or ''


class WhatsAppMessageSerializer(serializers.ModelSerializer):
    attachment_url = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()

    class Meta:
        model = WhatsAppMessage
        fields = ('id', 'whatsapp_message_id', 'direction', 'message_type', 'content', 'status', 'timestamp',
                  'seen_at', 'attachment_name', 'attachment_content_type', 'attachment_url')

    def get_content(self, instance):
        return getattr(instance, 'plain_content', None) or instance.content or ''

    def get_attachment_url(self, instance):
        if not instance.attachment:
            return None
        return f'/whatsapp/conversations/{instance.enquiry_id}/messages/{instance.id}/attachment/'


class ConversationSerializer(EnquirySerializer):
    messages = WhatsAppMessageSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    last_message_at = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta(EnquirySerializer.Meta):
        fields = EnquirySerializer.Meta.fields + ('last_message', 'last_message_at', 'unread_count', 'messages')

    def _last(self, instance):
        cached = getattr(instance, '_prefetched_objects_cache', {}).get('messages')
        if cached is not None:
            items = list(cached)
            return items[-1] if items else None
        return instance.messages.order_by('-timestamp').first()

    def get_last_message(self, instance):
        message = self._last(instance)
        if message:
            return getattr(message, 'plain_content', None) or message.content or ''
        return getattr(instance, 'plain_message', None) or instance.message or ''

    def get_last_message_at(self, instance):
        message = self._last(instance)
        return message.timestamp if message else instance.created_at

    def get_unread_count(self, instance):
        cached = getattr(instance, '_prefetched_objects_cache', {}).get('messages')
        if cached is not None:
            return sum(1 for message in cached if message.direction == 'incoming' and message.seen_at is None)
        return instance.messages.filter(direction='incoming', seen_at__isnull=True).count()


class ConversationReadSerializer(serializers.Serializer):
    is_read = serializers.BooleanField()


class ConversationListSerializer(ConversationSerializer):
    """Compact inbox representation; history is loaded only when a thread is opened."""

    class Meta(ConversationSerializer.Meta):
        fields = tuple(field for field in ConversationSerializer.Meta.fields if field != 'messages')


class SendMessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=4096, trim_whitespace=True, required=False, allow_blank=True)
    file = serializers.FileField(required=False)
    files = serializers.ListField(child=serializers.FileField(), required=False, allow_empty=False, max_length=10)

    def _validate_attachment(self, value):
        if value.size > 16 * 1024 * 1024:
            raise serializers.ValidationError('The attachment cannot exceed 16 MB.')
        allowed = {
            'image/jpeg', 'image/png', 'application/pdf', 'text/plain',
            'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'audio/aac', 'audio/mpeg', 'audio/mp4', 'audio/ogg', 'video/mp4', 'video/3gpp',
        }
        if value.content_type not in allowed:
            raise serializers.ValidationError('This file type is not supported for WhatsApp attachments.')
        return value

    def validate_file(self, value):
        return self._validate_attachment(value)

    def validate_files(self, values):
        return [self._validate_attachment(value) for value in values]

    def validate(self, attrs):
        if attrs.get('file') and attrs.get('files'):
            raise serializers.ValidationError('Use either file or files, not both.')
        if attrs.get('file'):
            attrs['files'] = [attrs.pop('file')]
        if not attrs.get('message', '').strip() and not attrs.get('files'):
            raise serializers.ValidationError('Enter a message or select a file.')
        return attrs


class BusinessNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessNumber
        fields = ('id', 'number', 'phone_number_id', 'forwarding_number', 'label', 'default_team', 'is_active')
        read_only_fields = ('id',)


class AutomationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationRule
        fields = (
            'id', 'rule_type', 'name', 'is_active', 'trigger_desc',
            'action_desc', 'config', 'last_triggered_at', 'updated_at',
        )
        read_only_fields = ('id', 'rule_type', 'name', 'trigger_desc', 'action_desc', 'last_triggered_at', 'updated_at')

