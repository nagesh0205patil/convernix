from .base import BaseV1ApiView
from integrations.scopes import RequireScope
from integrations.rate_limiter import rate_limit
from integrations.serializers import TemplateResponseSerializer
from organization.models import NotificationTemplate


class TemplateListView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('campaign:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request):
        qs = NotificationTemplate.objects.filter(tenant=self.tenant).order_by('-updated_at')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = TemplateResponseSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TemplateResponseSerializer(qs, many=True)
        return self.success_response(serializer.data)

