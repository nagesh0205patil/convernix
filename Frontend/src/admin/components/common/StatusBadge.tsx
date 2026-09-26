import React from 'react';
import { CheckCircle2, Clock, AlertTriangle, XCircle, ShieldCheck } from 'lucide-react';
import { USER_STATUSES, WHATSAPP_STATUSES, INVOICE_STATUSES } from '../../constants/statuses';

interface StatusBadgeProps {
  status: string;
  type?: 'user' | 'whatsapp' | 'invoice' | 'generic';
  labelOverride?: string;
}

export function StatusBadge({ status, type = 'generic', labelOverride }: StatusBadgeProps) {
  const norm = (status || '').toLowerCase().replace(/\s+/g, '_');

  let visual = {
    label: labelOverride || status || 'Unknown',
    bg: 'rgba(100, 116, 139, 0.15)',
    color: '#94a3b8',
    border: 'rgba(100, 116, 139, 0.3)',
    dotColor: '#64748b',
  };

  if (type === 'user' && USER_STATUSES[norm]) {
    visual = { ...USER_STATUSES[norm], label: labelOverride || USER_STATUSES[norm].label };
  } else if (type === 'whatsapp' && WHATSAPP_STATUSES[norm]) {
    visual = { ...WHATSAPP_STATUSES[norm], label: labelOverride || WHATSAPP_STATUSES[norm].label };
  } else if (type === 'invoice' && INVOICE_STATUSES[norm]) {
    visual = { ...INVOICE_STATUSES[norm], label: labelOverride || INVOICE_STATUSES[norm].label };
  } else if (norm === 'active' || norm === 'success' || norm === 'connected' || norm === 'paid' || norm === 'verified' || norm === 'completed') {
    visual = { label: labelOverride || 'Active', bg: 'rgba(37, 211, 102, 0.12)', color: '#52bb89', border: 'rgba(82, 187, 137, 0.3)', dotColor: '#25d366' };
  } else if (norm === 'pending' || norm === 'invited' || norm === 'pending_verification') {
    visual = { label: labelOverride || 'Pending', bg: 'rgba(245, 158, 11, 0.12)', color: '#fbbf24', border: 'rgba(245, 158, 11, 0.3)', dotColor: '#f59e0b' };
  } else if (norm === 'suspended' || norm === 'failed' || norm === 'error' || norm === 'rejected') {
    visual = { label: labelOverride || 'Failed', bg: 'rgba(239, 68, 68, 0.12)', color: '#f87171', border: 'rgba(239, 68, 68, 0.3)', dotColor: '#ef4444' };
  }

  const renderIcon = () => {
    if (norm === 'active' || norm === 'connected' || norm === 'paid' || norm === 'verified' || norm === 'completed') {
      return <CheckCircle2 size={11} aria-hidden="true" />;
    }
    if (norm === 'pending' || norm === 'invited') {
      return <Clock size={11} aria-hidden="true" />;
    }
    if (norm === 'suspended' || norm === 'failed' || norm === 'error') {
      return <AlertTriangle size={11} aria-hidden="true" />;
    }
    return <span className="pm-badge-dot" style={{ backgroundColor: visual.dotColor }} aria-hidden="true" />;
  };

  return (
    <span
      className="pm-status-badge-pro"
      style={{
        backgroundColor: visual.bg,
        color: visual.color,
        borderColor: visual.border,
      }}
      role="status"
    >
      {renderIcon()}
      <span>{visual.label}</span>
    </span>
  );
}

