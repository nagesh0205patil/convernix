import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from crm.models import CustomFieldDefinition
from crm.serializers import CustomFieldDefinitionSerializer
from users.tenant_context import require_request_tenant
from users.permissions import has_tenant_permission

logger = logging.getLogger(__name__)


class CustomFieldDefinitionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = require_request_tenant(request)
        entity_type = request.query_params.get('entity_type')
        qs = CustomFieldDefinition.objects.filter(tenant=tenant, is_active=True)
        if entity_type:
            qs = qs.filter(entity_type=entity_type.upper())
        serializer = CustomFieldDefinitionSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        tenant = require_request_tenant(request)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'custom_field.manage')):
            raise PermissionDenied("You do not have permission to manage custom fields.")

        serializer = CustomFieldDefinitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        field_name = data['field_name'].lower().replace(' ', '_')

        if CustomFieldDefinition.objects.filter(tenant=tenant, entity_type=data.get('entity_type', 'CUSTOMER'), field_name=field_name).exists():
            raise ValidationError({'field_name': 'A custom field with this identifier already exists.', 'code': 'INVALID_CUSTOM_FIELD'})

        definition = CustomFieldDefinition.objects.create(
            tenant=tenant,
            entity_type=data.get('entity_type', 'CUSTOMER'),
            field_name=field_name,
            field_label=data['field_label'],
            field_type=data['field_type'],
            is_required=data.get('is_required', False),
            is_unique=data.get('is_unique', False),
            is_searchable=data.get('is_searchable', False),
            is_sensitive_pii=data.get('is_sensitive_pii', False),
            is_visible=data.get('is_visible', True),
            is_editable=data.get('is_editable', True),
            default_value=data.get('default_value'),
            validation_rules=data.get('validation_rules', {}),
            options=data.get('options', []),
            display_order=data.get('display_order', 0),
        )

        out_serializer = CustomFieldDefinitionSerializer(definition)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class CustomFieldDefinitionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_definition(self, request, pk):
        tenant = require_request_tenant(request)
        definition = CustomFieldDefinition.objects.filter(tenant=tenant, field_id=pk).first()
        if not definition:
            raise NotFound({'detail': 'Custom field definition not found.'})
        return tenant, definition

    def patch(self, request, pk):
        tenant, definition = self._get_definition(request, pk)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'custom_field.manage')):
            raise PermissionDenied("You do not have permission to manage custom fields.")

        serializer = CustomFieldDefinitionSerializer(definition, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        tenant, definition = self._get_definition(request, pk)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'custom_field.manage')):
            raise PermissionDenied("You do not have permission to manage custom fields.")

        definition.is_active = False
        definition.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)
