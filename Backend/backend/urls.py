from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from organization.views import PrivacyExportDownloadView


def service_index(request):
    return JsonResponse({
        'status': 'ok',
        'service': 'whatsapp-backend',
        'api': '/api/',
        'health': '/api/health/',
        'whatsapp_health': '/api/whatsapp/health/',
        'admin': '/admin/',
    })


def api_index(request):
    base_url = request.build_absolute_uri('/').rstrip('/')

    def endpoint(path, methods, authentication='JWT'):
        return {
            'url': f'{base_url}{path}',
            'path': path,
            'methods': methods,
            'authentication': authentication,
        }

    return JsonResponse({
        'name': 'WhatsApp Business Enquiry Router API',
        'status': 'ok',
        'authentication': 'Use Authorization: Bearer <access_token> for JWT-protected endpoints.',
        'endpoints': {
            'system': {
                'service_index': endpoint('/', ['GET'], 'Public'),
                'backend_health': endpoint('/api/health/', ['GET'], 'Public'),
                'django_admin': endpoint('/admin/', ['GET', 'POST'], 'Django staff session'),
            },
            'authentication': {
                'login': endpoint('/api/auth/login/', ['POST'], 'Public'),
                'refresh_token': endpoint('/api/auth/refresh/', ['POST'], 'Refresh token'),
                'register': endpoint('/api/auth/register/', ['POST'], 'Public when ENABLE_PUBLIC_REGISTRATION=True'),
                'current_user': endpoint('/api/auth/me/', ['GET']),
            },
            'users': {
                'team_directory': endpoint('/api/team-directory/', ['GET']),
                'team_members': endpoint('/api/team-members/', ['GET', 'POST'], 'Admin JWT'),
                'team_member_detail': endpoint('/api/team-members/{id}/', ['GET', 'PUT', 'PATCH', 'DELETE'], 'Admin JWT'),
            },
            'whatsapp': {
                'health': endpoint('/api/whatsapp/health/', ['GET'], 'Public'),
                'meta_webhook': endpoint('/api/whatsapp/webhook/', ['GET', 'POST'], 'Meta verification/signature'),
                'enquiries': endpoint('/api/whatsapp/enquiries/', ['GET']),
                'enquiry_export': endpoint('/api/whatsapp/enquiries/export/', ['GET']),
                'settings': endpoint('/api/whatsapp/settings/', ['GET', 'PATCH'], 'Admin JWT'),
            },
            'campaigns': {
                'campaigns': endpoint('/api/campaigns/', ['GET', 'POST']),
                'campaign_statistics': endpoint('/api/campaigns/stats/', ['GET']),
                'campaign_detail': endpoint('/api/campaigns/{id}/', ['GET', 'PUT', 'PATCH', 'DELETE']),
            },
            'analytics': {
                'metrics': endpoint('/api/analytics/', ['GET']),
                'create_metric': endpoint('/api/analytics/create/', ['POST']),
                'dashboard': endpoint('/api/analytics/dashboard/', ['GET']),
                'export_report': endpoint('/api/analytics/export/', ['GET']),
            },
        },
    })


urlpatterns = [
    path('', service_index, name='service-index'),
    path('admin/', admin.site.urls),
    path('api/', api_index, name='api-index'),
    path('api/', include('users.urls')),
    path('api/', include('campaigns.urls')),
    path('api/', include('analytics.urls')),
    path('api/whatsapp/', include('whatsapp.urls')),
    path('api/inbox/', include('inbox.urls')),
    path('api/admin/', include('organization.urls')),
    path('api/admin/integrations/', include(('integrations.urls', 'integrations-admin'))),
    path('api/', include('crm.urls')),
    path('api/v1/', include('crm.urls')),
    path('api/v1/', include('integrations.urls')),
    path('api/privacy/exports/<str:token>/download/', PrivacyExportDownloadView.as_view(), name='root-privacy-export-download'),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
