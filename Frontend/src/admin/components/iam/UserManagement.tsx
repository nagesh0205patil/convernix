import React, { useState, useMemo } from 'react';
import {
  Users,
  Plus,
  MoreVertical,
  UserX,
  Mail,
  ShieldAlert,
  Edit2,
  RefreshCw,
  Eye,
} from 'lucide-react';
import { AdminPageHeader } from '../common/AdminPageHeader';
import { FilterBar, type FilterSelectConfig } from '../common/FilterBar';
import { DataTable, type Column } from '../common/DataTable';
import { StatusBadge } from '../common/StatusBadge';
import { EmptyState } from '../common/EmptyState';
import { ConfirmationDialog } from '../common/ConfirmationDialog';
import { InviteUserDrawer } from './InviteUserDrawer';
import type { AdminUser, TeamDepartment } from '../../types';

interface UserManagementProps {
  users: AdminUser[];
  teams: TeamDepartment[];
  currentUser: any;
  onInvite: (data: any) => Promise<boolean>;
  onUpdateRole: (id: number, updates: Partial<AdminUser>) => Promise<boolean>;
  onDeactivate: (id: number) => Promise<boolean>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export function UserManagement({
  users,
  teams,
  currentUser,
  onInvite,
  onUpdateRole,
  onDeactivate,
  toast,
}: UserManagementProps) {
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [teamFilter, setTeamFilter] = useState('all');
  const [mfaFilter, setMfaFilter] = useState('all');
  const [showInviteDrawer, setShowInviteDrawer] = useState(false);
  const [activeMenuId, setActiveMenuId] = useState<number | null>(null);
  const [deactivateTarget, setDeactivateTarget] = useState<AdminUser | null>(null);
  const [selectedUserDetail, setSelectedUserDetail] = useState<AdminUser | null>(null);

  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      const matchesSearch =
        u.name.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase());
      const matchesRole = roleFilter === 'all' || u.role.toLowerCase() === roleFilter.toLowerCase();
      const matchesStatus = statusFilter === 'all' || u.status.toLowerCase() === statusFilter.toLowerCase();
      const matchesTeam = teamFilter === 'all' || u.team.toLowerCase() === teamFilter.toLowerCase();
      const matchesMfa = mfaFilter === 'all' || u.mfa.toLowerCase() === mfaFilter.toLowerCase();

