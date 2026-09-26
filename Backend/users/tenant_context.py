import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional
from django.http import JsonResponse
from rest_framework.exceptions import PermissionDenied
from .models import Tenant, TenantMembership

logger = logging.getLogger(__name__)


@dataclass
class TenantContext:
    tenant: Optional[Tenant]
    user: Optional[Any]
    membership: Optional[TenantMembership] = None
    role: str = 'viewer'
    is_elevated_support: bool = False
    support_scopes: List[str] = field(default_factory=list)

    @property
    def is_operational(self) -> bool:
        return bool(self.tenant and self.tenant.is_operational)

    @property
    def is_suspended(self) -> bool:
        return bool(self.tenant and self.tenant.is_suspended)

    @property
    def is_deleted(self) -> bool:
        return bool(self.tenant and self.tenant.is_deleted)


def get_request_tenant(request) -> Optional[Tenant]:
    """Resolve the trusted Tenant for the current HTTP request from authenticated session."""
    req_tenant = getattr(request, 'tenant', None)
    if req_tenant:
        return req_tenant

    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return None

    # Check for platform staff support access elevation
    if user.is_superuser or user.is_staff:
        override_id = request.headers.get('X-Tenant-ID')
        if not override_id and hasattr(request, 'query_params'):
            override_id = request.query_params.get('tenant_id')
        elif not override_id and hasattr(request, 'GET'):
            override_id = request.GET.get('tenant_id')

        if override_id:
            try:
                target_tenant = Tenant.objects.filter(pk=int(override_id)).first()
                if target_tenant:
                    # Verify explicit support access session
                    from organization.services.support_access_service import SupportAccessService
                    session = SupportAccessService.verify_active_support_session(user, target_tenant)
                    if session:
                        setattr(request, '_support_access_session', session)
                        return target_tenant
                    elif user.is_superuser and getattr(request, '_allow_superuser_test_bypass', False):
                        return target_tenant
            except (ValueError, TypeError):
                pass

    # Standard tenant resolution: active user membership
    membership = TenantMembership.objects.filter(user=user, status='active').select_related('tenant').first()
    if membership and membership.tenant:
        return membership.tenant

    return getattr(user, 'tenant', None)


def resolve_tenant_context(request) -> TenantContext:
    """Constructs a trusted TenantContext object for the authenticated request."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return TenantContext(tenant=None, user=None)

    tenant = get_request_tenant(request)
    support_session = getattr(request, '_support_access_session', None)

    if support_session:
        return TenantContext(
            tenant=tenant,
            user=user,
            membership=None,
            role='support_operator',
            is_elevated_support=True,
            support_scopes=support_session.request.requested_scopes or ['read_only'],
        )

    membership = TenantMembership.objects.filter(user=user, tenant=tenant).first() if tenant else None
    role = membership.role if membership else getattr(user, 'role', 'viewer')

    return TenantContext(
        tenant=tenant,
        user=user,
        membership=membership,
        role=role,
        is_elevated_support=False,
    )


def require_request_tenant(request) -> Tenant:
    """Enforce that an authenticated request resolves to a valid, active tenant."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        raise PermissionDenied('Authentication credentials were not provided.')

    tenant = get_request_tenant(request)
    if not tenant:
        if user.is_superuser and not request.headers.get('X-Tenant-ID'):
            return None
        raise PermissionDenied('No active organization/tenant is associated with your account.')

    if tenant.is_suspended and not getattr(request, '_support_access_session', None):
        raise PermissionDenied('Your organization account has been suspended. Please contact platform support.')

    if tenant.is_deleted:
        raise PermissionDenied('Your organization account has been deleted.')

    return tenant


def filter_by_tenant(queryset, request, tenant_field='tenant'):
    """Scope a queryset to the active tenant, strictly preventing cross-tenant data leakage."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return queryset.none()

    tenant = get_request_tenant(request)
    support_session = getattr(request, '_support_access_session', None)

    if not user.is_superuser or support_session:
        if not tenant:
            return queryset.filter(**{f'{tenant_field}__isnull': True})
        if tenant.is_suspended and not support_session:
            raise PermissionDenied('Your organization account has been suspended. Please contact platform support.')

    if tenant:
        return queryset.filter(**{tenant_field: tenant})

    # Superuser without active tenant context or support session should NOT see all customer tenant data
    if user.is_superuser:
        if getattr(request, '_allow_superuser_test_bypass', False):
            return queryset
        # By default in multi-tenant mode, platform admin only sees platform-scoped or unassigned objects
        return queryset.filter(**{f'{tenant_field}__isnull': True})

    return queryset.none()


class TenantEnforcementMiddleware:
    """Middleware to reject requests for suspended or deleted tenants."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if (not user or not user.is_authenticated) and request.headers.get('Authorization', '').startswith('Bearer '):
            try:
                from rest_framework_simplejwt.authentication import JWTAuthentication
                auth_res = JWTAuthentication().authenticate(request)
                if auth_res:
                    user = auth_res[0]
                    request.user = user
            except Exception:
                pass

        if user and user.is_authenticated and not user.is_superuser:
            tenant = get_request_tenant(request)
            if tenant:
                if tenant.is_suspended:
                    exempt_paths = ('/api/auth/login/', '/api/auth/providers/', '/api/auth/me/')
                    if not any(request.path.startswith(p) for p in exempt_paths):
                        return JsonResponse({
                            'detail': 'Your organization account has been suspended. Please contact platform support.'
                        }, status=403)
                elif tenant.is_deleted:
                    return JsonResponse({
                        'detail': 'Your organization account has been deleted.'
                    }, status=403)

        return self.get_response(request)



