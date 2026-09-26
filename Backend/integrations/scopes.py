from typing import List, Union
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied


ALL_SCOPES = [
    # Leads
    'lead:read',
    'lead:create',
    'lead:update',
    # Contacts
    'contact:read',
    'contact:create',
    'contact:update',
    # Conversations
    'conversation:read',
    # Messages
    'message:read',
    'message:send',
    # Tickets / Enquiries
    'ticket:read',
    'ticket:create',
    'ticket:update',
    # Campaigns
    'campaign:read',
    'campaign:create',
    'campaign:execute',
    # Analytics
    'analytics:read',
    # Webhooks
    'webhook:read',
    'webhook:manage',
    # Connectors & Integrations
    'integration:read',
    'integration:manage',
]

SCOPE_DESCRIPTIONS = {
    'lead:read': 'Retrieve leads and pipeline enquiries',
    'lead:create': 'Create new leads and customer enquiries',
    'lead:update': 'Modify lead stage, status, assignments, or notes',
    'contact:read': 'View customer profiles and contact details',
    'contact:create': 'Create customer contacts',
    'contact:update': 'Update customer contact profiles and consent',
    'conversation:read': 'Access customer conversation metadata and threads',
    'message:read': 'Read incoming and outgoing WhatsApp messages',
    'message:send': 'Send outbound messages and notifications',
    'ticket:read': 'View support tickets and enquiries',
    'ticket:create': 'Create support tickets',
    'ticket:update': 'Assign, update, or resolve tickets',
    'campaign:read': 'View marketing campaigns and templates',
    'campaign:create': 'Draft and configure outbound campaigns',
    'campaign:execute': 'Trigger or schedule campaign delivery',
    'analytics:read': 'Access metrics, aggregate volume, and reporting',
    'webhook:read': 'View configured webhook endpoints and delivery logs',
    'webhook:manage': 'Create, edit, rotate secrets, and delete webhooks',
    'integration:read': 'View installed connectors, status, and mappings',
    'integration:manage': 'Configure, sync, and authorize external connectors',
}

# Mapping from API scope to dashboard user RBAC permission code
SCOPE_TO_RBAC_PERMISSION = {
    'lead:read': 'lead.view',
    'lead:create': 'lead.view',
    'lead:update': 'lead.assign',
    'contact:read': 'lead.view',
    'contact:create': 'lead.view',
    'contact:update': 'lead.assign',
    'conversation:read': 'conversation.view',
    'message:read': 'conversation.view',
    'message:send': 'conversation.reply',
    'ticket:read': 'lead.view',
    'ticket:create': 'lead.view',
    'ticket:update': 'lead.assign',
    'campaign:read': 'campaign.view',
    'campaign:create': 'campaign.manage',
    'campaign:execute': 'campaign.manage',
    'analytics:read': 'usage.read',
    'webhook:read': 'webhook.view',
    'webhook:manage': 'webhook.update',
    'integration:read': 'integration.view',
    'integration:manage': 'integration.manage',
}


class RequireScope(BasePermission):
    """
    DRF permission class that validates the client has at least one of the specified scopes.
    For API key requests, checks request.auth_context.scopes.
    For standard JWT/session user requests, checks user tenant RBAC permissions.
    """

    def __init__(self, scopes: Union[str, List[str]]):
        if isinstance(scopes, str):
            self.required_scopes = [scopes]
        else:
            self.required_scopes = list(scopes)

    def __call__(self):
        return self

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False

        # If authenticated via API Key / Service Account
        auth_context = getattr(request, 'auth_context', None)
        if auth_context:
            for scope in self.required_scopes:
                if auth_context.has_scope(scope):
                    return True
            raise PermissionDenied(
                f"Insufficient scope. Required one of: {', '.join(self.required_scopes)}"
            )

        # Superusers bypass
        if getattr(user, 'is_superuser', False):
            return True

        # Standard interactive user session: check RBAC
        from users.permissions import has_tenant_permission
        from users.tenant_context import get_request_tenant
        tenant = get_request_tenant(request)

        for scope in self.required_scopes:
            rbac_code = SCOPE_TO_RBAC_PERMISSION.get(scope, scope)
            if has_tenant_permission(user, tenant, rbac_code):
                return True

        raise PermissionDenied(
            f"Insufficient permissions for action (requires scope: {', '.join(self.required_scopes)})"
        )

