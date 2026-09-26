import React, { useState } from 'react';
import { X, Mail, UserPlus, Shield } from 'lucide-react';

interface InviteUserDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onInvite: (data: { email: string; first_name: string; last_name: string; role: string; team: string }) => Promise<boolean>;
  currentUserRole?: string;
  teams: { name: string }[];
}

export function InviteUserDrawer({
  isOpen,
  onClose,
  onInvite,
  currentUserRole = 'owner',
  teams,
}: InviteUserDrawerProps) {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('agent');
  const [team, setTeam] = useState(teams[0]?.name || 'Support');
  const [sendEmail, setSendEmail] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email || !email.includes('@')) {
      setError('Please provide a valid email address.');
      return;
    }
    if (!firstName.trim()) {
      setError('First name is required.');
      return;
    }

    setSubmitting(true);
    const ok = await onInvite({
      email: email.trim().toLowerCase(),
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      role,
      team,
    });
    setSubmitting(false);
    if (ok) {
      setFirstName('');
      setLastName('');
      setEmail('');
      setRole('agent');
      onClose();
    }
  };

  return (
    <div className="pm-modal-overlay" onClick={onClose} role="presentation">
      <div
        className="pm-drawer-container"
        role="dialog"
        aria-modal="true"
        aria-labelledby="invite-drawer-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="pm-drawer-header">
          <div className="pm-drawer-title-wrap">
            <div className="pm-drawer-icon" aria-hidden="true">
              <UserPlus size={18} />
            </div>
            <div>
              <h2 id="invite-drawer-title">Invite Team Member</h2>
              <p>Add a new operator, administrator, or manager to your workspace.</p>
            </div>
          </div>
          <button type="button" className="pm-modal-close" onClick={onClose} aria-label="Close drawer">
            <X size={16} />
          </button>
        </header>

        <form onSubmit={handleSubmit} className="pm-drawer-form" noValidate>
          {error && (
            <div className="pm-form-error-banner" role="alert">
              {error}
            </div>
          )}

          <div className="pm-form-grid-2">
            <div className="pm-form-field">
              <label htmlFor="inv_first_name">
                First Name <span className="req">*</span>
              </label>
              <input
                id="inv_first_name"
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="e.g. Priya"
                required
                autoFocus
              />
            </div>

            <div className="pm-form-field">
              <label htmlFor="inv_last_name">Last Name</label>
              <input
                id="inv_last_name"
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="e.g. Sharma"
              />
            </div>
          </div>

          <div className="pm-form-field">
            <label htmlFor="inv_email">
              Email Address <span className="req">*</span>
            </label>
            <input
              id="inv_email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="operator@company.com"
              required
            />
            <small className="field-help">An activation link will be dispatched to this address</small>
          </div>

          <div className="pm-form-grid-2">
            <div className="pm-form-field">
              <label htmlFor="inv_role">Assigned Role</label>
              <select
                id="inv_role"
                value={role}
                onChange={(e) => setRole(e.target.value)}
              >
                {currentUserRole === 'owner' && <option value="owner">Owner (Full Tenant Control)</option>}
                <option value="admin">Administrator</option>
                <option value="manager">Manager</option>
                <option value="agent">Agent (Standard Support)</option>
                <option value="billing_admin">Billing Administrator</option>
                <option value="viewer">Read Only Viewer</option>
              </select>
            </div>

            <div className="pm-form-field">
              <label htmlFor="inv_team">Assigned Team / Department</label>
              <select
                id="inv_team"
                value={team}
                onChange={(e) => setTeam(e.target.value)}
              >
                {teams.map((t) => (
                  <option key={t.name} value={t.name}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <label className="pm-checkbox-row">
            <input
              type="checkbox"
              checked={sendEmail}
              onChange={(e) => setSendEmail(e.target.checked)}
            />
            <span>Send invitation email with secure activation link immediately</span>
          </label>

          <div className="pm-drawer-footer">
            <button
              type="button"
              className="pm-secondary-btn"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="pm-primary-btn"
              disabled={submitting}
            >
              {submitting ? 'Sending Invitation...' : 'Send Invitation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

