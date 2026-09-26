from django.urls import path

from .views import AnalyticsDashboardView, AnalyticsReportExportView, CampaignMetricCreateView, CampaignMetricListView

urlpatterns = [
    path('analytics/', CampaignMetricListView.as_view(), name='analytics-list'),
    path('analytics/create/', CampaignMetricCreateView.as_view(), name='analytics-create'),
    path('analytics/dashboard/', AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
    path('analytics/export/', AnalyticsReportExportView.as_view(), name='analytics-export'),
]
