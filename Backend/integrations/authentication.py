import hashlib
import hmac
import ipaddress
import logging
import uuid
from typing import Optional, Tuple
from django.utils import timezone
from rest_framework import authentication, exceptions
from .models import ApiKey

logger = logging.getLogger(__name__)


class IntegrationPrincipal:
    """Represents a tenant-scoped service account or API key identity."""

    def __init__(self, api_key: ApiKey):
        self.api_key = api_key
        self.service_account = api_key.service_account
        self.tenant = api_key.tenant
        self.id = str(self.service_account.id) if self.service_account else str(api_key.id)
        self.pk = self.id
        self.is_authenticated = True
        self.is_anonymous = False
        self.is_staff = False
        self.is_superuser = False
        self.is_active = True
        self.is_service_account = True
        self.role = 'service_account'
        sa_name = self.service_account.name if self.service_account else api_key.name
        slug = getattr(self.tenant, 'slug', 'tenant')
        self.email = f"sa-{api_key.key_prefix}@{slug}.convernix.internal"
        self.username = self.email

    def __str__(self):
        return f'ServiceAccount({self.id}, tenant={getattr(self.tenant, "slug", self.tenant_id)})'

    @property
    def tenant_id(self):
        return self.tenant.id if self.tenant else None


class IntegrationAuthContext:
    """Trusted request context for API key integrations."""

    def __init__(self, api_key: ApiKey, request_id: str):
        self.api_key = api_key
        self.service_account = api_key.service_account
        self.tenant = api_key.tenant
        self.tenant_id = api_key.tenant.id if api_key.tenant else None
        self.principal_id = str(api_key.service_account.id) if api_key.service_account else str(api_key.id)
        self.principal_type = 'service_account' if api_key.service_account else 'api_key'
        self.scopes = list(api_key.scopes or [])
        self.request_id = request_id

    def has_scope(self, required_scope: str) -> bool:
        if '*' in self.scopes or 'admin' in self.scopes:
            return True
        if required_scope in self.scopes:
            return True
        # Prefix matching e.g. "lead:*" covers "lead:read" and "lead:create"
        parts = required_scope.split(':')
        if len(parts) == 2 and f"{parts[0]}:*" in self.scopes:
            return True
        return False

    def has_any_scope(self, scopes: list) -> bool:
        return any(self.has_scope(s) for s in scopes)


def get_client_ip(request) -> str:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


def is_ip_allowed(client_ip: str, allowlist: list) -> bool:
    if not allowlist:
        return True
    try:
        client_addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False

    for item in allowlist:
        item = str(item).strip()
        if not item:
            continue
        try:
            if '/' in item:
                net = ipaddress.ip_network(item, strict=False)
                if client_addr in net:
                    return True
            else:
                addr = ipaddress.ip_address(item)
                if client_addr == addr:
                    return True
        except ValueError:
            continue
    return False


class ApiKeyAuthentication(authentication.BaseAuthentication):
    """
    Authenticates requests using cryptographically secure Convernix API keys.
    Supports headers:
      - X-API-Key: cvx_live_...
      - Authorization: Bearer cvx_live_...
    """

    def authenticate_header(self, request):
        return 'Bearer realm="Convernix API Key"'

    def authenticate(self, request) -> Optional[Tuple[IntegrationPrincipal, IntegrationAuthContext]]:
        raw_key = None
        auth_header = request.headers.get('Authorization', '')

        if auth_header.startswith('Bearer cvx_') or auth_header.startswith('ApiKey cvx_'):
            raw_key = auth_header.split(' ', 1)[1].strip()
        elif request.headers.get('X-API-Key', '').startswith('cvx_'):
            raw_key = request.headers.get('X-API-Key', '').strip()

        if not raw_key:
            return None

        # Format validation
        if not (raw_key.startswith('cvx_live_') or raw_key.startswith('cvx_test_')):
            raise exceptions.AuthenticationFailed('Invalid API key format. Expected prefix cvx_live_ or cvx_test_.')

        prefix_parts = raw_key.split('_')
        if len(prefix_parts) < 3:
            raise exceptions.AuthenticationFailed('Malformed API key.')

        # Key prefix is the first 16 characters e.g. "cvx_live_ab12cd34"
        key_prefix = raw_key[:16]
        hashed_secret = hashlib.sha256(raw_key.encode('utf-8')).hexdigest()

        # Lookup by key prefix
        candidate_keys = ApiKey.objects.filter(
            key_prefix=key_prefix,
            is_active=True,
        ).select_related('tenant', 'service_account')

        matched_key: Optional[ApiKey] = None
        for candidate in candidate_keys:
            if hmac.compare_digest(candidate.secret_hash, hashed_secret):
                matched_key = candidate
                break

        if not matched_key:
            raise exceptions.AuthenticationFailed('Invalid or unrecognized API key.')

        # Validate lifecycle & revocation
        if matched_key.revoked_at is not None:
            raise exceptions.AuthenticationFailed('API key has been revoked.')

        if matched_key.expires_at and timezone.now() > matched_key.expires_at:
            raise exceptions.AuthenticationFailed('API key has expired.')

        # Validate service account
        if matched_key.service_account and matched_key.service_account.status != 'active':
            raise exceptions.AuthenticationFailed(f'Service account is {matched_key.service_account.status}.')

        # Validate tenant
        tenant = matched_key.tenant
        if not tenant:
            raise exceptions.AuthenticationFailed('API key is not bound to a valid tenant.')

        if tenant.is_suspended:
            raise exceptions.PermissionDenied('Organization account is suspended.')

        if tenant.is_deleted:
            raise exceptions.PermissionDenied('Organization account is deleted.')

        # Validate IP restrictions
        client_ip = get_client_ip(request)
        if matched_key.ip_restrictions and not is_ip_allowed(client_ip, matched_key.ip_restrictions):
            logger.warning('API key %s rejected from disallowed IP %s', matched_key.id, client_ip)
            raise exceptions.PermissionDenied('Client IP address not allowed by API key security policy.')

        # Update last used timestamp efficiently
        ApiKey.objects.filter(pk=matched_key.pk).update(last_used_at=timezone.now())

        # Bind trusted request context
        request_id = request.headers.get('X-Request-ID') or f"req_{uuid.uuid4().hex[:16]}"
        auth_context = IntegrationAuthContext(matched_key, request_id)
        principal = IntegrationPrincipal(matched_key)

        request.tenant = tenant
        request.auth_context = auth_context
        request.request_id = request_id

        return (principal, auth_context)

