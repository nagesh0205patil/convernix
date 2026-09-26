import csv
from calendar import monthrange
from datetime import date

from django.db.models import Count, Sum
from django.db.models.functions import TruncDay, TruncMonth
from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from campaigns.models import Campaign
from whatsapp.models import Enquiry
from whatsapp.workspace import selected_business_number, workspace_is_explicit
from users.permissions import PlatformReadWritePermission
from users.tenant_context import get_request_tenant
from .models import CampaignMetric
from .serializers import CampaignMetricSerializer


class CampaignMetricListView(generics.ListAPIView):
    serializer_class = CampaignMetricSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant = get_request_tenant(self.request)
        queryset = CampaignMetric.objects.all()
        if not self.request.user.is_superuser:
            if tenant:
                if getattr(tenant, 'status', None) == 'suspended':
                    raise PermissionDenied('Your organization account has been suspended.')
                queryset = queryset.filter(campaign__tenant=tenant)
            else:
                queryset = queryset.filter(created_by=self.request.user)
        elif tenant:
            queryset = queryset.filter(campaign__tenant=tenant)

        if workspace_is_explicit(self.request):
            queryset = queryset.filter(campaign__business_number=selected_business_number(self.request))
        return queryset


class CampaignMetricCreateView(generics.CreateAPIView):
    serializer_class = CampaignMetricSerializer
    permission_classes = [PlatformReadWritePermission]

    def perform_create(self, serializer):
        tenant = get_request_tenant(self.request)
        campaign = serializer.validated_data['campaign']
        if not self.request.user.is_superuser and tenant:
            if getattr(tenant, 'status', None) == 'suspended':
                raise PermissionDenied('Your organization account has been suspended.')
            if campaign.tenant_id != tenant.pk:
                raise PermissionDenied('You cannot create metrics for another organization’s campaign.')
        if workspace_is_explicit(self.request):
            selected = selected_business_number(self.request)
            if selected is None or campaign.business_number_id != selected.pk:
                raise PermissionDenied('The campaign is outside the selected workspace.')
        serializer.save(created_by=self.request.user)


def report_period(request):
    today = date.today()
    try:
        year = int(request.query_params.get('year', today.year))
        month_value = request.query_params.get('month', '')
        month = int(month_value) if month_value else None
        if year < 2000 or year > today.year or (month and not 1 <= month <= 12):
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError('Provide a valid year and optional month.')
    start = date(year, month or 1, 1)
    end = date(year, month, monthrange(year, month)[1]) if month else date(year, 12, 31)
    return year, month, start, min(end, today)


class AnalyticsDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            year, month, start, end = report_period(request)
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        business_number = selected_business_number(request)
        enquiries = Enquiry.objects.filter(created_at__date__range=(start, end))
        campaigns = Campaign.objects.filter(created_at__date__range=(start, end))
        tenant = get_request_tenant(request)
        if not request.user.is_superuser:
            if tenant:
                if getattr(tenant, 'status', None) == 'suspended':
                    raise PermissionDenied('Your organization account has been suspended.')
                enquiries = enquiries.filter(tenant=tenant)
                campaigns = campaigns.filter(tenant=tenant)
            else:
                enquiries = enquiries.filter(tenant__isnull=True)
                campaigns = campaigns.filter(created_by=request.user)
        elif tenant:
            enquiries = enquiries.filter(tenant=tenant)
            campaigns = campaigns.filter(tenant=tenant)

        if workspace_is_explicit(request):
            enquiries = enquiries.filter(legacy_lead__business_number=business_number)
            campaigns = campaigns.filter(business_number=business_number)
        bucket = TruncDay('created_at') if month else TruncMonth('created_at')
        enquiry_trend = enquiries.annotate(period=bucket).values('period').annotate(count=Count('id')).order_by('period')
        campaign_trend = campaigns.annotate(period=bucket).values('period').annotate(count=Count('id')).order_by('period')
        campaign_totals = campaigns.aggregate(
            sent=Sum('sent_count'), delivered=Sum('delivered_count'),
            opened=Sum('opened_count'), clicked=Sum('clicked_count'),
        )
        return Response({
            'period': {'year': year, 'month': month, 'start': start, 'end': end},
            'totals': {
                'enquiries': enquiries.count(), 'campaigns': campaigns.count(),
                **{key: value or 0 for key, value in campaign_totals.items()},
            },
            'trend': {
                'enquiries': [{'label': row['period'].date(), 'value': row['count']} for row in enquiry_trend],
                'campaigns': [{'label': row['period'].date(), 'value': row['count']} for row in campaign_trend],
            },
            'enquiry_statuses': list(enquiries.values('status').annotate(value=Count('id')).order_by('-value')),
            'enquiry_teams': [
                {'label': row['department__name'], 'value': row['value']}
                for row in enquiries.values('department__name').annotate(value=Count('id')).order_by('-value')
            ],
            'campaign_statuses': list(campaigns.values('status').annotate(value=Count('id')).order_by('-value')),
        })


