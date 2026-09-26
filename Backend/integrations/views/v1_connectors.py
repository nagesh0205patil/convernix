from django.utils import timezone
from rest_framework import status
from .base import BaseV1ApiView
from integrations.scopes import RequireScope
from integrations.rate_limiter import rate_limit
from integrations.connectors.registry import get_all_manifests, get_connector_class, get_connector_instance_handler
from integrations.models import (
    ConnectorInstance,
    ConnectorFieldMapping,
    ConnectorSyncJob,
)
from integrations.serializers import (
    ConnectorInstanceResponseSerializer,
    ConnectorFieldMappingSerializer,
)


class ConnectorMarketplaceView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('integration:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request):
        manifests = get_all_manifests()
        installed_keys = set(
            ConnectorInstance.objects.filter(tenant=self.tenant).exclude(status='disconnected').values_list('connector_key', flat=True)
        )

        data = []
        for m in manifests:
            data.append({
                'key': m.key,
                'name': m.name,
                'category': m.category,
                'auth_type': m.auth_type,
                'capabilities': m.capabilities,
                'supported_objects': m.supported_objects,
                'icon': m.icon,
                'description': m.description,
                'docs_url': m.docs_url,
                'configuration_schema': m.configuration_schema,
                'is_installed': m.key in installed_keys,
            })
        return self.success_response(data)


class ConnectorInstanceListCreateView(BaseV1ApiView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [RequireScope('integration:manage')()]
        return [RequireScope('integration:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request):
        qs = ConnectorInstance.objects.filter(tenant=self.tenant).order_by('-created_at')
        serializer = ConnectorInstanceResponseSerializer(qs, many=True)
        return self.success_response(serializer.data)

    @rate_limit(capacity=30, fill_rate=0.5)
    def post(self, request):
        connector_key = request.data.get('connector_key')
        name = request.data.get('name')
        config = request.data.get('config', {})
        credentials = request.data.get('credentials', {})

        if not connector_key or not name:
            return self.error_response(
                code='VALIDATION_ERROR',
                message='connector_key and name are required.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        connector_cls = get_connector_class(connector_key)
        if not connector_cls:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message=f"Connector '{connector_key}' is not available.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        manifest = connector_cls.get_manifest()

        instance = ConnectorInstance.objects.filter(tenant=self.tenant, connector_key=connector_key, name=name).first()
        if not instance:
            instance = ConnectorInstance(
                tenant=self.tenant,
                connector_key=connector_key,
                name=name,
                auth_type=manifest.auth_type,
                config=config,
                status='active',
                created_by=request.user if getattr(request.user, 'pk', None) and not getattr(request.user, 'is_service_account', False) else None,
            )
        else:
            instance.config = config
            instance.status = 'active'

        if credentials:
            instance.set_credentials(credentials)

        instance.save()

        # Audit log
        from organization.models import AuditLog
        AuditLog.log(
            tenant=self.tenant,
            actor_name=getattr(request.user, 'email', 'System Operator'),
            actor_email=getattr(request.user, 'email', ''),
            action='CONNECTOR_CONNECTED',
            module='Integrations',
            resource=f'{manifest.name} ({instance.name})',
            status='Success',
        )

        return self.success_response(ConnectorInstanceResponseSerializer(instance).data, status_code=status.HTTP_201_CREATED)


class ConnectorInstanceDetailView(BaseV1ApiView):
    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [RequireScope('integration:manage')()]
        return [RequireScope('integration:read')()]

    def get_object(self, pk):
        return ConnectorInstance.objects.filter(pk=pk, tenant=self.tenant).first()

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request, pk):
        instance = self.get_object(pk)
        if not instance:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Connector instance not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return self.success_response(ConnectorInstanceResponseSerializer(instance).data)

    @rate_limit(capacity=60, fill_rate=1.0)
    def patch(self, request, pk):
        instance = self.get_object(pk)
        if not instance:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Connector instance not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if 'config' in request.data:
            instance.config = request.data['config']
        if 'credentials' in request.data:
            instance.set_credentials(request.data['credentials'])
        if 'conflict_strategy' in request.data:
            instance.conflict_strategy = request.data['conflict_strategy']
        if 'sync_direction' in request.data:
            instance.sync_direction = request.data['sync_direction']
        if 'status' in request.data:
            instance.status = request.data['status']

        instance.save()

        from organization.models import AuditLog
        AuditLog.log(
            tenant=self.tenant,
            actor_name=getattr(request.user, 'email', 'System Operator'),
            actor_email=getattr(request.user, 'email', ''),
            action='CONNECTOR_CONFIGURATION_CHANGED',
            module='Integrations',
            resource=f'Connector #{instance.id} ({instance.name})',
            status='Success',
        )

        return self.success_response(ConnectorInstanceResponseSerializer(instance).data)


class ConnectorTestConnectionView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('integration:manage')()]

    @rate_limit(capacity=30, fill_rate=0.5)
    def post(self, request, pk):
        instance = ConnectorInstance.objects.filter(pk=pk, tenant=self.tenant).first()
        if not instance:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Connector instance not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        handler = get_connector_instance_handler(instance)
        if not handler:
            return self.error_response(
                code='CONNECTOR_UNAVAILABLE',
                message=f"Handler not found for {instance.connector_key}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        success, msg = handler.test_connection()
        instance.health_status = 'healthy' if success else 'failing'
        instance.health_message = msg
        instance.last_health_check_at = timezone.now()
        instance.save(update_fields=['health_status', 'health_message', 'last_health_check_at'])

        return self.success_response({
            'success': success,
            'message': msg,
            'health_status': instance.health_status,
        })


class ConnectorFieldMappingView(BaseV1ApiView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [RequireScope('integration:manage')()]
        return [RequireScope('integration:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request, pk):
        instance = ConnectorInstance.objects.filter(pk=pk, tenant=self.tenant).first()
        if not instance:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Connector instance not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        mappings = ConnectorFieldMapping.objects.filter(connector_instance=instance)
        return self.success_response(ConnectorFieldMappingSerializer(mappings, many=True).data)

    @rate_limit(capacity=60, fill_rate=1.0)
    def post(self, request, pk):
        instance = ConnectorInstance.objects.filter(pk=pk, tenant=self.tenant).first()
        if not instance:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Connector instance not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        mappings_list = request.data.get('mappings', [])
        saved = []
        for item in mappings_list:
            mapping, _ = ConnectorFieldMapping.objects.update_or_create(
                tenant=self.tenant,
                connector_instance=instance,
                object_type=item['object_type'],
                convernix_field=item['convernix_field'],
                defaults={
                    'external_field': item['external_field'],
                    'transformation_type': item.get('transformation_type', 'direct'),
                    'transformation_config': item.get('transformation_config', {}),
                    'is_active': item.get('is_active', True),
                }
            )
            saved.append(mapping)

        return self.success_response(ConnectorFieldMappingSerializer(saved, many=True).data)
