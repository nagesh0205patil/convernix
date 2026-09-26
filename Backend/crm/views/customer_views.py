import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from django.db.models import Q

from crm.models import Customer, Activity, Note
from crm.serializers import (
    CustomerSerializer, CustomerCreateUpdateSerializer, CustomerMergeSerializer,
    ActivitySerializer, NoteSerializer, NoteCreateSerializer
)
from crm.services.customer_service import CustomerService
from crm.services.customer_360_service import Customer360Service
from crm.services.custom_field_service import CustomFieldService
from crm.services.tag_service import TagService
from users.tenant_context import require_request_tenant
from users.permissions import has_tenant_permission

logger = logging.getLogger(__name__)


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CustomerListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = require_request_tenant(request)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'customer.read')):
            raise PermissionDenied("You do not have permission to view customers (requires 'customer.read').")

        queryset = Customer.objects.filter(tenant=tenant, deleted_at__isnull=True).prefetch_related('customer_tags__tag')

        # Filters
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())

        source_filter = request.query_params.get('source')
        if source_filter:
            queryset = queryset.filter(source=source_filter.upper())

        q = request.query_params.get('q', '').strip()
        if q:
            # Check display_name or HMAC blind index
            from organization.services.crypto_service import compute_blind_index, normalize_search_term
            phone_hash = compute_blind_index(tenant, normalize_search_term(q, 'phone'), 'phone')
            email_hash = compute_blind_index(tenant, normalize_search_term(q, 'email'), 'email')
            search_q = Q(display_name__icontains=q)
            if phone_hash:
                search_q |= Q(phone_lookup_hash=phone_hash)
            if email_hash:
                search_q |= Q(email_lookup_hash=email_hash)
            queryset = queryset.filter(search_q)

        # Tag filter
        tag_filter = request.query_params.get('tag')
        if tag_filter:
            queryset = queryset.filter(customer_tags__tag__name=tag_filter)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = CustomerSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        tenant = require_request_tenant(request)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'customer.create')):
            raise PermissionDenied("You do not have permission to create customers (requires 'customer.create').")

        serializer = CustomerCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        customer = CustomerService.create_customer(tenant, data, actor_user=request.user)

        # Handle tags
        if 'tags' in data and data['tags']:
            TagService.sync_customer_tags(customer, data['tags'], actor_user=request.user)

        # Handle custom fields
        if 'custom_fields' in data and data['custom_fields']:
            CustomFieldService.save_custom_field_values(tenant, customer, data['custom_fields'], actor_user=request.user)

        out_serializer = CustomerSerializer(customer, context={'request': request})
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class CustomerDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_customer(self, request, pk):
        tenant = require_request_tenant(request)
        customer = Customer.objects.filter(tenant=tenant, customer_id=pk, deleted_at__isnull=True).first()
        if not customer:
            raise NotFound({'detail': 'Customer not found.', 'code': 'CUSTOMER_NOT_FOUND'})
        return tenant, customer

    def get(self, request, pk):
        tenant, customer = self._get_customer(request, pk)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'customer.read')):
            raise PermissionDenied("You do not have permission to view customer details (requires 'customer.read').")

        serializer = CustomerSerializer(customer, context={'request': request})
        return Response(serializer.data)

    def patch(self, request, pk):
        tenant, customer = self._get_customer(request, pk)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'customer.update')):
            raise PermissionDenied("You do not have permission to update customers (requires 'customer.update').")

        serializer = CustomerCreateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        updated_customer = CustomerService.update_customer(customer, data, actor_user=request.user)

        if 'tags' in data:
            TagService.sync_customer_tags(updated_customer, data['tags'], actor_user=request.user)

        if 'custom_fields' in data:
            CustomFieldService.save_custom_field_values(tenant, updated_customer, data['custom_fields'], actor_user=request.user)

        out_serializer = CustomerSerializer(updated_customer, context={'request': request})
        return Response(out_serializer.data)

    def delete(self, request, pk):
        tenant, customer = self._get_customer(request, pk)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'customer.update')):
            raise PermissionDenied("Permission denied to delete customer.")

        customer.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class Customer360View(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        tenant = require_request_tenant(request)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'customer.read')):
            raise PermissionDenied("You do not have permission to view Customer 360.")

        customer = Customer.objects.filter(tenant=tenant, customer_id=pk, deleted_at__isnull=True).first()
        if not customer:
            raise NotFound({'detail': 'Customer not found.', 'code': 'CUSTOMER_NOT_FOUND'})

        data = Customer360Service.get_customer_360(tenant, customer, request.user)
        return Response(data)


class CustomerConversationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        tenant = require_request_tenant(request)
        customer = Customer.objects.filter(tenant=tenant, customer_id=pk, deleted_at__isnull=True).first()
        if not customer:
            raise NotFound({'detail': 'Customer not found.', 'code': 'CUSTOMER_NOT_FOUND'})

        conversations = []
        if customer.legacy_whatsapp_customer:
            from inbox.models import Conversation
            inbox_convs = Conversation.objects.filter(
                tenant=tenant,
                contact=customer.legacy_whatsapp_customer,
            ).select_related('department', 'assigned_user').order_by('-last_message_at')

            for conv in inbox_convs:
                conversations.append({
                    'conversation_id': conv.id,
                    'status': conv.status,
                    'priority': conv.priority,
                    'department': conv.department.name if conv.department else None,
                    'assigned_user': conv.assigned_user.email if conv.assigned_user else None,
                    'last_message_preview': conv.plain_last_message_preview,
                    'last_message_at': conv.last_message_at.isoformat() if conv.last_message_at else None,
                    'created_at': conv.created_at.isoformat(),
                })

        return Response(conversations)


class CustomerActivitiesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        tenant = require_request_tenant(request)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'activity.read')):
            raise PermissionDenied("You do not have permission to read activities.")

        customer = Customer.objects.filter(tenant=tenant, customer_id=pk, deleted_at__isnull=True).first()
        if not customer:
            raise NotFound({'detail': 'Customer not found.', 'code': 'CUSTOMER_NOT_FOUND'})

        activities = Activity.objects.filter(tenant=tenant, customer=customer).order_by('-created_at')[:100]
        serializer = ActivitySerializer(activities, many=True)
        return Response(serializer.data)


class CustomerNotesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        tenant = require_request_tenant(request)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'note.read')):
            raise PermissionDenied("You do not have permission to read notes.")

        customer = Customer.objects.filter(tenant=tenant, customer_id=pk, deleted_at__isnull=True).first()
        if not customer:
            raise NotFound({'detail': 'Customer not found.', 'code': 'CUSTOMER_NOT_FOUND'})

        notes = Note.objects.filter(tenant=tenant, customer=customer).select_related('author_user').order_by('-is_pinned', '-created_at')
        serializer = NoteSerializer(notes, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        tenant = require_request_tenant(request)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'note.create')):
            raise PermissionDenied("You do not have permission to create notes.")

        customer = Customer.objects.filter(tenant=tenant, customer_id=pk, deleted_at__isnull=True).first()
        if not customer:
            raise NotFound({'detail': 'Customer not found.', 'code': 'CUSTOMER_NOT_FOUND'})

        serializer = NoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        lead = None
        if data.get('lead_id'):
            from crm.models import Lead
            lead = Lead.objects.filter(tenant=tenant, lead_id=data['lead_id']).first()

        note = Note(
            tenant=tenant,
            customer=customer,
            lead=lead,
            author_user=request.user,
            is_pinned=data.get('is_pinned', False),
        )
        note.set_content(data['content'])
        note.save()

        # Log Activity
        from crm.services.activity_service import ActivityService
        ActivityService.log_activity(
            tenant=tenant,
            customer=customer,
            lead=lead,
            activity_type='NOTE_ADDED',
            title='Note Added',
            description=data['content'][:150],
            actor_user=request.user,
        )

        out_serializer = NoteSerializer(note)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class CustomerMergeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tenant = require_request_tenant(request)
        if not (request.user.is_superuser or has_tenant_permission(request.user, tenant, 'customer.merge')):
            raise PermissionDenied("You do not have permission to merge customers (requires 'customer.merge').")

        serializer = CustomerMergeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        primary_customer = Customer.objects.filter(tenant=tenant, customer_id=data['primary_customer_id'], deleted_at__isnull=True).first()
        secondary_customer = Customer.objects.filter(tenant=tenant, customer_id=data['secondary_customer_id'], deleted_at__isnull=True).first()

        if not primary_customer or not secondary_customer:
            raise NotFound({'detail': 'One or both customers to merge could not be found.', 'code': 'CUSTOMER_NOT_FOUND'})

        merged = CustomerService.merge_customers(
            tenant=tenant,
            primary_customer=primary_customer,
            secondary_customer=secondary_customer,
            merged_by=request.user,
            reason=data.get('reason', ''),
        )

        out_serializer = CustomerSerializer(merged, context={'request': request})
        return Response({
            'status': 'merged',
            'primary_customer': out_serializer.data,
        })
