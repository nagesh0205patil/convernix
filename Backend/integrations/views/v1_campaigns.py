from rest_framework import status
from .base import BaseV1ApiView
from integrations.scopes import RequireScope
from integrations.rate_limiter import rate_limit
from integrations.idempotency import enforce_idempotency
from integrations.outbox import emit_outbox_event
from integrations.events import EVENT_CAMPAIGN_CREATED, EVENT_CAMPAIGN_STARTED
from integrations.serializers import (
    CampaignResponseSerializer,
    CampaignCreateSerializer,
)
from campaigns.models import Campaign


class CampaignListCreateView(BaseV1ApiView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [RequireScope('campaign:create')()]
        return [RequireScope('campaign:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request):
        qs = Campaign.objects.filter(tenant=self.tenant).order_by('-created_at')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = CampaignResponseSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = CampaignResponseSerializer(qs, many=True)
        return self.success_response(serializer.data)

    @rate_limit(capacity=60, fill_rate=1.0)
    def post(self, request):
        serializer = CampaignCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                code='VALIDATION_ERROR',
                message='Invalid campaign payload.',
                status_code=status.HTTP_400_BAD_REQUEST,
                details=serializer.errors,
            )

        validated = serializer.validated_data
        campaign = Campaign.objects.create(
            tenant=self.tenant,
            name=validated['name'],
            message=validated['message'],
            target_audience=validated.get('target_audience', 'All customers'),
            scheduled_at=validated.get('scheduled_at'),
            status='scheduled' if validated.get('scheduled_at') else 'draft',
        )

        emit_outbox_event(
            tenant=self.tenant,
            event_type=EVENT_CAMPAIGN_CREATED,
            payload={
                'campaign_id': campaign.id,
                'name': campaign.name,
                'status': campaign.status,
            },
            correlation_id=request.request_id,
        )

        resp_serializer = CampaignResponseSerializer(campaign)
        return self.success_response(resp_serializer.data, status_code=status.HTTP_201_CREATED)


class CampaignDetailView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('campaign:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request, pk):
        campaign = Campaign.objects.filter(pk=pk, tenant=self.tenant).first()
        if not campaign:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Campaign not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = CampaignResponseSerializer(campaign)
        return self.success_response(serializer.data)


class CampaignExecuteView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('campaign:execute')()]

    @rate_limit(capacity=30, fill_rate=0.5)
    @enforce_idempotency()
    def post(self, request, pk):
        campaign = Campaign.objects.filter(pk=pk, tenant=self.tenant).first()
        if not campaign:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Campaign not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        campaign.status = 'running'
        campaign.save(update_fields=['status', 'updated_at'])

        emit_outbox_event(
            tenant=self.tenant,
            event_type=EVENT_CAMPAIGN_STARTED,
            payload={
                'campaign_id': campaign.id,
                'name': campaign.name,
                'target_audience': campaign.target_audience,
            },
            correlation_id=request.request_id,
        )

        return self.success_response({
            'message': 'Campaign execution dispatched.',
            'campaign_id': campaign.id,
            'status': campaign.status,
        })

