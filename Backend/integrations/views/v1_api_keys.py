import hashlib
import secrets
from datetime import timedelta
from django.utils import timezone
from rest_framework import status

from .base import BaseV1ApiView
from integrations.scopes import RequireScope, ALL_SCOPES
from integrations.rate_limiter import rate_limit
from integrations.models import ApiKey, ServiceAccount
from integrations.serializers import (
    ApiKeyResponseSerializer,
    ApiKeyCreateSerializer,
)


def generate_secure_api_key(prefix: str = 'cvx_live_') -> str:
    # 32 bytes cryptographically secure random urlsafe token (approx 43 chars)
    token = secrets.token_urlsafe(32)
    return f"{prefix}{token}"


class ApiKeyListCreateView(BaseV1ApiView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [RequireScope('integration:manage')()]
        return [RequireScope('integration:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request):
        qs = ApiKey.objects.filter(tenant=self.tenant).select_related('service_account').order_by('-created_at')
        serializer = ApiKeyResponseSerializer(qs, many=True)
        return self.success_response(serializer.data)

    @rate_limit(capacity=30, fill_rate=0.5)
    def post(self, request):
        serializer = ApiKeyCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                code='VALIDATION_ERROR',
                message='Invalid API key payload.',
                status_code=status.HTTP_400_BAD_REQUEST,
                details=serializer.errors,
            )

        validated = serializer.validated_data
        sa_id = validated.get('service_account_id')
        sa = None
        if sa_id:
            sa = ServiceAccount.objects.filter(pk=sa_id, tenant=self.tenant).first()
            if not sa:
                return self.error_response(
                    code='RESOURCE_NOT_FOUND',
                    message='Specified service account not found in this tenant.',
                    status_code=status.HTTP_404_NOT_FOUND,
                )

        # Scopes validation
        requested_scopes = validated.get('scopes', [])
        if not requested_scopes or '*' in requested_scopes:
            scopes = ['*']
        else:
            scopes = [s for s in requested_scopes if s in ALL_SCOPES or s.endswith(':*')]

        # Prefix & Secret generation
        prefix = 'cvx_live_'
        raw_secret = generate_secure_api_key(prefix)
        key_prefix = raw_secret[:16]  # e.g. cvx_live_a1b2c3d4
        secret_hash = hashlib.sha256(raw_secret.encode('utf-8')).hexdigest()

        days = validated.get('expires_in_days', 90)
        expires_at = timezone.now() + timedelta(days=days)

        api_key = ApiKey.objects.create(
            tenant=self.tenant,
            service_account=sa,
            name=validated['name'],
            key_prefix=key_prefix,
            secret_hash=secret_hash,
            scopes=scopes,
            ip_restrictions=validated.get('ip_restrictions', []),
            is_active=True,
            expires_at=expires_at,
            created_by=request.user if getattr(request.user, 'pk', None) and not getattr(request.user, 'is_service_account', False) else None,
        )

        from organization.models import AuditLog
        AuditLog.log(
            tenant=self.tenant,
            actor_name=getattr(request.user, 'email', 'System Operator'),
            actor_email=getattr(request.user, 'email', ''),
            action='API_KEY_CREATED',
            module='Security',
            resource=f'API Key #{api_key.id} ({api_key.name} - {key_prefix}...)',
            status='Success',
            metadata={'api_key_id': str(api_key.id), 'prefix': key_prefix, 'scopes': scopes}
        )

        data = ApiKeyResponseSerializer(api_key).data
        data['api_key'] = raw_secret
        data['warning'] = 'Store the complete secret securely. It is hashed and will NEVER be shown again.'
        return self.success_response(data, status_code=status.HTTP_201_CREATED)


class ApiKeyRevokeView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('integration:manage')()]

    @rate_limit(capacity=60, fill_rate=1.0)
    def post(self, request, pk):
        key = ApiKey.objects.filter(pk=pk, tenant=self.tenant).first()
        if not key:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='API key not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        key.is_active = False
        key.revoked_at = timezone.now()
        key.revoked_by = request.user if getattr(request.user, 'pk', None) and not getattr(request.user, 'is_service_account', False) else None
        key.save(update_fields=['is_active', 'revoked_at', 'revoked_by'])

        from organization.models import AuditLog
        AuditLog.log(
            tenant=self.tenant,
            actor_name=getattr(request.user, 'email', 'System Operator'),
            actor_email=getattr(request.user, 'email', ''),
            action='API_KEY_REVOKED',
            module='Security',
            resource=f'API Key #{key.id} ({key.name})',
            status='Success',
        )

        return self.success_response({'message': f'API key {key.name} revoked successfully.'})


class ApiKeyRotateView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('integration:manage')()]

    @rate_limit(capacity=30, fill_rate=0.5)
    def post(self, request, pk):
        old_key = ApiKey.objects.filter(pk=pk, tenant=self.tenant).first()
        if not old_key:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='API key not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Revoke old key
        old_key.is_active = False
        old_key.revoked_at = timezone.now()
        old_key.save(update_fields=['is_active', 'revoked_at'])

        # Generate fresh replacement key with same scopes & service account
        prefix = 'cvx_live_'
        raw_secret = generate_secure_api_key(prefix)
        key_prefix = raw_secret[:16]
        secret_hash = hashlib.sha256(raw_secret.encode('utf-8')).hexdigest()

        new_key = ApiKey.objects.create(
            tenant=self.tenant,
            service_account=old_key.service_account,
            name=f"{old_key.name} (Rotated)",
            key_prefix=key_prefix,
            secret_hash=secret_hash,
            scopes=old_key.scopes,
            ip_restrictions=old_key.ip_restrictions,
            is_active=True,
            expires_at=timezone.now() + timedelta(days=90),
            created_by=request.user if getattr(request.user, 'pk', None) and not getattr(request.user, 'is_service_account', False) else None,
        )

        from organization.models import AuditLog
        AuditLog.log(
            tenant=self.tenant,
            actor_name=getattr(request.user, 'email', 'System Operator'),
            actor_email=getattr(request.user, 'email', ''),
            action='API_KEY_ROTATED',
            module='Security',
            resource=f'Rotated Key #{old_key.id} -> #{new_key.id}',
            status='Success',
        )

        data = ApiKeyResponseSerializer(new_key).data
        data['api_key'] = raw_secret
        data['warning'] = 'Store the complete secret securely. It is hashed and will NEVER be shown again.'
        return self.success_response(data, status_code=status.HTTP_201_CREATED)

