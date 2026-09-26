import logging
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.exceptions import PermissionDenied
from users.permissions import has_tenant_permission
from users.tenant_context import get_request_tenant

logger = logging.getLogger(__name__)


class HasCrmPermission:
    """Helper creating BasePermission classes for specific CRM permission codes."""
    def __init__(self, permission_code: str):
        self.permission_code = permission_code

    def __call__(self):
        code = self.permission_code
        class DynamicPermission(BasePermission):
            def has_permission(self, request, view):
                if not request.user or not request.user.is_authenticated:
                    return False
                tenant = get_request_tenant(request)
                if not tenant and not request.user.is_superuser:
                    return False
                return has_tenant_permission(request.user, tenant, code)
        return DynamicPermission


class CrmRecordPermission(BasePermission):
    """
    Enforces record-level restrictions for Leads:
    - Admin/Owner/Manager can view all leads within tenant.
    - Agents with lead.read_all can view all.
    - Otherwise, agent can view/modify leads assigned to them or their department.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        tenant = get_request_tenant(request)
        if not tenant and not request.user.is_superuser:
            return False
        
        required_perm = getattr(view, 'required_permission', 'lead.read' if request.method in SAFE_METHODS else 'lead.update')
        return has_tenant_permission(request.user, tenant, required_perm)

    def has_object_permission(self, request, view, obj):
        tenant = get_request_tenant(request)
        if obj.tenant_id != getattr(tenant, 'id', None) and not request.user.is_superuser:
            return False
        
        if request.user.is_superuser:
            return True

        # Check tenant permission
        required_perm = getattr(view, 'required_permission', 'lead.read' if request.method in SAFE_METHODS else 'lead.update')
        if not has_tenant_permission(request.user, tenant, required_perm):
            return False

        # If user has lead.read_all (e.g. manager/admin), grant access
        if has_tenant_permission(request.user, tenant, 'lead.read_all'):
            return True

        # Check ownership or department membership
        lead_owner_id = getattr(obj, 'owner_user_id', None)
        if lead_owner_id and lead_owner_id == request.user.id:
            return True

        lead_dept = getattr(obj, 'department', None)
        if lead_dept:
            from whatsapp.models import DepartmentMember
            if DepartmentMember.objects.filter(department=lead_dept, user=request.user, active=True).exists():
                return True

        # If unassigned lead, user with lead.read can view
        if not lead_owner_id and request.method in SAFE_METHODS:
            return True

        return False