      return matchesSearch && matchesRole && matchesStatus && matchesTeam && matchesMfa;
    });
  }, [users, search, roleFilter, statusFilter, teamFilter, mfaFilter]);

  const filters: FilterSelectConfig[] = [
    {
      key: 'role',
      label: 'Role',
      value: roleFilter,
      onChange: setRoleFilter,
      options: [
        { label: 'All Roles', value: 'all' },
        { label: 'Owner', value: 'owner' },
        { label: 'Administrator', value: 'admin' },
        { label: 'Manager', value: 'manager' },
        { label: 'Agent', value: 'agent' },
        { label: 'Billing Admin', value: 'billing_admin' },
      ],
    },
    {
      key: 'status',
      label: 'Status',
      value: statusFilter,
      onChange: setStatusFilter,
      options: [
        { label: 'All Statuses', value: 'all' },
        { label: 'Active', value: 'active' },
        { label: 'Invited', value: 'invited' },
        { label: 'Suspended', value: 'suspended' },
        { label: 'Disabled', value: 'disabled' },
      ],
    },
    {
      key: 'team',
      label: 'Team',
      value: teamFilter,
      onChange: setTeamFilter,
      options: [
        { label: 'All Teams', value: 'all' },
        ...teams.map((t) => ({ label: t.name, value: t.name })),
      ],
    },
    {
      key: 'mfa',
      label: 'MFA',
      value: mfaFilter,
      onChange: setMfaFilter,
      options: [
        { label: 'All MFA', value: 'all' },
        { label: 'MFA Enabled', value: 'enabled' },
        { label: 'MFA Disabled', value: 'disabled' },
        { label: 'MFA Pending', value: 'pending' },
      ],
    },
  ];

  const handleToggleSuspend = async (user: AdminUser) => {
    setActiveMenuId(null);
    const newStatus = user.status === 'Suspended' ? 'Active' : 'Suspended';
    await onUpdateRole(user.id, { status: newStatus as any });
  };

  const handleResendInvite = (user: AdminUser) => {
    setActiveMenuId(null);
    toast(`Invitation resent to ${user.email}.`, 'success');
  };

  const handleResetMFA = (user: AdminUser) => {
    setActiveMenuId(null);
    toast(`MFA reset token generated for ${user.email}.`, 'info');
  };

  const columns: Column<AdminUser>[] = [
    {
      key: 'name',
      header: 'User',
      render: (u) => (
        <div className="pm-user-cell">
          <div className="pm-avatar-circle" aria-hidden="true">
            {u.name.charAt(0).toUpperCase()}
          </div>
          <div className="pm-user-name-meta">
            <strong>{u.name}</strong>
            <small>{u.email}</small>
          </div>
        </div>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      render: (u) => <span className="pm-role-pill">{u.role}</span>,
    },
    {
      key: 'team',
      header: 'Team',
      render: (u) => <span>{u.team || 'Support'}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (u) => <StatusBadge status={u.status} type="user" />,
    },
    {
      key: 'last_login',
      header: 'Last Login',
      render: (u) => <span className="pm-text-subtle">{u.last_login}</span>,
    },
    {
      key: 'mfa',
      header: 'MFA',
      render: (u) => (
        <span className={`pm-mfa-badge ${u.mfa.toLowerCase()}`}>
          {u.mfa}
        </span>
      ),
    },
    {
      key: 'created',
      header: 'Created',
      render: (u) => <span className="pm-text-subtle">{u.created}</span>,
    },
    {
      key: 'actions',
      header: 'Actions',
      align: 'right',
      render: (u) => (
        <div className="pm-actions-menu-wrap">
          <button
            type="button"
            className="pm-icon-btn"
            onClick={() => setActiveMenuId(activeMenuId === u.id ? null : u.id)}
            aria-label={`Actions for ${u.name}`}
          >
            <MoreVertical size={15} />
          </button>

          {activeMenuId === u.id && (
            <div className="pm-dropdown-menu right">
              <button
                type="button"
                onClick={() => {
                  setSelectedUserDetail(u);
                  setActiveMenuId(null);
                }}
              >
                <Eye size={13} /> View User
              </button>

              <button
                type="button"
                onClick={() => {
                  const newRole = u.role === 'admin' ? 'agent' : 'admin';
                  onUpdateRole(u.id, { role: newRole });
                  setActiveMenuId(null);
                }}
              >
                <Edit2 size={13} /> Change Role
              </button>

              <button type="button" onClick={() => handleResetMFA(u)}>
                <RefreshCw size={13} /> Reset MFA
              </button>

              {u.status === 'Invited' ? (
                <button type="button" onClick={() => handleResendInvite(u)}>
                  <Mail size={13} /> Resend Invitation
                </button>
              ) : (
                <button type="button" onClick={() => handleToggleSuspend(u)}>
                  <ShieldAlert size={13} /> {u.status === 'Suspended' ? 'Reactivate User' : 'Suspend User'}
                </button>
              )}

              {u.role !== 'owner' && (
                <button
                  type="button"
                  className="danger"
                  onClick={() => {
                    setDeactivateTarget(u);
                    setActiveMenuId(null);
                  }}
                >
                  <UserX size={13} /> Deactivate User
                </button>
              )}
            </div>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="pm-iam-panel">
      <AdminPageHeader
        breadcrumbs={[
          { label: 'Administration' },
          { label: 'IAM' },
          { label: 'Users' },
        ]}
        title="Users"
        subtitle="Manage people who can access your organization."
        actions={
          <button
            type="button"
            className="pm-primary-btn"
            onClick={() => setShowInviteDrawer(true)}
          >
            <Plus size={14} /> Invite User
          </button>
        }
      />

      <FilterBar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search by name or email..."
        filters={filters}
      />

      <DataTable
        columns={columns}
        data={filteredUsers}
        keyExtractor={(item) => item.id}
        emptyState={
          <EmptyState
            icon={Users}
            title="No team members yet"
            description="Invite your team to start collaborating on WhatsApp conversations."
            actionLabel="Invite User"
            onAction={() => setShowInviteDrawer(true)}
          />
        }
      />

      {/* Invite User Drawer */}
      <InviteUserDrawer
        isOpen={showInviteDrawer}
        onClose={() => setShowInviteDrawer(false)}
        onInvite={onInvite}
        currentUserRole={currentUser?.role}
        teams={teams}
      />

      {/* Deactivate User Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={Boolean(deactivateTarget)}
        title="Deactivate User?"
        message={`This user (${deactivateTarget?.name}) will immediately lose access to the organization. Their previous assigned conversation history and audit trails will remain preserved.`}
        confirmLabel="Deactivate User"
        isDanger={true}
        onConfirm={async () => {
          if (deactivateTarget) {
            await onDeactivate(deactivateTarget.id);
            setDeactivateTarget(null);
          }
        }}
        onCancel={() => setDeactivateTarget(null)}
      />

      {/* View User Modal */}
      {selectedUserDetail && (
        <div className="pm-modal-overlay" onClick={() => setSelectedUserDetail(null)} role="presentation">
          <div className="pm-confirm-dialog" onClick={(e) => e.stopPropagation()} role="dialog">
            <div className="pm-confirm-dialog-header">
              <div className="pm-avatar-circle large">
                {selectedUserDetail.name.charAt(0).toUpperCase()}
              </div>
              <div>
                <h3>{selectedUserDetail.name}</h3>
                <p>{selectedUserDetail.email}</p>
              </div>
            </div>

            <dl className="pm-key-value-list" style={{ marginTop: 14 }}>
              <div><dt>Assigned Role</dt><dd><span className="pm-role-pill">{selectedUserDetail.role}</span></dd></div>
              <div><dt>Department Team</dt><dd>{selectedUserDetail.team}</dd></div>
              <div><dt>Account Status</dt><dd><StatusBadge status={selectedUserDetail.status} type="user" /></dd></div>
              <div><dt>Multi-Factor Authentication</dt><dd>{selectedUserDetail.mfa}</dd></div>
              <div><dt>Date Created</dt><dd>{selectedUserDetail.created}</dd></div>
              <div><dt>Last Sign In</dt><dd>{selectedUserDetail.last_login}</dd></div>
            </dl>

            <div className="pm-confirm-dialog-actions">
              <button type="button" className="pm-primary-btn" onClick={() => setSelectedUserDetail(null)}>
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

