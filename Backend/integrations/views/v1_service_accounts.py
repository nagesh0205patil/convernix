from rest_framework import status
from .base import BaseV1ApiView
from integrations.scopes import RequireScope
from integrations.rate_limiter import rate_limit
from integrations.models import ServiceAccount
from integrations.serializers import (
    ServiceAccountSerializer,
    ServiceAccountCreateSerializer,
)


class ServiceAccountListCreateView(BaseV1ApiView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [RequireScope('integration:manage')()]
        return [RequireScope('integration:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request):
        qs = ServiceAccount.objects.filter(tenant=self.tenant).order_by('-created_at')
        serializer = ServiceAccountSerializer(qs, many=True)
        return self.success_response(serializer.data)

    @rate_limit(capacity=60, fill_rate=1.0)
    def post(self, request):
        serializer = ServiceAccountCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                code='VALIDATION_ERROR',
                message='Invalid service account data.',
                status_code=status.HTTP_400_BAD_REQUEST,
                details=serializer.errors,
            )

        sa = ServiceAccount.objects.create(
            tenant=self.tenant,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            status='active',
            created_by=request.user if getattr(request.user, 'pk', None) and not getattr(request.user, 'is_service_account', False) else None,
        )

        from organization.models import AuditLog
        AuditLog.log(
            tenant=self.tenant,
            actor_name=getattr(request.user, 'email', 'System Operator'),
            actor_email=getattr(request.user, 'email', ''),
            action='SERVICE_ACCOUNT_CREATED',
            module='IAM',
            resource=f'ServiceAccount #{sa.id} ({sa.name})',
            status='Success',
        )

        return self.success_response(ServiceAccountSerializer(sa).data, status_code=status.HTTP_201_CREATED)


class ServiceAccountDetailView(BaseV1ApiView):
    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [RequireScope('integration:manage')()]
        return [RequireScope('integration:read')()]

    def get_object(self, pk):
        return ServiceAccount.objects.filter(pk=pk, tenant=self.tenant).first()

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request, pk):
        sa = self.get_object(pk)
        if not sa:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Service account not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return self.success_response(ServiceAccountSerializer(sa).data)

    @rate_limit(capacity=60, fill_rate=1.0)
    def patch(self, request, pk):
        sa = self.get_object(pk)
        if not sa:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Service account not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if 'name' in request.data:
            sa.name = request.data['name']
        if 'description' in request.data:
            sa.description = request.data['description']
        if 'status' in request.data:
            new_status = request.data['status']
            if new_status in ('active', 'disabled', 'revoked'):
                sa.status = new_status
                if new_status in ('disabled', 'revoked'):
                    # Disable active api keys for this service account
                    sa.api_keys.filter(is_active=True).update(is_active=False)

        sa.save()

        from organization.models import AuditLog
        AuditLog.log(
            tenant=self.tenant,
            actor_name=getattr(request.user, 'email', 'System Operator'),
            actor_email=getattr(request.user, 'email', ''),
            action='SERVICE_ACCOUNT_UPDATED',
            module='IAM',
            resource=f'ServiceAccount #{sa.id}',
            status='Success',
        )

        return self.success_response(ServiceAccountSerializer(sa).data)

    @rate_limit(capacity=60, fill_rate=1.0)
    def delete(self, request, pk):
        sa = self.get_object(pk)
        if not sa:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Service account not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        sa_id = str(sa.id)
        sa.status = 'revoked'
        sa.api_keys.filter(is_active=True).update(is_active=False)
        sa.save(update_fields=['status'])

        from organization.models import AuditLog
        AuditLog.log(
            tenant=self.tenant,
            actor_name=getattr(request.user, 'email', 'System Operator'),
            actor_email=getattr(request.user, 'email', ''),
            action='SERVICE_ACCOUNT_DISABLED',
            module='IAM',
            resource=f'ServiceAccount #{sa_id}',
            status='Success',
        )

        return self.success_response({'message': 'Service account revoked and disabled.'})

