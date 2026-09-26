from rest_framework import serializers
from crm.models import (
    Customer, CustomerIdentity, CustomerMergeHistory, Pipeline, PipelineStage,
    Lead, LeadFollower, LeadStageHistory, LeadAssignmentHistory,
    CustomFieldDefinition, CustomFieldValue, Tag, CustomerTag, LeadTag,
    Activity, Note
)
from users.permissions import has_tenant_permission
from organization.services.masking_service import MaskingService


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['tag_id', 'name', 'color', 'description', 'created_at']
        read_only_fields = ['tag_id', 'created_at']


class CustomFieldDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomFieldDefinition
        fields = [
            'field_id', 'entity_type', 'field_name', 'field_label', 'field_type',
            'is_required', 'is_unique', 'is_searchable', 'is_sensitive_pii',
            'is_visible', 'is_editable', 'default_value', 'validation_rules',
            'options', 'display_order', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['field_id', 'created_at', 'updated_at']


class CustomerIdentitySerializer(serializers.ModelSerializer):
    identifier = serializers.SerializerMethodField()

    class Meta:
        model = CustomerIdentity
        fields = ['identity_id', 'provider', 'identifier', 'is_primary', 'verified', 'metadata', 'created_at']

    def get_identifier(self, obj):
        request = self.context.get('request')
        tenant = getattr(obj, 'tenant', None)
        user = getattr(request, 'user', None) if request else None
        can_view_pii = user and (user.is_superuser or has_tenant_permission(user, tenant, 'customer.view_pii'))
        plain = obj.plain_identifier
        if can_view_pii:
            return plain
        if obj.provider in ('WHATSAPP', 'PHONE'):
            return MaskingService.mask_phone(plain)
        elif obj.provider == 'EMAIL':
            return MaskingService.mask_email(plain)
        return '********'


class CustomerSerializer(serializers.ModelSerializer):
    phone = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    is_pii_unmasked = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'customer_id', 'display_name', 'first_name', 'last_name',
            'phone', 'email', 'status', 'source', 'is_pii_unmasked',
            'tags', 'version', 'created_at', 'updated_at'
        ]
        read_only_fields = ['customer_id', 'created_at', 'updated_at', 'version']

    def _can_view_pii(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user or not user.is_authenticated:
            return False
        return user.is_superuser or has_tenant_permission(user, obj.tenant, 'customer.view_pii')

    def get_is_pii_unmasked(self, obj):
        return self._can_view_pii(obj)

    def get_phone(self, obj):
        if self._can_view_pii(obj):
            return obj.plain_phone
        return obj.masked_phone

    def get_email(self, obj):
        if self._can_view_pii(obj):
            return obj.plain_email
        return obj.masked_email

    def get_first_name(self, obj):
        if self._can_view_pii(obj):
            return obj.plain_first_name
        return ''

    def get_last_name(self, obj):
        if self._can_view_pii(obj):
            return obj.plain_last_name
        return ''

    def get_tags(self, obj):
        return [
            {'tag_id': str(ct.tag.tag_id), 'name': ct.tag.name, 'color': ct.tag.color}
            for ct in obj.customer_tags.all()
        ]


class CustomerCreateUpdateSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Customer.STATUS_CHOICES, default='ACTIVE', required=False)
    source = serializers.CharField(max_length=50, default='MANUAL', required=False)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    custom_fields = serializers.DictField(required=False)


class CustomerMergeSerializer(serializers.Serializer):
    primary_customer_id = serializers.UUIDField(required=True)
    secondary_customer_id = serializers.UUIDField(required=True)
    reason = serializers.CharField(required=False, allow_blank=True, default='Duplicate resolution')


class PipelineStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PipelineStage
        fields = [
            'stage_id', 'pipeline_id', 'name', 'description', 'display_order',
            'is_active', 'is_terminal', 'classification', 'color', 'created_at', 'updated_at'
        ]
        read_only_fields = ['stage_id', 'created_at', 'updated_at']


class PipelineSerializer(serializers.ModelSerializer):
    stages = PipelineStageSerializer(many=True, read_only=True)

    class Meta:
        model = Pipeline
        fields = [
            'pipeline_id', 'name', 'description', 'is_default', 'is_active',
            'display_order', 'stages', 'created_at', 'updated_at'
        ]
        read_only_fields = ['pipeline_id', 'created_at', 'updated_at']


class LeadListSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    pipeline_name = serializers.CharField(source='pipeline.name', read_only=True)
    stage_name = serializers.CharField(source='stage.name', read_only=True)
    stage_classification = serializers.CharField(source='stage.classification', read_only=True)
    stage_color = serializers.CharField(source='stage.color', read_only=True)
    department_name = serializers.CharField(source='department.name', default='', read_only=True)
    owner_name = serializers.SerializerMethodField()
    owner_email = serializers.CharField(source='owner_user.email', default='', read_only=True)
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            'lead_id', 'title', 'customer', 'pipeline_id', 'pipeline_name',
            'stage_id', 'stage_name', 'stage_classification', 'stage_color',
            'department_id', 'department_name', 'owner_user_id', 'owner_name', 'owner_email',
            'source', 'priority', 'status', 'estimated_value', 'currency', 'win_probability',
            'last_contacted_at', 'closed_at', 'tags', 'version', 'created_at', 'updated_at'
        ]

    def get_owner_name(self, obj):
        if not obj.owner_user:
            return 'Unassigned'
        return getattr(obj.owner_user, 'get_full_name', lambda: '')() or obj.owner_user.email

    def get_tags(self, obj):
        return [
            {'tag_id': str(lt.tag.tag_id), 'name': lt.tag.name, 'color': lt.tag.color}
            for lt in obj.lead_tags.all()
        ]


class LeadDetailSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    pipeline = PipelineSerializer(read_only=True)
    stage = PipelineStageSerializer(read_only=True)
    department_name = serializers.CharField(source='department.name', default='', read_only=True)
    owner = serializers.SerializerMethodField()
    followers = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    custom_fields = serializers.SerializerMethodField()
    recent_stage_history = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            'lead_id', 'title', 'customer', 'pipeline', 'stage',
            'department_id', 'department_name', 'owner', 'followers',
            'source', 'priority', 'status', 'estimated_value', 'currency', 'win_probability',
            'last_contacted_at', 'closed_at', 'tags', 'custom_fields',
            'recent_stage_history', 'version', 'created_at', 'updated_at'
        ]

    def get_owner(self, obj):
        if not obj.owner_user:
            return None
        return {
            'id': obj.owner_user.id,
            'name': getattr(obj.owner_user, 'get_full_name', lambda: '')() or obj.owner_user.email,
            'email': obj.owner_user.email,
        }

    def get_followers(self, obj):
        return [
            {
                'id': f.user.id,
                'name': getattr(f.user, 'get_full_name', lambda: '')() or f.user.email,
                'email': f.user.email,
            }
            for f in obj.followers.select_related('user').all()
        ]

    def get_tags(self, obj):
        return [
            {'tag_id': str(lt.tag.tag_id), 'name': lt.tag.name, 'color': lt.tag.color}
            for lt in obj.lead_tags.all()
        ]

    def get_custom_fields(self, obj):
        res = []
        for cfv in obj.custom_field_values.select_related('definition'):
            res.append({
                'field_id': str(cfv.definition.field_id),
                'field_name': cfv.definition.field_name,
                'field_label': cfv.definition.field_label,
                'field_type': cfv.definition.field_type,
                'value': cfv.get_plain_value(),
            })
        return res

    def get_recent_stage_history(self, obj):
        history = obj.stage_history.select_related('from_stage', 'to_stage').order_by('-created_at')[:10]
        return [
            {
                'history_id': str(h.history_id),
                'from_stage': h.from_stage.name if h.from_stage else None,
                'to_stage': h.to_stage.name,
                'actor_name': h.actor_name,
                'reason': h.reason,
                'created_at': h.created_at.isoformat(),
            }
            for h in history
        ]


class LeadCreateSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField(required=True)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    pipeline_id = serializers.UUIDField(required=False)
    stage_id = serializers.UUIDField(required=False)
    department_id = serializers.IntegerField(required=False, allow_null=True)
    owner_user_id = serializers.IntegerField(required=False, allow_null=True)
    priority = serializers.ChoiceField(choices=Lead.PRIORITY_CHOICES, default='MEDIUM', required=False)
    source = serializers.CharField(max_length=50, default='MANUAL', required=False)
    estimated_value = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, allow_null=True)
    currency = serializers.CharField(max_length=10, default='INR', required=False)
    win_probability = serializers.IntegerField(min_value=0, max_value=100, default=0, required=False)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    custom_fields = serializers.DictField(required=False)


class LeadUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    priority = serializers.ChoiceField(choices=Lead.PRIORITY_CHOICES, required=False)
    estimated_value = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, allow_null=True)
    currency = serializers.CharField(max_length=10, required=False)
    win_probability = serializers.IntegerField(min_value=0, max_value=100, required=False)
    version = serializers.IntegerField(required=False, help_text='Expected version for optimistic concurrency control')
    custom_fields = serializers.DictField(required=False)


class LeadAssignSerializer(serializers.Serializer):
    owner_user_id = serializers.IntegerField(required=False, allow_null=True)
    department_id = serializers.IntegerField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True, default='')
    method = serializers.CharField(default='MANUAL', required=False)
    version = serializers.IntegerField(required=False)


class LeadStageTransitionSerializer(serializers.Serializer):
    stage_id = serializers.UUIDField(required=True)
    reason = serializers.CharField(required=False, allow_blank=True, default='')
    version = serializers.IntegerField(required=False, help_text='Expected version for optimistic locking')


class LeadTagsSerializer(serializers.Serializer):
    tags = serializers.ListField(child=serializers.CharField(), required=True)


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = [
            'activity_id', 'customer_id', 'lead_id', 'activity_type',
            'title', 'description', 'actor_name', 'metadata', 'created_at'
        ]
        read_only_fields = ['activity_id', 'created_at']


class NoteSerializer(serializers.ModelSerializer):
    content = serializers.CharField(source='plain_content', read_only=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = ['note_id', 'customer_id', 'lead_id', 'author_user_id', 'author_name', 'content', 'is_pinned', 'created_at', 'updated_at']
        read_only_fields = ['note_id', 'author_user_id', 'author_name', 'created_at', 'updated_at']

    def get_author_name(self, obj):
        return getattr(obj.author_user, 'get_full_name', lambda: '')() or obj.author_user.email


class NoteCreateSerializer(serializers.Serializer):
    content = serializers.CharField(required=True)
    lead_id = serializers.UUIDField(required=False, allow_null=True)
    is_pinned = serializers.BooleanField(default=False, required=False)
