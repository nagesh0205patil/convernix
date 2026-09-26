import time
from rest_framework import status
from rest_framework.response import Response

from .base import BaseV1ApiView
from integrations.scopes import RequireScope
from integrations.rate_limiter import rate_limit
from integrations.webhooks import (
    generate_webhook_secret,
    execute_webhook_delivery,
    replay_webhook_delivery,
)
from integrations.ssrf import validate_safe_url, SSRFValidationError
from integrations.models import WebhookEndpoint, WebhookDelivery
from integrations.serializers import (
    WebhookEndpointResponseSerializer,
    WebhookEndpointCreateSerializer,
    WebhookDeliveryResponseSerializer,
)


class WebhookEndpointListCreateView(BaseV1ApiView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [RequireScope('webhook:manage')()]
        return [RequireScope('webhook:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request):
        qs = WebhookEndpoint.objects.filter(tenant=self.tenant).order_by('-created_at')
        serializer = WebhookEndpointResponseSerializer(qs, many=True)
        return self.success_response(serializer.data)

    @rate_limit(capacity=60, fill_rate=1.0)
    def post(self, request):
        serializer = WebhookEndpointCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                code='VALIDATION_ERROR',
                message='Invalid webhook configuration.',
                status_code=status.HTTP_400_BAD_REQUEST,
                details=serializer.errors,
            )

        url = serializer.validated_data['url']

        # SSRF validation before registering
        from django.conf import settings
        allow_http = getattr(settings, 'DEBUG', False) or getattr(settings, 'TESTING', False)
        try:
            validate_safe_url(url, allow_http=allow_http)
        except SSRFValidationError as err:
            return self.error_response(
                code='VALIDATION_ERROR',
                message=f'Webhook URL rejected: {err}',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        raw_secret = generate_webhook_secret()
        endpoint = WebhookEndpoint(
            tenant=self.tenant,
            name=serializer.validated_data['name'],
            url=url,
            event_filters=serializer.validated_data.get('event_filters', ['*']),
            created_by=request.user if getattr(request.user, 'pk', None) and not getattr(request.user, 'is_service_account', False) else None,
        )
        endpoint.set_signing_secret(raw_secret)
        endpoint.save()

        # Audit log
        from organization.models import AuditLog
        AuditLog.log(
            tenant=self.tenant,
            actor_name=getattr(request.user, 'email', 'Service Account'),
            actor_email=getattr(request.user, 'email', ''),
            action='WEBHOOK_CREATED',
            module='Integrations',
            resource=f'WebhookEndpoint #{endpoint.id} ({endpoint.name})',
            status='Success',
            metadata={'endpoint_id': str(endpoint.id), 'url': endpoint.url}
        )

        data = WebhookEndpointResponseSerializer(endpoint).data
        data['signing_secret'] = raw_secret
        data['warning'] = 'Store the signing secret securely. It will not be shown again.'
        return self.success_response(data, status_code=status.HTTP_201_CREATED)


class WebhookEndpointDetailView(BaseV1ApiView):
    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [RequireScope('webhook:manage')()]
        return [RequireScope('webhook:read')()]

    def get_object(self, pk):
        return WebhookEndpoint.objects.filter(pk=pk, tenant=self.tenant).first()

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request, pk):
        endpoint = self.get_object(pk)
        if not endpoint:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Webhook endpoint not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return self.success_response(WebhookEndpointResponseSerializer(endpoint).data)

    @rate_limit(capacity=60, fill_rate=1.0)
    def patch(self, request, pk):
        endpoint = self.get_object(pk)
        if not endpoint:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Webhook endpoint not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if 'url' in request.data:
            url = request.data['url']
            from django.conf import settings
            allow_http = getattr(settings, 'DEBUG', False) or getattr(settings, 'TESTING', False)
            try:
                validate_safe_url(url, allow_http=allow_http)
            except SSRFValidationError as err:
                return self.error_response(
                    code='VALIDATION_ERROR',
                    message=f'Webhook URL rejected: {err}',
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            endpoint.url = url

        if 'name' in request.data:
            endpoint.name = request.data['name']
        if 'event_filters' in request.data:
            endpoint.event_filters = request.data['event_filters']
        if 'status' in request.data:
            endpoint.status = request.data['status']
            if endpoint.status == 'active':
                endpoint.consecutive_failures = 0
                endpoint.disabled_reason = ''

        endpoint.save()

        from organization.models import AuditLog
        AuditLog.log(
            tenant=self.tenant,
            actor_name=getattr(request.user, 'email', 'Service Account'),
            actor_email=getattr(request.user, 'email', ''),
            action='WEBHOOK_UPDATED',
            module='Integrations',
            resource=f'WebhookEndpoint #{endpoint.id}',
            status='Success',
        )

        return self.success_response(WebhookEndpointResponseSerializer(endpoint).data)

    @rate_limit(capacity=60, fill_rate=1.0)
    def delete(self, request, pk):
        endpoint = self.get_object(pk)
        if not endpoint:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Webhook endpoint not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        endpoint_id = str(endpoint.id)
        endpoint.delete()

        from organization.models import AuditLog
        AuditLog.log(
            tenant=self.tenant,
            actor_name=getattr(request.user, 'email', 'Service Account'),
            actor_email=getattr(request.user, 'email', ''),
            action='WEBHOOK_DELETED',
            module='Integrations',
            resource=f'WebhookEndpoint #{endpoint_id}',
            status='Success',
        )

        return self.success_response({'message': 'Webhook endpoint deleted successfully.'})


class WebhookRotateSecretView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('webhook:manage')()]

    @rate_limit(capacity=30, fill_rate=0.5)
    def post(self, request, pk):
        endpoint = WebhookEndpoint.objects.filter(pk=pk, tenant=self.tenant).first()
        if not endpoint:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Webhook endpoint not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        new_secret = generate_webhook_secret()
        endpoint.set_signing_secret(new_secret)
        endpoint.save(update_fields=['encrypted_signing_secret', 'updated_at'])

        from organization.models import AuditLog
        AuditLog.log(
            tenant=self.tenant,
            actor_name=getattr(request.user, 'email', 'Service Account'),
            actor_email=getattr(request.user, 'email', ''),
            action='WEBHOOK_SECRET_ROTATED',
            module='Integrations',
            resource=f'WebhookEndpoint #{endpoint.id}',
            status='Success',
        )

        return self.success_response({
            'message': 'Webhook signing secret rotated successfully.',
            'signing_secret': new_secret,
            'warning': 'Store this secret securely. It will not be displayed again.',
        })


class WebhookTestPingView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('webhook:manage')()]

    @rate_limit(capacity=30, fill_rate=0.5)
    def post(self, request, pk):
        endpoint = WebhookEndpoint.objects.filter(pk=pk, tenant=self.tenant).first()
        if not endpoint:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Webhook endpoint not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        import uuid
        test_delivery = WebhookDelivery.objects.create(
            tenant=self.tenant,
            endpoint=endpoint,
            event_id=f"test_{uuid.uuid4().hex[:12]}",
            event_type='webhook.ping',
            payload={
                'event': 'webhook.ping',
                'timestamp': time.time(),
                'message': 'This is a test webhook payload from Convernix.',
                'tenant_id': self.tenant.id,
            },
            attempt_number=1,
            status='retrying',
        )

        result_delivery = execute_webhook_delivery(str(test_delivery.id))
        return self.success_response(WebhookDeliveryResponseSerializer(result_delivery).data)


class WebhookDeliveryListView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('webhook:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request):
        qs = WebhookDelivery.objects.filter(tenant=self.tenant).select_related('endpoint').order_by('-created_at')

        endpoint_id = request.query_params.get('endpoint_id')
        if endpoint_id:
            qs = qs.filter(endpoint_id=endpoint_id)

        status_param = request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = WebhookDeliveryResponseSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = WebhookDeliveryResponseSerializer(qs, many=True)
        return self.success_response(serializer.data)


class WebhookReplayView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('webhook:manage')()]

    @rate_limit(capacity=60, fill_rate=1.0)
    def post(self, request, pk):
        delivery = WebhookDelivery.objects.filter(pk=pk, tenant=self.tenant).select_related('endpoint').first()
        if not delivery:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Webhook delivery record not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        replayed = replay_webhook_delivery(delivery, actor=request.user)
        return self.success_response(WebhookDeliveryResponseSerializer(replayed).data)

