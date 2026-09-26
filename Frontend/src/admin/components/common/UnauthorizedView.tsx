import React from 'react';
import { ShieldAlert, ArrowLeft } from 'lucide-react';

interface UnauthorizedViewProps {
  userRole?: string;
  onReturnToDashboard?: () => void;
}

export function UnauthorizedView({
  userRole = 'Agent',
  onReturnToDashboard,
}: UnauthorizedViewProps) {
  return (
    <div className="pm-unauthorized-container" role="region" aria-label="Access Denied">
      <div className="pm-unauthorized-card">
        <div className="pm-unauthorized-icon" aria-hidden="true">
          <ShieldAlert size={48} />
        </div>
        <h2>Access Restricted</h2>
        <p className="pm-unauthorized-lead">You don't have permission to access this administration page.</p>
        <div className="pm-unauthorized-meta">
          <span>Current Role:</span>
          <strong>{userRole}</strong>
        </div>
        <p className="pm-unauthorized-sub">
          Administrative sections require elevated privileges (Owner, Administrator, or Billing Administrator).
          If you believe this is an error, please contact your organization owner to request role adjustment.
        </p>
        {onReturnToDashboard && (
          <button type="button" className="pm-primary-btn" onClick={onReturnToDashboard}>
            <ArrowLeft size={14} /> Return to Dashboard
          </button>
        )}
      </div>
    </div>
  );
}

