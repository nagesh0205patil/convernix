import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from django.db.models import Q
from django.utils.dateparse import parse_date

from crm.models import Lead, Customer, PipelineStage, Pipeline
from crm.serializers import (
    LeadListSerializer, LeadDetailSerializer, LeadCreateSerializer,
    LeadUpdateSerializer, LeadAssignSerializer, LeadStageTransitionSerializer,
    LeadTagsSerializer
)
from crm.services.lead_service import LeadService
from crm.services.tag_service import TagService
from crm.services.custom_field_service import CustomFieldService
from users.tenant_context import require_request_tenant
from users.permissions import has_tenant_permission

logger = logging.getLogger(__name__)


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class LeadListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def _scope_leads_by_rbac(self, queryset, user, tenant):
        if user.is_superuser:
            return queryset
        if has_tenant_permission(user, tenant, 'lead.read_all'):
            return queryset
        # Restrict to user's assigned leads or department leads or unassigned
        from whatsapp.models import DepartmentMember
        user_dept_ids = list(DepartmentMember.objects.filter(user=user, active=True).values_list('department_id', flat=True))
        return queryset.filter(
            Q(owner_user=user) |
            Q(department_id__in=user_dept_ids) |
            Q(owner_user__isnull=True)
        )

    def get(self, request):
        tenant = require_request_tenant(request)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'lead.read')):
            raise PermissionDenied("You do not have permission to view leads (requires 'lead.read').")

        queryset = Lead.objects.filter(tenant=tenant, deleted_at__isnull=True).select_related(
            'customer', 'pipeline', 'stage', 'department', 'owner_user'
        ).prefetch_related('lead_tags__tag')

        queryset = self._scope_leads_by_rbac(queryset, request.user, tenant)

        # Filters
        stage_id = request.query_params.get('stage_id') or request.query_params.get('stage')
        if stage_id:
            queryset = queryset.filter(stage_id=stage_id)

        pipeline_id = request.query_params.get('pipeline_id')
        if pipeline_id:
            queryset = queryset.filter(pipeline_id=pipeline_id)

        owner_id = request.query_params.get('owner_id') or request.query_params.get('owner')
        if owner_id:
            if owner_id == 'unassigned':
                queryset = queryset.filter(owner_user__isnull=True)
            else:
                queryset = queryset.filter(owner_user_id=owner_id)

        department_id = request.query_params.get('department_id') or request.query_params.get('department')
        if department_id:
            queryset = queryset.filter(department_id=department_id)

        tag_filter = request.query_params.get('tag')
        if tag_filter:
            queryset = queryset.filter(lead_tags__tag__name=tag_filter)

        source_filter = request.query_params.get('source')
        if source_filter:
            queryset = queryset.filter(source=source_filter.upper())

        priority_filter = request.query_params.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter.upper())

        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())

        # Date filters
        date_from = request.query_params.get('date_from')
        if date_from:
            d = parse_date(date_from)
            if d:
                queryset = queryset.filter(created_at__date__gte=d)

        date_to = request.query_params.get('date_to')
        if date_to:
            d = parse_date(date_to)
            if d:
                queryset = queryset.filter(created_at__date__lte=d)

        last_contact_from = request.query_params.get('last_contact_from')
        if last_contact_from:
            d = parse_date(last_contact_from)
            if d:
                queryset = queryset.filter(last_contacted_at__date__gte=d)

        # Search
        q = request.query_params.get('q', '').strip()
        if q:
            from organization.services.crypto_service import compute_blind_index, normalize_search_term
            phone_hash = compute_blind_index(tenant, normalize_search_term(q, 'phone'), 'phone')
            search_filter = Q(title__icontains=q) | Q(customer__display_name__icontains=q)
            if phone_hash:
                search_filter |= Q(customer__phone_lookup_hash=phone_hash)
            queryset = queryset.filter(search_filter)

        # Sorting
        sort_by = request.query_params.get('sort_by', '-created_at')
        allowed_sort = {
            'created_at', '-created_at', 'updated_at', '-updated_at',
            'last_contacted_at', '-last_contacted_at', 'estimated_value', '-estimated_value',
            'priority', '-priority', 'title', '-title'
        }
        if sort_by in allowed_sort:
            queryset = queryset.order_by(sort_by)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = LeadListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        tenant = require_request_tenant(request)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'lead.create')):
            raise PermissionDenied("You do not have permission to create leads (requires 'lead.create').")

        serializer = LeadCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        customer = Customer.objects.filter(tenant=tenant, customer_id=data['customer_id'], deleted_at__isnull=True).first()
        if not customer:
            raise NotFound({'detail': 'Customer not found.', 'code': 'CUSTOMER_NOT_FOUND'})

        lead = LeadService.create_lead(
            tenant=tenant,
            customer=customer,
            data=data,
            actor_user=request.user,
        )

        if 'tags' in data and data['tags']:
            TagService.sync_lead_tags(lead, data['tags'], actor_user=request.user)

        if 'custom_fields' in data and data['custom_fields']:
            CustomFieldService.save_custom_field_values(tenant, lead, data['custom_fields'], actor_user=request.user)

        out_serializer = LeadDetailSerializer(lead, context={'request': request})
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class LeadDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_lead(self, request, pk):
        tenant = require_request_tenant(request)
        lead = Lead.objects.filter(tenant=tenant, lead_id=pk, deleted_at__isnull=True).select_related(
            'customer', 'pipeline', 'stage', 'department', 'owner_user'
        ).first()
        if not lead:
            raise NotFound({'detail': 'Lead not found.', 'code': 'LEAD_NOT_FOUND'})
        return tenant, lead

    def get(self, request, pk):
        tenant, lead = self._get_lead(request, pk)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'lead.read')):
            raise PermissionDenied("You do not have permission to view this lead.")

        serializer = LeadDetailSerializer(lead, context={'request': request})
        return Response(serializer.data)

    def patch(self, request, pk):
        tenant, lead = self._get_lead(request, pk)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'lead.update')):
            raise PermissionDenied("You do not have permission to update this lead.")

        serializer = LeadUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        client_version = data.get('version')
        updated_lead = LeadService.update_lead(
            lead=lead,
            data=data,
            actor_user=request.user,
            client_version=client_version,
        )

        if 'custom_fields' in data and data['custom_fields']:
            CustomFieldService.save_custom_field_values(tenant, updated_lead, data['custom_fields'], actor_user=request.user)

        out_serializer = LeadDetailSerializer(updated_lead, context={'request': request})
        return Response(out_serializer.data)

    def delete(self, request, pk):
        tenant, lead = self._get_lead(request, pk)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'lead.delete')):
            raise PermissionDenied("You do not have permission to delete this lead.")

        lead.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeadAssignView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        tenant = require_request_tenant(request)
        is_reassign = 'owner_user_id' in request.data
        required_perm = 'lead.reassign' if is_reassign else 'lead.assign'
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'lead.assign') or has_tenant_permission(request.user, tenant, 'lead.reassign')):
            raise PermissionDenied("Permission denied to assign or reassign leads.")

        lead = Lead.objects.filter(tenant=tenant, lead_id=pk, deleted_at__isnull=True).first()
        if not lead:
            raise NotFound({'detail': 'Lead not found.', 'code': 'LEAD_NOT_FOUND'})

        serializer = LeadAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        owner_user = None
        owner_id = data.get('owner_user_id')
        if owner_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            owner_user = User.objects.filter(pk=owner_id).first()
            if not owner_user:
                raise ValidationError({'detail': 'Specified owner user not found.', 'code': 'OWNER_NOT_AVAILABLE'})

        department = None
        dept_id = data.get('department_id')
        if dept_id:
            from whatsapp.models import Department
            department = Department.objects.filter(tenant=tenant, pk=dept_id).first()

        updated_lead = LeadService.assign_lead(
            lead=lead,
            owner_user=owner_user,
            department=department,
            assigned_by=request.user,
            method=data.get('method', 'MANUAL'),
            reason=data.get('reason', ''),
            client_version=data.get('version'),
        )

        out_serializer = LeadDetailSerializer(updated_lead, context={'request': request})
        return Response(out_serializer.data)


class LeadStageTransitionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        tenant = require_request_tenant(request)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'lead.change_stage')):
            raise PermissionDenied("Permission denied to change lead stage (requires 'lead.change_stage').")

        lead = Lead.objects.filter(tenant=tenant, lead_id=pk, deleted_at__isnull=True).first()
        if not lead:
            raise NotFound({'detail': 'Lead not found.', 'code': 'LEAD_NOT_FOUND'})

        serializer = LeadStageTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_stage = PipelineStage.objects.filter(
            tenant=tenant,
            stage_id=data['stage_id'],
            is_active=True,
        ).first()

        if not target_stage:
            raise NotFound({'detail': 'Target pipeline stage not found.', 'code': 'INVALID_STAGE_TRANSITION'})

        updated_lead = LeadService.transition_lead_stage(
            lead=lead,
            target_stage=target_stage,
            actor_user=request.user,
            reason=data.get('reason', ''),
            client_version=data.get('version'),
        )

        out_serializer = LeadDetailSerializer(updated_lead, context={'request': request})
        return Response(out_serializer.data)


class LeadTagsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        tenant = require_request_tenant(request)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'lead.update') or has_tenant_permission(request.user, tenant, 'tag.manage')):
            raise PermissionDenied("Permission denied to update lead tags.")

        lead = Lead.objects.filter(tenant=tenant, lead_id=pk, deleted_at__isnull=True).first()
        if not lead:
            raise NotFound({'detail': 'Lead not found.', 'code': 'LEAD_NOT_FOUND'})

        serializer = LeadTagsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        tags = TagService.sync_lead_tags(lead, data['tags'], actor_user=request.user)
        return Response({'tags': [{'id': str(t.tag_id), 'name': t.name, 'color': t.color} for t in tags]})
