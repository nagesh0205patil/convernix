from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Tenant
from .permissions import access_role

User = get_user_model()


class TenantSerializer(serializers.ModelSerializer):
    tier_display = serializers.CharField(source='get_tier_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    users_count = serializers.SerializerMethodField()
    numbers_count = serializers.SerializerMethodField()
    campaigns_count = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = (
            'id', 'name', 'slug', 'tier', 'tier_display', 'status', 'status_display',
            'max_numbers', 'max_users', 'max_campaigns_monthly',
            'users_count', 'numbers_count', 'campaigns_count',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_users_count(self, obj):
        return obj.users.filter(is_active=True).count()

    def get_numbers_count(self, obj):
        return obj.business_numbers.filter(is_active=True).count()

    def get_campaigns_count(self, obj):
        return obj.campaigns.count()


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    tenant = TenantSerializer(read_only=True)

    def get_role(self, obj):
        return access_role(obj)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'phone_number',
            'whatsapp_number',
            'team_name',
            'role',
            'number_access',
            'organization',
            'tenant',
            'is_staff',
            'is_superuser',
            'created_at',
        )
        read_only_fields = ('id', 'created_at', 'is_staff', 'is_superuser')


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'first_name', 'last_name', 'phone_number', 'organization')

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class TeamMemberSerializer(serializers.ModelSerializer):
    effective_role = serializers.SerializerMethodField()

    def get_effective_role(self, obj):
        return access_role(obj)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'phone_number',
            'whatsapp_number',
            'team_name',
            'role',
            'number_access',
            'organization',
            'is_active',
            'effective_role',
        )
        read_only_fields = ('id', 'is_active')

    def update(self, instance, validated_data):
        if 'role' in validated_data:
            validated_data['is_staff'] = validated_data['role'] in ('admin', 'owner')
        return super().update(instance, validated_data)

    def validate_role(self, value):
        requester = self.context['request'].user
        if value == 'owner' and not (requester.is_superuser or requester.role == 'owner'):
            raise serializers.ValidationError('Only an Owner can grant Owner access.')
        return value


class IAMInvitationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)
    number_access = serializers.ChoiceField(choices=User.NUMBER_ACCESS_CHOICES, default='both')
    team_name = serializers.CharField(max_length=50, default='Support', required=False)

    def validate_role(self, value):
        requester = self.context['request'].user
        if value == 'owner' and not (requester.is_superuser or requester.role == 'owner'):
            raise serializers.ValidationError('Only an Owner can invite another Owner.')
        return value


class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.CharField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)


class RegisterTenantSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=150)
    tier = serializers.ChoiceField(choices=Tenant.TIER_CHOICES, default='small')
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('A user with this email address already exists.')
        return email


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['username'] = user.username
        token['tenant_id'] = user.tenant_id if user.tenant else None
        token['is_superuser'] = user.is_superuser
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.tenant and self.user.tenant.status == 'suspended' and not self.user.is_superuser:
            raise serializers.ValidationError({
                'detail': 'Your organization account has been suspended. Please contact platform support.'
            })
        data['user'] = UserSerializer(self.user).data
        return data
