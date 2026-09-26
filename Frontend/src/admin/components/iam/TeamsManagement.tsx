import React, { useState } from 'react';
import { Users, Plus, Edit2, UserPlus, X, Radio, ArrowRight } from 'lucide-react';
import { AdminPageHeader } from '../common/AdminPageHeader';
import { StatusBadge } from '../common/StatusBadge';
import type { TeamDepartment } from '../../types';

interface TeamsManagementProps {
  teams: TeamDepartment[];
  onCreateTeam: (data: { name: string; description?: string }) => Promise<boolean>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export function TeamsManagement({ teams, onCreateTeam, toast }: TeamsManagementProps) {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [creating, setCreating] = useState(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast('Please enter a department/team name.', 'error');
      return;
    }

    setCreating(true);
    const ok = await onCreateTeam({ name: name.trim(), description: desc.trim() });
    setCreating(false);
    if (ok) {
      setName('');
      setDesc('');
      setShowCreateModal(false);
    }
  };

  return (
    <div className="pm-iam-panel">
      <AdminPageHeader
        breadcrumbs={[
          { label: 'Administration' },
          { label: 'IAM' },
          { label: 'Teams' },
        ]}
        title="Departments & Teams"
        subtitle="Organize staff into operational units and link WhatsApp queue routing to specific departmental pools."
        actions={
          <button
            type="button"
            className="pm-primary-btn"
            onClick={() => setShowCreateModal(true)}
          >
            <Plus size={14} /> Create Team
          </button>
        }
      />

      <div className="pm-teams-grid-pro">
        {teams.map((t) => (
          <div key={t.id} className="pm-team-card-pro">
            <div className="pm-team-card-head">
              <div>
                <h4>{t.name} Department</h4>
                <p className="pm-team-desc">{t.description}</p>
              </div>
              <StatusBadge status={t.status} />
            </div>

            <div className="pm-team-meta-stack">
              <div className="pm-team-meta-row">
                <span className="pm-meta-label">Team Manager:</span>
                <strong>{t.manager}</strong>
              </div>

              <div className="pm-team-meta-row">
                <span className="pm-meta-label">Assigned Members:</span>
                <span>{t.members_count} Operator{t.members_count === 1 ? '' : 's'}</span>
              </div>

              <div className="pm-team-meta-row">
                <span className="pm-meta-label">Assigned WhatsApp Queues:</span>
                <div className="pm-queues-list">
                  {t.assigned_queues?.map((q, idx) => (
                    <code key={idx} className="pm-queue-tag">
                      <Radio size={10} color="#25d366" /> {q}
                    </code>
                  )) || <span>Default queue</span>}
                </div>
              </div>
            </div>

            <div className="pm-team-card-actions">
              <button
                type="button"
                className="pm-secondary-btn small"
                onClick={() => toast(`Editing team ${t.name}`, 'info')}
              >
                <Edit2 size={12} /> Edit Team
              </button>
              <button
                type="button"
                className="pm-secondary-btn small"
                onClick={() => toast(`Managing members for ${t.name}`, 'info')}
              >
                <UserPlus size={12} /> Manage Members
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Create Team Modal */}
      {showCreateModal && (
        <div className="pm-modal-overlay" onClick={() => setShowCreateModal(false)} role="presentation">
          <div
            className="pm-confirm-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-team-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="pm-confirm-dialog-header">
              <div className="pm-avatar-circle" aria-hidden="true">
                <Users size={18} />
              </div>
              <div>
                <h3 id="create-team-title">Create Department / Team</h3>
                <p>Define a new organizational unit for WhatsApp inquiry assignment.</p>
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
                <label htmlFor="tm_name">
                  Department Name <span className="req">*</span>
                </label>
                <input
                  id="tm_name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Enterprise Sales, Retention, Compliance"
                  required
                  autoFocus
                />
              </div>

              <div className="pm-form-field">
                <label htmlFor="tm_desc">Description</label>
                <textarea
                  id="tm_desc"
                  rows={2}
                  value={desc}
                  onChange={(e) => setDesc(e.target.value)}
                  placeholder="Explain the scope and responsibilities of this team..."
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
                  {creating ? 'Creating...' : 'Create Team'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

