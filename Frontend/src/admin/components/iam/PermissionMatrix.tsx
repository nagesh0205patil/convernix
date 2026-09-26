import React, { useState } from 'react';
import { CheckSquare, Square, Save, RotateCcw } from 'lucide-react';
import { AdminPageHeader } from '../common/AdminPageHeader';
import { PERMISSION_MODULES, DEFAULT_ROLE_MATRICES } from '../../constants/permissions';

interface PermissionMatrixProps {
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export function PermissionMatrix({ toast }: PermissionMatrixProps) {
  const [selectedRole, setSelectedRole] = useState('manager');
  const [rolePermissions, setRolePermissions] = useState<Record<string, Set<string>>>(() => {
    const initial: Record<string, Set<string>> = {};
    for (const [r, list] of Object.entries(DEFAULT_ROLE_MATRICES)) {
      initial[r] = new Set(list);
    }
    return initial;
  });
  const [dirty, setDirty] = useState(false);

  const currentSet = rolePermissions[selectedRole] || new Set();

  const handleToggle = (actionKey: string) => {
    if (selectedRole === 'owner') {
      toast('The Owner role has full administrative authority and cannot be modified.', 'info');
      return;
    }

    setRolePermissions((prev) => {
      const nextSet = new Set(prev[selectedRole] || []);
      if (nextSet.has(actionKey)) {
        nextSet.delete(actionKey);
      } else {
        nextSet.add(actionKey);
      }
      return { ...prev, [selectedRole]: nextSet };
    });
    setDirty(true);
  };

  const handleSelectAll = () => {
    if (selectedRole === 'owner') return;
    const all = PERMISSION_MODULES.flatMap((m) => m.actions.map((a) => a.key));
    setRolePermissions((prev) => ({ ...prev, [selectedRole]: new Set(all) }));
    setDirty(true);
    toast('All module permissions selected.', 'info');
  };

  const handleClearAll = () => {
    if (selectedRole === 'owner') return;
    setRolePermissions((prev) => ({ ...prev, [selectedRole]: new Set() }));
    setDirty(true);
    toast('All permissions cleared for role.', 'info');
  };

  const handleSave = () => {
    setDirty(false);
    toast(`Permission policies saved for ${selectedRole}.`, 'success');
  };

  const handleReset = () => {
    setRolePermissions((prev) => ({
      ...prev,
      [selectedRole]: new Set(DEFAULT_ROLE_MATRICES[selectedRole] || []),
    }));
    setDirty(false);
    toast('Permissions reset to system defaults.', 'info');
  };

  const roles = [
    { key: 'owner', label: 'Owner (Protected)' },
    { key: 'admin', label: 'Administrator' },
    { key: 'manager', label: 'Manager' },
    { key: 'agent', label: 'Agent' },
    { key: 'billing_admin', label: 'Billing Administrator' },
    { key: 'read_only', label: 'Read Only' },
  ];

  return (
    <div className="pm-iam-panel">
      <AdminPageHeader
        breadcrumbs={[
          { label: 'Administration' },
          { label: 'IAM' },
          { label: 'Permission Policies' },
        ]}
        title="Permission Policies"
        subtitle="Enforce the principle of least privilege across dashboard, WhatsApp conversations, campaigns, and administrative controls."
        actions={
          <div className="pm-header-action-group">
            <button
              type="button"
              className="pm-secondary-btn"
              onClick={handleReset}
              disabled={!dirty || selectedRole === 'owner'}
            >
              <RotateCcw size={13} /> Reset Defaults
            </button>
            <button
              type="button"
              className="pm-primary-btn"
              onClick={handleSave}
              disabled={!dirty || selectedRole === 'owner'}
            >
              <Save size={14} /> Save Role Policies
            </button>
          </div>
        }
      />

      {/* Role Picker Bar */}
      <div className="pm-policy-role-selector">
        <span className="pm-role-select-label">Configure Role:</span>
        <div className="pm-role-pills-row">
          {roles.map((r) => (
            <button
              key={r.key}
              type="button"
              className={`pm-role-tab-btn ${selectedRole === r.key ? 'active' : ''}`}
              onClick={() => setSelectedRole(r.key)}
            >
              {r.label}
            </button>
          ))}
        </div>

        <div className="pm-matrix-bulk-actions">
          <button
            type="button"
            className="pm-secondary-btn small"
            onClick={handleSelectAll}
            disabled={selectedRole === 'owner'}
          >
            Select All
          </button>
          <button
            type="button"
            className="pm-secondary-btn small"
            onClick={handleClearAll}
            disabled={selectedRole === 'owner'}
          >
            Clear All
          </button>
        </div>
      </div>

      {/* Permission Modules Matrix */}
      <div className="pm-permission-matrix-container">
        {PERMISSION_MODULES.map((module) => {
          const moduleActionKeys = module.actions.map((a) => a.key);
          const allChecked = moduleActionKeys.every((k) => currentSet.has(k));
          const someChecked = moduleActionKeys.some((k) => currentSet.has(k)) && !allChecked;

          const toggleModuleAll = () => {
            if (selectedRole === 'owner') return;
            setRolePermissions((prev) => {
              const nextSet = new Set(prev[selectedRole] || []);
              if (allChecked) {
                moduleActionKeys.forEach((k) => nextSet.delete(k));
              } else {
                moduleActionKeys.forEach((k) => nextSet.add(k));
              }
              return { ...prev, [selectedRole]: nextSet };
            });
            setDirty(true);
          };

          return (
            <div key={module.key} className="pm-matrix-module-card">
              <div className="pm-matrix-module-header">
                <div className="pm-matrix-module-title">
                  <label className="pm-checkbox-label">
                    <input
                      type="checkbox"
                      checked={allChecked}
                      ref={(el) => {
                        if (el) el.indeterminate = someChecked;
                      }}
                      onChange={toggleModuleAll}
                      disabled={selectedRole === 'owner'}
                    />
                    <strong>{module.label} Module</strong>
                  </label>
                </div>
                <span className="pm-matrix-action-count">
                  {moduleActionKeys.filter((k) => currentSet.has(k)).length} of {module.actions.length} enabled
                </span>
              </div>

              <div className="pm-matrix-actions-grid">
                {module.actions.map((act) => {
                  const isChecked = currentSet.has(act.key);

                  return (
                    <label
                      key={act.key}
                      className={`pm-matrix-action-item ${isChecked ? 'active' : ''}`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => handleToggle(act.key)}
                        disabled={selectedRole === 'owner'}
                      />
                      <div>
                        <strong>{act.label}</strong>
                        {act.description && <small>{act.description}</small>}
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

