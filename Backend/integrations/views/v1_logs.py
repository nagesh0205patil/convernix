from rest_framework import status
from .base import BaseV1ApiView
from integrations.scopes import RequireScope
from integrations.rate_limiter import rate_limit
from integrations.models import IntegrationApiLog
from organization.models import AuditLog


class IntegrationApiLogListView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('integration:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request):
        qs = IntegrationApiLog.objects.filter(tenant=self.tenant).order_by('-created_at')

        status_code = request.query_params.get('status_code')
        if status_code:
            qs = qs.filter(status_code=int(status_code))

        method = request.query_params.get('method')
        if method:
            qs = qs.filter(http_method=method.upper())

        page = self.paginate_queryset(qs)
        if page is not None:
            data = [{
                'id': str(l.id),
                'request_id': l.request_id,
                'endpoint': l.endpoint,
                'method': l.http_method,
                'status_code': l.status_code,
                'duration_ms': l.duration_ms,
                'source_ip': l.source_ip,
                'user_agent': l.user_agent,
                'timestamp': l.created_at.isoformat(),
            } for l in page]
            return self.get_paginated_response(data)

        data = [{
            'id': str(l.id),
            'request_id': l.request_id,
            'endpoint': l.endpoint,
            'method': l.http_method,
            'status_code': l.status_code,
            'duration_ms': l.duration_ms,
            'source_ip': l.source_ip,
            'user_agent': l.user_agent,
            'timestamp': l.created_at.isoformat(),
        } for l in qs[:50]]
        return self.success_response(data)


class IntegrationAuditLogListView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('integration:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request):
        qs = AuditLog.objects.filter(
            tenant=self.tenant,
            module__in=['Integrations', 'Security', 'IAM']
        ).order_by('-created_at')

        page = self.paginate_queryset(qs)
        if page is not None:
            data = [{
                'id': l.id,
                'actor_name': l.actor_name,
                'actor_email': l.actor_email,
                'action': l.action,
                'module': l.module,
                'resource': l.resource,
                'status': l.status,
                'tamper_hash': l.tamper_hash,
                'timestamp': l.created_at.isoformat(),
            } for l in page]
            return self.get_paginated_response(data)

        data = [{
            'id': l.id,
            'actor_name': l.actor_name,
            'actor_email': l.actor_email,
            'action': l.action,
            'module': l.module,
            'resource': l.resource,
            'status': l.status,
            'tamper_hash': l.tamper_hash,
            'timestamp': l.created_at.isoformat(),
        } for l in qs[:50]]
        return self.success_response(data)

