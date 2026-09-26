from rest_framework.permissions import BasePermission
from users.tenant_context import get_request_tenant
from users.permissions import has_tenant_permission
from .exceptions import PermissionDeniedInboxException, TenantAccessDeniedException


class HasInboxPermission(BasePermission):
    """
    Validates authenticated user, valid tenant context, and granular RBAC code.
    Deny-by-default security model.
    """
    required_permission: str = 'inbox.view'

    def __init__(self, permission_code: str = None):
        if permission_code:
            self.required_permission = permission_code

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        tenant = get_request_tenant(request)
        if not tenant:
            if request.user.is_superuser:
                return True
            raise TenantAccessDeniedException('No active organization/tenant context resolved.')

        if tenant.is_suspended:
            raise TenantAccessDeniedException('Tenant organization is suspended.')

        perm_code = getattr(view, 'required_permission', self.required_permission)
        if not has_tenant_permission(request.user, tenant, perm_code):
            raise PermissionDeniedInboxException(
                f"You don't have permission to perform this action (requires '{perm_code}')."
            )
        return True


def check_department_access(user, tenant, department) -> bool:
    """
    Validate that user has access to the specified department queue.
    Tenant owners, platform admins, and department managers have department-wide visibility.
    Agents can access if they are members of the department or assigned to the conversation.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not department:
        return True
    if department.tenant_id != tenant.id:
        return False

    # Check user role
    from users.models import TenantMembership
    membership = TenantMembership.objects.filter(user=user, tenant=tenant).first()
    role = membership.role if membership else getattr(user, 'role', 'agent')

    if role in ('owner', 'superadmin', 'admin'):
        return True

    # Check if user is department manager
    if department.manager_id == user.id:
        return True

    # Check department membership
    from whatsapp.models import DepartmentMember
    is_member = DepartmentMember.objects.filter(department=department, user=user, active=True).exists()
    if is_member:
        return True

    # Legacy fallback: match user.team_name with department.name
    if getattr(user, 'team_name', '').strip().lower() == department.name.strip().lower():
        return True

    return False

