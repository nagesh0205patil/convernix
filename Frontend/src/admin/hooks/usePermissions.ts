import { useMemo } from 'react';
import { DEFAULT_ROLE_MATRICES } from '../constants/permissions';

export function usePermissions(userOrRole: any) {
  let role = 'owner';
  let isSuperuser = false;

  if (typeof userOrRole === 'string') {
    role = userOrRole.toLowerCase();
  } else if (userOrRole && typeof userOrRole === 'object') {
    role = (userOrRole.role || 'owner').toLowerCase();
    isSuperuser = Boolean(userOrRole.is_superuser);
  }

  // Normalize common aliases
  if (role === 'administrator') role = 'admin';
  if (role === 'billing') role = 'billing_admin';

  const isOwner = isSuperuser || role === 'owner';
  const isAdmin = isOwner || role === 'admin';
  const isManager = isAdmin || role === 'manager';
  const isBillingAdmin = isOwner || role === 'billing_admin';

  const permissions = useMemo<Set<string>>(() => {
    if (isOwner) {
      return new Set(DEFAULT_ROLE_MATRICES.owner);
    }
    const roleList = DEFAULT_ROLE_MATRICES[role] || DEFAULT_ROLE_MATRICES.agent || [];
    return new Set(roleList);
  }, [role, isOwner]);

  const can = (permissionKey: string): boolean => {
    if (isOwner || isAdmin) return true;
    return permissions.has(permissionKey);
  };

  const canAccess = (module: string, _action = 'view'): boolean => {
    if (isOwner || isAdmin) return true;
    if (module === 'overview') return true;
    if (module === 'settings') return isOwner || isAdmin || can('manage_organization') || can('manage_whatsapp');
    if (module === 'iam' || module === 'users') return isOwner || isAdmin || can('manage_users') || can('manage_roles');
    if (module === 'account' || module === 'billing') return isOwner || isBillingAdmin || can('manage_billing');
    if (module === 'audit') return isOwner || isAdmin || can('view_audit_logs');
    if (module === 'compliance') return isOwner || isAdmin || role === 'security_admin' || role === 'auditor' || can('view_audit_logs');
    return can(module);
  };

  // Section access checks
  const canAccessAdministration = isOwner || isAdmin || isManager || isBillingAdmin || can('manage_organization');
  const canManageOrganization = isOwner || isAdmin || can('manage_organization');
  const canManageWhatsApp = isOwner || isAdmin || can('manage_whatsapp');
  const canManageUsers = isOwner || isAdmin || can('manage_users');
  const canManageRoles = isOwner || isAdmin || can('manage_roles');
  const canManageBilling = isOwner || isBillingAdmin || can('manage_billing');
  const canViewAuditLogs = isOwner || isAdmin || can('view_audit_logs');

  return {
    role,
    isOwner,
    isAdmin,
    isManager,
    isBillingAdmin,
    can,
    canAccess,
    canAccessAdministration,
    canManageOrganization,
    canManageWhatsApp,
    canManageUsers,
    canManageRoles,
    canManageBilling,
    canViewAuditLogs,
  };
}
