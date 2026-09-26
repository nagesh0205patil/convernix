import uuid
from django.db import transaction
from django.utils import timezone
from rest_framework import status

from .base import BaseV1ApiView
from integrations.scopes import RequireScope
from integrations.rate_limiter import rate_limit
from integrations.idempotency import enforce_idempotency
from integrations.outbox import emit_outbox_event
from integrations.events import EVENT_MESSAGE_SENT
from integrations.serializers import (
    MessageResponseSerializer,
    MessageSendSerializer,
)
from whatsapp.models import WhatsAppMessage, Customer, BusinessNumber, Enquiry, Department


class MessageListView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('message:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request):
        qs = WhatsAppMessage.objects.filter(customer__tenant=self.tenant).select_related('customer', 'enquiry').order_by('-timestamp')

        customer_id = request.query_params.get('customer_id')
        if customer_id:
            qs = qs.filter(customer_id=customer_id)

        enquiry_id = request.query_params.get('enquiry_id')
        if enquiry_id:
            qs = qs.filter(enquiry_id=enquiry_id)

        direction = request.query_params.get('direction')
        if direction:
            qs = qs.filter(direction=direction)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = MessageResponseSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MessageResponseSerializer(qs, many=True)
        return self.success_response(serializer.data)


class MessageSendView(BaseV1ApiView):
    def get_permissions(self):
        return [RequireScope('message:send')()]

    @rate_limit(capacity=60, fill_rate=1.0)
    @enforce_idempotency()
    def post(self, request):
        serializer = MessageSendSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                code='VALIDATION_ERROR',
                message='Invalid message send payload.',
                status_code=status.HTTP_400_BAD_REQUEST,
                details=serializer.errors,
            )

        validated = serializer.validated_data
        to_phone = validated['to_phone']
        msg_text = validated['message']

        # Resolve Customer
        from organization.services.crypto_service import compute_blind_index
        p_hash = compute_blind_index(self.tenant, to_phone, 'phone')
        customer = Customer.objects.filter(tenant=self.tenant, phone_hash=p_hash).first()

        with transaction.atomic():
            if not customer:
                customer = Customer.objects.create(
                    tenant=self.tenant,
                    whatsapp_number=to_phone,
                    full_name=to_phone,
                )

            # Resolve active enquiry or create support enquiry
            enquiry = Enquiry.objects.filter(tenant=self.tenant, customer=customer).exclude(status='closed').order_by('-created_at').first()
            if not enquiry:
                dept = Department.objects.filter(tenant=self.tenant).first()
                if not dept:
                    dept = Department.objects.create(tenant=self.tenant, name='Support', slug='support')
                enquiry = Enquiry.objects.create(
                    tenant=self.tenant,
                    customer=customer,
                    department=dept,
                    message=msg_text,
                    status='in_progress',
                    source='api_outbound',
                )

            # Create outgoing WhatsAppMessage
            wam_id = f"wamid.{uuid.uuid4().hex}"
            message = WhatsAppMessage.objects.create(
                whatsapp_message_id=wam_id,
                customer=customer,
                enquiry=enquiry,
                direction='outgoing',
                message_type='text',
                content=msg_text,
                status='sent',
                timestamp=timezone.now(),
            )

            emit_outbox_event(
                tenant=self.tenant,
                event_type=EVENT_MESSAGE_SENT,
                payload={
                    'message_id': message.id,
                    'whatsapp_message_id': message.whatsapp_message_id,
                    'customer_id': customer.id,
                    'to_phone': to_phone,
                    'direction': 'outgoing',
                    'content': msg_text,
                    'timestamp': message.timestamp.isoformat(),
                },
                correlation_id=request.request_id,
            )

        resp_data = MessageResponseSerializer(message).data
        return self.success_response(resp_data, status_code=status.HTTP_201_CREATED)

