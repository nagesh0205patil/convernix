from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from .base import BaseV1ApiView
from integrations.scopes import RequireScope
from integrations.idempotency import enforce_idempotency
from integrations.rate_limiter import rate_limit
from integrations.outbox import emit_outbox_event
from integrations.events import EVENT_LEAD_CREATED, EVENT_LEAD_UPDATED
from integrations.serializers import (
    LeadResponseSerializer,
    LeadCreateSerializer,
    LeadUpdateSerializer,
)
from whatsapp.models import Lead, BusinessNumber, Customer, Enquiry, Department


class LeadListCreateView(BaseV1ApiView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [RequireScope('lead:create')()]
        return [RequireScope('lead:read')()]

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request):
        qs = Lead.objects.filter(business_number__tenant=self.tenant).select_related('business_number', 'enquiry')

        status_param = request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        team_param = request.query_params.get('team')
        if team_param:
            qs = qs.filter(team_name=team_param)

        search_param = request.query_params.get('search')
        if search_param:
            # Blind index lookup for phone / email
            from organization.services.crypto_service import compute_blind_index
            p_hash = compute_blind_index(self.tenant, search_param, 'phone')
            e_hash = compute_blind_index(self.tenant, search_param, 'email')
            qs = qs.filter(phone_hash=p_hash) if p_hash else qs

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = LeadResponseSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = LeadResponseSerializer(qs, many=True)
        return self.success_response(serializer.data)

    @rate_limit(capacity=60, fill_rate=1.0)
    @enforce_idempotency()
    def post(self, request):
        serializer = LeadCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                code='VALIDATION_ERROR',
                message='Invalid lead payload.',
                status_code=status.HTTP_400_BAD_REQUEST,
                details=serializer.errors,
            )

        validated = serializer.validated_data
        b_num_str = validated.get('business_number')

        # Find or use first active business number for tenant
        if b_num_str:
            b_num = BusinessNumber.objects.filter(tenant=self.tenant, number=b_num_str).first()
            if not b_num:
                return self.error_response(
                    code='RESOURCE_NOT_FOUND',
                    message=f"Business number '{b_num_str}' not found in tenant.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
        else:
            b_num = BusinessNumber.objects.filter(tenant=self.tenant, is_active=True).first()
            if not b_num:
                b_num = BusinessNumber.objects.create(
                    tenant=self.tenant,
                    number='+919876543210',
                    label='Primary WhatsApp',
                )

        # Department
        dept_name = validated.get('team_name', 'Support')
        dept = Department.objects.filter(tenant=self.tenant, name__iexact=dept_name).first()
        if not dept:
            dept = Department.objects.filter(tenant=self.tenant).first()
            if not dept:
                dept = Department.objects.create(tenant=self.tenant, name='Support', slug='support')

        with transaction.atomic():
            # Get or create customer
            from organization.services.crypto_service import compute_blind_index
            raw_phone = validated['phone_number']
            p_hash = compute_blind_index(self.tenant, raw_phone, 'phone')
            customer = Customer.objects.filter(tenant=self.tenant, phone_hash=p_hash).first()
            if not customer:
                customer = Customer.objects.create(
                    tenant=self.tenant,
                    whatsapp_number=raw_phone,
                    full_name=validated['customer_name'],
                    email=validated.get('customer_email', ''),
                )

            # Create enquiry
            enquiry = Enquiry.objects.create(
                tenant=self.tenant,
                customer=customer,
                department=dept,
                message=validated['message'],
                status='new',
                source='api',
            )

            # Create lead projection
            lead = Lead.objects.create(
                business_number=b_num,
                enquiry=enquiry,
                customer_name=validated['customer_name'],
                phone_number=raw_phone,
                customer_email=validated.get('customer_email', ''),
                message=validated['message'],
                team_name=dept.name,
                status='new',
                source='api',
            )

            # Emit transactional outbox event
            emit_outbox_event(
                tenant=self.tenant,
                event_type=EVENT_LEAD_CREATED,
                payload={
                    'id': lead.id,
                    'customer_name': validated['customer_name'],
                    'phone_number': raw_phone,
                    'email': validated.get('customer_email', ''),
                    'message': validated['message'],
                    'team': dept.name,
                    'status': 'new',
                },
                correlation_id=request.request_id,
            )

        resp_serializer = LeadResponseSerializer(lead)
        return self.success_response(resp_serializer.data, status_code=status.HTTP_201_CREATED)


class LeadDetailView(BaseV1ApiView):
    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [RequireScope('lead:update')()]
        return [RequireScope('lead:read')()]

    def get_object(self, pk):
        lead = Lead.objects.filter(pk=pk, business_number__tenant=self.tenant).select_related('business_number', 'enquiry').first()
        if not lead:
            return None
        return lead

    @rate_limit(capacity=120, fill_rate=2.0)
    def get(self, request, pk):
        lead = self.get_object(pk)
        if not lead:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Lead not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = LeadResponseSerializer(lead)
        return self.success_response(serializer.data)

    @rate_limit(capacity=60, fill_rate=1.0)
    def patch(self, request, pk):
        lead = self.get_object(pk)
        if not lead:
            return self.error_response(
                code='RESOURCE_NOT_FOUND',
                message='Lead not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = LeadUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return self.error_response(
                code='VALIDATION_ERROR',
                message='Invalid update data.',
                status_code=status.HTTP_400_BAD_REQUEST,
                details=serializer.errors,
            )

        with transaction.atomic():
            for attr, val in serializer.validated_data.items():
                if attr == 'status':
                    lead.status = val
                    if lead.enquiry:
                        lead.enquiry.status = 'closed' if val == 'resolved' else val
                        lead.enquiry.save(update_fields=['status', 'updated_at'])
                elif attr == 'team_name':
                    lead.team_name = val

            lead.save()

            emit_outbox_event(
                tenant=self.tenant,
                event_type=EVENT_LEAD_UPDATED,
                payload={
                    'id': lead.id,
                    'status': lead.status,
                    'team_name': lead.team_name,
                },
                correlation_id=request.request_id,
            )

        resp_serializer = LeadResponseSerializer(lead)
        return self.success_response(resp_serializer.data)

