import React, { useState } from 'react';
import { Shield, Plus, Lock, CheckCircle2, UserCheck, X } from 'lucide-react';
import { AdminPageHeader } from '../common/AdminPageHeader';
import type { RoleDefinition } from '../../types';

interface RolesManagementProps {
  systemRoles: RoleDefinition[];
  customRoles: RoleDefinition[];
  onCreateRole: (data: { name: string; description: string; permissions: Record<string, string[]> }) => Promise<boolean>;
  onNavigateToPolicies: () => void;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export function RolesManagement({
  systemRoles,
  customRoles,
  onCreateRole,
  onNavigateToPolicies,
  toast,
}: RolesManagementProps) {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newRoleName, setNewRoleName] = useState('');
  const [newRoleDesc, setNewRoleDesc] = useState('');
  const [creating, setCreating] = useState(false);

  const allRoles = [...systemRoles, ...customRoles];

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRoleName.trim()) {
      toast('Please enter a role name.', 'error');
      return;
    }

    setCreating(true);
    const ok = await onCreateRole({
      name: newRoleName.trim(),
      description: newRoleDesc.trim(),
      permissions: {},
    });
    setCreating(false);
    if (ok) {
      setNewRoleName('');
      setNewRoleDesc('');
      setShowCreateModal(false);
    }
  };

  return (
    <div className="pm-iam-panel">
      <AdminPageHeader
        breadcrumbs={[
          { label: 'Administration' },
          { label: 'IAM' },
          { label: 'Roles' },
        ]}
        title="Role Management"
        subtitle="Review predefined system authorization profiles and provision custom operational roles."
        actions={
          <div className="pm-header-action-group">
            <button
              type="button"
              className="pm-secondary-btn"
              onClick={onNavigateToPolicies}
            >
              Permission Matrix →
            </button>
            <button
              type="button"
              className="pm-primary-btn"
              onClick={() => setShowCreateModal(true)}
            >
              <Plus size={14} /> Create Role
            </button>
          </div>
        }
      />

      <div className="pm-admin-role-grid-pro">
        {allRoles.map((role) => {
          const isOwner = role.slug === 'owner';

          return (
            <div key={role.id || role.slug} className="pm-admin-role-card-pro">
              <div className="pm-role-card-head">
                <div className="pm-role-card-title-group">
                  <div className="pm-role-icon">
                    <Shield size={16} />
                  </div>
                  <strong>{role.name}</strong>
                </div>
                <span className={`pm-role-system-tag ${role.is_system ? 'system' : 'custom'}`}>
                  {role.is_system ? 'System' : 'Custom'}
                </span>
              </div>

              <p className="pm-role-card-desc">{role.description}</p>

              <div className="pm-role-card-meta-row">
                <div className="pm-role-user-count">
                  <UserCheck size={13} />
                  <span>{role.user_count} User{role.user_count === 1 ? '' : 's'} assigned</span>
                </div>
                {isOwner && (
                  <span className="pm-role-protected" title="Owner role is permanently protected">
                    <Lock size={12} /> Permanent
                  </span>
                )}
              </div>

              <div className="pm-role-card-footer">
                <button
                  type="button"
                  className="pm-btn-link"
                  onClick={onNavigateToPolicies}
                >
                  Inspect Permissions →
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Create Custom Role Modal */}
      {showCreateModal && (
        <div className="pm-modal-overlay" onClick={() => setShowCreateModal(false)} role="presentation">
          <div
            className="pm-confirm-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-role-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="pm-confirm-dialog-header">
              <div className="pm-avatar-circle" aria-hidden="true">
                <Shield size={18} />
              </div>
              <div>
                <h3 id="create-role-title">Create Custom Role</h3>
                <p>Define a new organizational authorization profile with tailored module rights.</p>
              </div>
              <button
                type="button"
                className="pm-modal-close"
                onClick={() => setShowCreateModal(false)}
                aria-label="Close modal"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleCreate} className="pm-form-stack" style={{ marginTop: 16 }}>
              <div className="pm-form-field">
                <label htmlFor="cr_name">
                  Role Name <span className="req">*</span>
                </label>
                <input
                  id="cr_name"
                  type="text"
                  value={newRoleName}
                  onChange={(e) => setNewRoleName(e.target.value)}
                  placeholder="e.g. Lead Qualifier, Compliance Officer"
                  required
                  autoFocus
                />
              </div>

              <div className="pm-form-field">
                <label htmlFor="cr_desc">Description</label>
                <textarea
                  id="cr_desc"
                  rows={2}
                  value={newRoleDesc}
                  onChange={(e) => setNewRoleDesc(e.target.value)}
                  placeholder="Summarize the operational scope of this role..."
                />
              </div>

              <div className="pm-confirm-dialog-actions">
                <button
                  type="button"
                  className="pm-secondary-btn"
                  onClick={() => setShowCreateModal(false)}
                  disabled={creating}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="pm-primary-btn"
                  disabled={creating}
                >
                  {creating ? 'Creating...' : 'Create Role'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

