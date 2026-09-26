import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from crm.models import Customer, Lead
from crm.serializers import CustomerSerializer, LeadListSerializer
from users.tenant_context import require_request_tenant
from users.permissions import has_tenant_permission
from organization.services.crypto_service import compute_blind_index, normalize_search_term

logger = logging.getLogger(__name__)


class CrmSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = require_request_tenant(request)
        q = request.query_params.get('q', '').strip()
        if not q:
            return Response({'customers': [], 'leads': []})

        phone_hash = compute_blind_index(tenant, normalize_search_term(q, 'phone'), 'phone')
        email_hash = compute_blind_index(tenant, normalize_search_term(q, 'email'), 'email')

        # 1. Search Customers
        can_read_customers = request.user.is_superuser or has_tenant_permission(request.user, tenant, 'customer.read')
        matched_customers = []
        if can_read_customers:
            cust_filter = Q(display_name__icontains=q)
            if phone_hash:
                cust_filter |= Q(phone_lookup_hash=phone_hash)
            if email_hash:
                cust_filter |= Q(email_lookup_hash=email_hash)

            customers_qs = Customer.objects.filter(
                tenant=tenant,
                deleted_at__isnull=True,
            ).filter(cust_filter).prefetch_related('customer_tags__tag')[:15]
            cust_serializer = CustomerSerializer(customers_qs, many=True, context={'request': request})
            matched_customers = cust_serializer.data

        # 2. Search Leads
        can_read_leads = request.user.is_superuser or has_tenant_permission(request.user, tenant, 'lead.read')
        matched_leads = []
        if can_read_leads:
            lead_filter = Q(title__icontains=q) | Q(customer__display_name__icontains=q) | Q(stage__name__icontains=q) | Q(lead_tags__tag__name__icontains=q)
            if phone_hash:
                lead_filter |= Q(customer__phone_lookup_hash=phone_hash)
            if email_hash:
                lead_filter |= Q(customer__email_lookup_hash=email_hash)

            leads_qs = Lead.objects.filter(
                tenant=tenant,
                deleted_at__isnull=True,
            ).filter(lead_filter).select_related(
                'customer', 'pipeline', 'stage', 'department', 'owner_user'
            ).prefetch_related('lead_tags__tag').distinct()[:15]

            # Record-level filter if not superuser or lead.read_all
            if not request.user.is_superuser and not has_tenant_permission(request.user, tenant, 'lead.read_all'):
                from whatsapp.models import DepartmentMember
                user_dept_ids = list(DepartmentMember.objects.filter(user=request.user, active=True).values_list('department_id', flat=True))
                leads_qs = leads_qs.filter(
                    Q(owner_user=request.user) |
                    Q(department_id__in=user_dept_ids) |
                    Q(owner_user__isnull=True)
                )

            lead_serializer = LeadListSerializer(leads_qs, many=True, context={'request': request})
            matched_leads = lead_serializer.data

        return Response({
            'query': q,
            'customers': matched_customers,
            'leads': matched_leads,
        })
