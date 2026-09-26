from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomTokenObtainPairView,
    HealthView,
    MeView,
    RegisterView,
    TeamDirectoryView,
    TeamMemberDetailView,
    TeamMemberListCreateView,
    IAMInvitationView,
    AcceptInvitationView,
    AuthProviderView,
    TenantCurrentView,
    PlatformTenantListView,
    PlatformTenantDetailView,
    RegisterTenantView,
)

urlpatterns = [
    path('health/', HealthView.as_view(), name='health'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/register-tenant/', RegisterTenantView.as_view(), name='register-tenant'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/providers/', AuthProviderView.as_view(), name='auth-providers'),
    path('auth/invitations/accept/', AcceptInvitationView.as_view(), name='accept-invitation'),
    path('iam/invitations/', IAMInvitationView.as_view(), name='iam-invitation'),
    path('team-directory/', TeamDirectoryView.as_view(), name='team-directory'),
    path('team-members/', TeamMemberListCreateView.as_view(), name='team-members-list-create'),
    path('team-members/<int:pk>/', TeamMemberDetailView.as_view(), name='team-members-detail'),
    path('tenant/me/', TenantCurrentView.as_view(), name='tenant-current'),
    path('platform/tenants/', PlatformTenantListView.as_view(), name='platform-tenants-list'),
    path('platform/tenants/<int:pk>/', PlatformTenantDetailView.as_view(), name='platform-tenants-detail'),
]
