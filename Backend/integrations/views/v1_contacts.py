from django.db import transaction
from rest_framework import status

from .base import BaseV1ApiView
from integrations.scopes import RequireScope
from integrations.rate_limiter import rate_limit
from integrations.idempotency import enforce_idempotency
from integrations.outbox import emit_outbox_event
from integrations.events import EVENT_CONTACT_CREATED, EVENT_CONTACT_UPDATED
from integrations.serializers import (
    ContactResponseSerializer,
    ContactCreateSerializer,
    ContactUpdateSerializer,
)
from whatsapp.models import Customer


class ContactListCreateView(BaseV1ApiView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [RequireScope('contact:create')()]
        return [RequireScope('contact:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request):
        qs = Customer.objects.filter(tenant=self.tenant).order_by('-created_at')

        phone_param = request.query_params.get('phone')
        if phone_param:
            from organization.services.crypto_service import compute_blind_index
            p_hash = compute_blind_index(self.tenant, phone_param, 'phone')
            qs = qs.filter(phone_hash=p_hash)

        email_param = request.query_params.get('email')
        if email_param:
            from organization.services.crypto_service import compute_blind_index
            e_hash = compute_blind_index(self.tenant, email_param, 'email')
            qs = qs.filter(email_hash=e_hash)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ContactResponseSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ContactResponseSerializer(qs, many=True)
        return self.success_response(serializer.data)

    @rate_limit(capacity=60, fill_rate=1.0)
    @enforce_idempotency()
    def post(self, request):
        serializer = ContactCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                code='VALIDATION_ERROR',
                message='Invalid contact payload.',
                status_code=status.HTTP_400_BAD_REQUEST,
                details=serializer.errors,
            )

        validated = serializer.validated_data
        raw_phone = validated['whatsapp_number']

        from organization.services.crypto_service import compute_blind_index
        p_hash = compute_blind_index(self.tenant, raw_phone, 'phone')

        # Check existing contact
        existing = Customer.objects.filter(tenant=self.tenant, phone_hash=p_hash).first()
        if existing:
            return self.error_response(
                code='RESOURCE_CONFLICT',
                message=f"Contact with phone number '{raw_phone}' already exists.",
                status_code=status.HTTP_409_CONFLICT,
                details={'existing_id': existing.id},
            )

        with transaction.atomic():
            customer = Customer.objects.create(
                tenant=self.tenant,
                whatsapp_number=raw_phone,
                full_name=validated['full_name'],
                email=validated.get('email', ''),
                organization_name=validated.get('organization_name', ''),
                consent_status=validated.get('consent_status', 'ACTIVE'),
            )

            emit_outbox_event(
                tenant=self.tenant,
                event_type=EVENT_CONTACT_CREATED,
                payload={
                    'id': customer.id,
                    'full_name': validated['full_name'],
                    'whatsapp_number': raw_phone,
                    'email': validated.get('email', ''),
                    'consent_status': customer.consent_status,
                },
                correlation_id=request.request_id,
            )

        resp_serializer = ContactResponseSerializer(customer)
        return self.success_response(resp_serializer.data, status_code=status.HTTP_201_CREATED)


class ContactDetailView(BaseV1ApiView):
    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [RequireScope('contact:update')()]
        return [RequireScope('contact:read')()]

    def get_object(self, pk):
        customer = Customer.objects.filter(pk=pk, tenant=self.tenant).first()
        return customer

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request, pk):
        customer = self.get_object(pk)
        if not customer:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Contact not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = ContactResponseSerializer(customer)
        return self.success_response(serializer.data)

    @rate_limit(capacity=60, fill_rate=1.0)
    def patch(self, request, pk):
        customer = self.get_object(pk)
        if not customer:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Contact not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = ContactUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return self.error_response(
                code='VALIDATION_ERROR',
                message='Invalid update data.',
                status_code=status.HTTP_400_BAD_REQUEST,
                details=serializer.errors,
            )

        with transaction.atomic():
            for attr, val in serializer.validated_data.items():
                if attr == 'full_name':
                    customer.full_name = val
                elif attr == 'email':
                    customer.email = val
                elif attr == 'organization_name':
                    customer.organization_name = val
                elif attr == 'consent_status':
                    customer.consent_status = val

            customer.save()

            emit_outbox_event(
                tenant=self.tenant,
                event_type=EVENT_CONTACT_UPDATED,
                payload={
                    'id': customer.id,
                    'full_name': customer.plain_name,
                    'consent_status': customer.consent_status,
                },
                correlation_id=request.request_id,
            )

        resp_serializer = ContactResponseSerializer(customer)
        return self.success_response(resp_serializer.data)

