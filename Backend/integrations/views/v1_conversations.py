from rest_framework import status
from .base import BaseV1ApiView
from integrations.scopes import RequireScope
from integrations.rate_limiter import rate_limit
from integrations.outbox import emit_outbox_event
from integrations.events import EVENT_CONVERSATION_CLOSED
from integrations.serializers import (
    ConversationResponseSerializer,
    MessageResponseSerializer,
)
from whatsapp.models import Enquiry, WhatsAppMessage


class ConversationListView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('conversation:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request):
        qs = Enquiry.objects.filter(tenant=self.tenant).select_related('customer', 'department').order_by('-created_at')

        status_param = request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ConversationResponseSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ConversationResponseSerializer(qs, many=True)
        return self.success_response(serializer.data)


class ConversationDetailView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('conversation:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request, pk):
        enquiry = Enquiry.objects.filter(pk=pk, tenant=self.tenant).select_related('customer', 'department').first()
        if not enquiry:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Conversation not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        messages = WhatsAppMessage.objects.filter(enquiry=enquiry).order_by('timestamp')
        conv_data = ConversationResponseSerializer(enquiry).data
        conv_data['messages'] = MessageResponseSerializer(messages, many=True).data

        return self.success_response(conv_data)


class ConversationCloseView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('conversation:read')()]

    @rate_limit(capacity=60, fill_rate=1.0)
    def post(self, request, pk):
        enquiry = Enquiry.objects.filter(pk=pk, tenant=self.tenant).first()
        if not enquiry:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Conversation not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        enquiry.status = 'closed'
        enquiry.save(update_fields=['status', 'updated_at'])

        emit_outbox_event(
            tenant=self.tenant,
            event_type=EVENT_CONVERSATION_CLOSED,
            payload={
                'id': enquiry.id,
                'reference': enquiry.reference,
                'status': 'closed',
            },
            correlation_id=request.request_id,
        )

        return self.success_response({'message': 'Conversation closed successfully.', 'id': enquiry.id})

