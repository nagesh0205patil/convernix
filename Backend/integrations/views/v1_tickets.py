from django.db import transaction
from rest_framework import status

from .base import BaseV1ApiView
from integrations.scopes import RequireScope
from integrations.rate_limiter import rate_limit
from integrations.idempotency import enforce_idempotency
from integrations.outbox import emit_outbox_event
from integrations.events import EVENT_TICKET_CREATED, EVENT_TICKET_UPDATED
from integrations.serializers import (
    TicketResponseSerializer,
    TicketCreateSerializer,
    TicketUpdateSerializer,
)
from whatsapp.models import Enquiry, Customer, Department


class TicketListCreateView(BaseV1ApiView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [RequireScope('ticket:create')()]
        return [RequireScope('ticket:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request):
        qs = Enquiry.objects.filter(tenant=self.tenant).select_related('customer', 'department').order_by('-created_at')

        status_param = request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = TicketResponseSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TicketResponseSerializer(qs, many=True)
        return self.success_response(serializer.data)

    @rate_limit(capacity=60, fill_rate=1.0)
    @enforce_idempotency()
    def post(self, request):
        serializer = TicketCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                code='VALIDATION_ERROR',
                message='Invalid ticket payload.',
                status_code=status.HTTP_400_BAD_REQUEST,
                details=serializer.errors,
            )

        validated = serializer.validated_data
        raw_phone = validated['customer_phone']

        dept_name = validated.get('department_name', 'Support')
        dept = Department.objects.filter(tenant=self.tenant, name__iexact=dept_name).first()
        if not dept:
            dept = Department.objects.filter(tenant=self.tenant).first()
            if not dept:
                dept = Department.objects.create(tenant=self.tenant, name='Support', slug='support')

        with transaction.atomic():
            from organization.services.crypto_service import compute_blind_index
            p_hash = compute_blind_index(self.tenant, raw_phone, 'phone')
            customer = Customer.objects.filter(tenant=self.tenant, phone_hash=p_hash).first()
            if not customer:
                customer = Customer.objects.create(
                    tenant=self.tenant,
                    whatsapp_number=raw_phone,
                    full_name=validated['customer_name'],
                    email=validated.get('customer_email', ''),
                )

            enquiry = Enquiry.objects.create(
                tenant=self.tenant,
                customer=customer,
                department=dept,
                message=validated['message'],
                status='new',
                source='ticket_api',
            )

            emit_outbox_event(
                tenant=self.tenant,
                event_type=EVENT_TICKET_CREATED,
                payload={
                    'ticket_id': enquiry.id,
                    'reference': enquiry.reference,
                    'customer_name': validated['customer_name'],
                    'customer_phone': raw_phone,
                    'department': dept.name,
                    'message': validated['message'],
                    'status': 'new',
                },
                correlation_id=request.request_id,
            )

        resp_serializer = TicketResponseSerializer(enquiry)
        return self.success_response(resp_serializer.data, status_code=status.HTTP_201_CREATED)


class TicketDetailView(BaseV1ApiView):
    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [RequireScope('ticket:update')()]
        return [RequireScope('ticket:read')()]

    def get_object(self, pk):
        return Enquiry.objects.filter(pk=pk, tenant=self.tenant).select_related('customer', 'department').first()

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request, pk):
        ticket = self.get_object(pk)
        if not ticket:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Ticket not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = TicketResponseSerializer(ticket)
        return self.success_response(serializer.data)

    @rate_limit(capacity=60, fill_rate=1.0)
    def patch(self, request, pk):
        ticket = self.get_object(pk)
        if not ticket:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Ticket not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = TicketUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return self.error_response(
                code='VALIDATION_ERROR',
                message='Invalid update data.',
                status_code=status.HTTP_400_BAD_REQUEST,
                details=serializer.errors,
            )

        with transaction.atomic():
            if 'status' in serializer.validated_data:
                ticket.status = serializer.validated_data['status']
            if 'department_name' in serializer.validated_data:
                d_name = serializer.validated_data['department_name']
                dept = Department.objects.filter(tenant=self.tenant, name__iexact=d_name).first()
                if dept:
                    ticket.department = dept
            ticket.save()

            emit_outbox_event(
                tenant=self.tenant,
                event_type=EVENT_TICKET_UPDATED,
                payload={
                    'ticket_id': ticket.id,
                    'reference': ticket.reference,
                    'status': ticket.status,
                    'department': ticket.department.name,
                },
                correlation_id=request.request_id,
            )

        resp_serializer = TicketResponseSerializer(ticket)
        return self.success_response(resp_serializer.data)

