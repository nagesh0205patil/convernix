from django.urls import path

from .views import CampaignDetailView, CampaignListCreateView, CampaignStatsView

urlpatterns = [
    path('campaigns/', CampaignListCreateView.as_view(), name='campaign-list-create'),
    path('campaigns/stats/', CampaignStatsView.as_view(), name='campaign-stats'),
    path('campaigns/<int:pk>/', CampaignDetailView.as_view(), name='campaign-detail'),
]
