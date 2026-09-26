from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.exceptions import PermissionDenied


def access_role(user):
    if not user or not user.is_authenticated:
        return 'anonymous'
    if user.is_superuser:
        return 'owner'
    if user.is_staff and user.role not in ('admin', 'owner'):
        return 'admin'
    return user.role or 'viewer'


def has_tenant_permission(user, tenant, permission_code: str) -> bool:
    """Authoritative server-side permission evaluator against granular RBAC policies."""
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    # Check TenantMembership first
    from .models import TenantMembership
    membership = TenantMembership.objects.filter(user=user, tenant=tenant).first() if tenant else None
    role_slug = membership.role if membership else getattr(user, 'role', 'viewer')

    if role_slug in ('owner', 'superadmin'):
        return True

    # System role baseline mapping following least privilege & separation of duties
    system_role_perms = {
        'admin': lambda code: not code.startswith('subscription.manage'),
        'security_admin': lambda code: code in (
            'security.manage', 'audit.view', 'audit.read', 'privacy.request.manage',
            'compliance.view', 'users.read', 'tenant.settings.read',
            'api_key.view', 'api_key.create', 'api_key.revoke',
            'service_account.view', 'service_account.manage',
            'webhook.view', 'integration.view', 'api_logs.view', 'integration_audit.view',
        ),
        'billing_admin': lambda code: code in (
            'tenant.settings.read', 'billing.read', 'billing.manage', 'subscription.read',
            'subscription.manage', 'usage.read', 'audit.read', 'billing.view',
        ),
        'manager': lambda code: code in (
            'tenant.settings.read', 'users.read', 'departments.read', 'departments.create', 'departments.update',
            'whatsapp.read', 'templates.read', 'templates.create', 'templates.update', 'templates.publish',
            'usage.read', 'audit.read', 'lead.view', 'lead.assign', 'lead.phone.view', 'lead.email.view',
            'lead.export', 'conversation.view', 'conversation.reply',
            'inbox.view', 'conversation.claim', 'conversation.assign', 'conversation.reassign',
            'conversation.transfer', 'conversation.resolve', 'conversation.reopen',
            'message.view', 'message.send', 'note.view', 'note.create',
            'attachment.upload', 'attachment.download', 'contact.view_pii',
            'department.queue.view', 'audit.view',
            'lead.create', 'lead.read', 'lead.read_all', 'lead.update', 'lead.delete',
            'lead.reassign', 'lead.change_stage',
            'customer.create', 'customer.read', 'customer.update', 'customer.merge', 'customer.view_pii',
            'activity.create', 'activity.read',
            'note.update', 'note.delete',
            'pipeline.manage', 'custom_field.manage', 'tag.manage',
        ),
        'agent': lambda code: code in (
            'tenant.settings.read', 'departments.read', 'whatsapp.read', 'templates.read',
            'lead.view', 'lead.assign', 'conversation.view', 'conversation.reply',
            'inbox.view', 'conversation.claim', 'conversation.assign',
            'conversation.transfer', 'conversation.resolve', 'conversation.reopen',
            'message.view', 'message.send', 'note.view', 'note.create',
            'attachment.upload', 'attachment.download', 'department.queue.view',
            'lead.create', 'lead.read', 'lead.update', 'lead.change_stage',
            'customer.create', 'customer.read', 'customer.update',
            'activity.create', 'activity.read',
            'note.update',
        ),
        'auditor': lambda code: code in (
            'audit.view', 'audit.read', 'usage.read', 'compliance.view', 'tenant.settings.read',
            'inbox.view', 'conversation.view', 'message.view', 'note.view',
            'lead.read', 'lead.read_all', 'customer.read', 'activity.read',
        ),
        'read_only': lambda code: (code.endswith('.read') or code.endswith('.view')) and code not in ('contact.view_pii', 'customer.view_pii'),
    }

    if role_slug in system_role_perms and system_role_perms[role_slug](permission_code):
        return True

    # Custom role lookup in database
    if tenant:
        from organization.models import CustomRole, RolePermission
        custom_role = CustomRole.objects.filter(tenant=tenant, slug=role_slug).first()
        if custom_role:
            if custom_role.permissions and custom_role.permissions.get(permission_code):
                return True
            if RolePermission.objects.filter(role=custom_role, permission__code=permission_code).exists():
                return True

    return False


def check_tenant_permission(request, permission_code: str):
    """Enforces that the current authenticated user has permission_code; raises PermissionDenied if not."""
    from .tenant_context import get_request_tenant
    tenant = get_request_tenant(request)
    if not has_tenant_permission(request.user, tenant, permission_code):
        raise PermissionDenied(f"You don't have permission to perform this action (requires '{permission_code}').")
    return True


class PlatformReadWritePermission(BasePermission):
    """Viewers can read; Editors, Admins and Owners can mutate."""
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and (
            request.method in SAFE_METHODS or access_role(request.user) in ('editor', 'admin', 'owner')
        ))


class PlatformAdminPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and access_role(request.user) in ('admin', 'owner'))


class RequirePermission(BasePermission):
    """Declarative view permission checking canonical permission code."""
    def __init__(self, permission_code: str):
        self.permission_code = permission_code

    def has_permission(self, request, view):
        code = getattr(view, 'required_permission', self.permission_code)
        from .tenant_context import get_request_tenant
        return has_tenant_permission(request.user, get_request_tenant(request), code)