class AnalyticsReportExportView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def safe(value):
        text = str(value or '')
        return f"'{text}" if text.startswith(('=', '+', '-', '@')) else text

    def get(self, request):
        try:
            year, month, start, end = report_period(request)
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        report_type = request.query_params.get('type', 'enquiries')
        business_number = selected_business_number(request)
        if report_type not in ('enquiries', 'campaigns'):
            return Response({'detail': 'Report type must be enquiries or campaigns.'}, status=status.HTTP_400_BAD_REQUEST)
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        suffix = f'{year}-{month:02d}' if month else str(year)
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{suffix}.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        tenant = get_request_tenant(request)
        if report_type == 'enquiries':
            writer.writerow(['Reference', 'Customer', 'Phone', 'Email', 'Organization', 'Team', 'Status', 'Message', 'Received At'])
            records = Enquiry.objects.filter(created_at__date__range=(start, end))
            if not request.user.is_superuser:
                if tenant:
                    if getattr(tenant, 'status', None) == 'suspended':
                        raise PermissionDenied('Your organization account has been suspended.')
                    records = records.filter(tenant=tenant)
                else:
                    records = records.filter(tenant__isnull=True)
            elif tenant:
                records = records.filter(tenant=tenant)
            if workspace_is_explicit(request):
                records = records.filter(legacy_lead__business_number=business_number)
            records = records.select_related('customer', 'department')
            for item in records:
                writer.writerow([self.safe(item.reference), self.safe(item.customer.full_name), self.safe(item.customer.whatsapp_number), self.safe(item.customer.email), self.safe(item.customer.organization_name), self.safe(item.department.name), item.get_status_display(), self.safe(item.message), item.created_at.isoformat()])
        else:
            writer.writerow(['Campaign', 'Status', 'Audience', 'Message', 'Scheduled At', 'Sent', 'Delivered', 'Opened', 'Clicked', 'Created At'])
            records = Campaign.objects.filter(created_at__date__range=(start, end))
            if not request.user.is_superuser:
                if tenant:
                    if getattr(tenant, 'status', None) == 'suspended':
                        raise PermissionDenied('Your organization account has been suspended.')
                    records = records.filter(tenant=tenant)
                else:
                    records = records.filter(created_by=request.user)
            elif tenant:
                records = records.filter(tenant=tenant)
            if workspace_is_explicit(request):
                records = records.filter(business_number=business_number)
            for item in records:
                writer.writerow([
                    self.safe(item.name),
                    item.get_status_display(),
                    self.safe(item.target_audience),
                    self.safe(item.message),
                    item.scheduled_at.isoformat() if item.scheduled_at else '',
                    item.sent_count,
                    item.delivered_count,
                    item.opened_count,
                    item.clicked_count,
                    item.created_at.isoformat(),
                ])
        return response

