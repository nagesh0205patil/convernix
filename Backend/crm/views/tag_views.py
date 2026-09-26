import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from crm.models import Tag
from crm.serializers import TagSerializer
from users.tenant_context import require_request_tenant
from users.permissions import has_tenant_permission

logger = logging.getLogger(__name__)


class TagListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = require_request_tenant(request)
        tags = Tag.objects.filter(tenant=tenant)
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)

    def post(self, request):
        tenant = require_request_tenant(request)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'tag.manage')):
            raise PermissionDenied("You do not have permission to manage tags.")

        name = request.data.get('name', '').strip()
        if not name:
            raise ValidationError({'name': 'Tag name is required.'})

        tag, created = Tag.objects.get_or_create(
            tenant=tenant,
            name=name,
            defaults={
                'color': request.data.get('color', '#6366f1'),
                'description': request.data.get('description', ''),
            },
        )
        if not created and 'color' in request.data:
            tag.color = request.data['color']
            tag.save()

        serializer = TagSerializer(tag)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class TagDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_tag(self, request, pk):
        tenant = require_request_tenant(request)
        tag = Tag.objects.filter(tenant=tenant, tag_id=pk).first()
        if not tag:
            raise NotFound({'detail': 'Tag not found.'})
        return tenant, tag

    def patch(self, request, pk):
        tenant, tag = self._get_tag(request, pk)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'tag.manage')):
            raise PermissionDenied("You do not have permission to manage tags.")

        if 'name' in request.data:
            tag.name = request.data['name'].strip()
        if 'color' in request.data:
            tag.color = request.data['color']
        if 'description' in request.data:
            tag.description = request.data['description']

        tag.save()
        serializer = TagSerializer(tag)
        return Response(serializer.data)

    def delete(self, request, pk):
        tenant, tag = self._get_tag(request, pk)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'tag.manage')):
            raise PermissionDenied("You do not have permission to manage tags.")

        tag.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
