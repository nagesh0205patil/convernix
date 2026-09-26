from rest_framework import generics, status
from rest_framework.response import Response
from users.permissions import PlatformReadWritePermission
from users.tenant_context import filter_by_tenant, get_request_tenant
from whatsapp.workspace import selected_business_number, workspace_is_explicit

from .models import Campaign
from .serializers import CampaignSerializer


class CampaignListCreateView(generics.ListCreateAPIView):
    serializer_class = CampaignSerializer
    permission_classes = [PlatformReadWritePermission]

    def get_queryset(self):
        queryset = filter_by_tenant(Campaign.objects.all(), self.request)
        return queryset.filter(business_number=selected_business_number(self.request)) if workspace_is_explicit(self.request) else queryset

    def perform_create(self, serializer):
        tenant = get_request_tenant(self.request)
        if tenant and not self.request.user.is_superuser:
            from django.utils import timezone
            from rest_framework.exceptions import ValidationError
            now = timezone.now()
            month_count = Campaign.objects.filter(
                tenant=tenant,
                created_at__year=now.year,
                created_at__month=now.month,
            ).count()
            if month_count >= tenant.max_campaigns_monthly:
                raise ValidationError({
                    'detail': f'Your {tenant.get_tier_display()} plan allows up to {tenant.max_campaigns_monthly} campaign(s) per month. Please upgrade your plan to create more.'
                })
        serializer.save(
            tenant=tenant,
            created_by=self.request.user,
            business_number=selected_business_number(self.request),
        )


class CampaignDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CampaignSerializer
    permission_classes = [PlatformReadWritePermission]

    def get_queryset(self):
        queryset = filter_by_tenant(Campaign.objects.all(), self.request)
        return queryset.filter(business_number=selected_business_number(self.request)) if workspace_is_explicit(self.request) else queryset


class CampaignStatsView(generics.GenericAPIView):
    permission_classes = [PlatformReadWritePermission]

    def get(self, request, *args, **kwargs):
        campaigns = filter_by_tenant(Campaign.objects.all(), request)
        if workspace_is_explicit(request):
            campaigns = campaigns.filter(business_number=selected_business_number(request))
        total_sent = sum(item.sent_count for item in campaigns)
        total_delivered = sum(item.delivered_count for item in campaigns)
        total_opened = sum(item.opened_count for item in campaigns)
        total_clicked = sum(item.clicked_count for item in campaigns)

        return Response(
            {
                'total_campaigns': campaigns.count(),
                'total_sent': total_sent,
                'total_delivered': total_delivered,
                'total_opened': total_opened,
                'total_clicked': total_clicked,
            },
            status=status.HTTP_200_OK,
        )
