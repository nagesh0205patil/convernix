export interface StatusVisual {
  label: string;
  bg: string;
  color: string;
  border: string;
  dotColor?: string;
}

export const USER_STATUSES: Record<string, StatusVisual> = {
  active: { label: 'Active', bg: 'rgba(37, 211, 102, 0.12)', color: '#52bb89', border: 'rgba(82, 187, 137, 0.3)', dotColor: '#25d366' },
  invited: { label: 'Invited', bg: 'rgba(245, 158, 11, 0.12)', color: '#fbbf24', border: 'rgba(245, 158, 11, 0.3)', dotColor: '#f59e0b' },
  suspended: { label: 'Suspended', bg: 'rgba(239, 68, 68, 0.12)', color: '#f87171', border: 'rgba(239, 68, 68, 0.3)', dotColor: '#ef4444' },
  disabled: { label: 'Disabled', bg: 'rgba(100, 116, 139, 0.15)', color: '#94a3b8', border: 'rgba(100, 116, 139, 0.3)', dotColor: '#64748b' },
};

export const WHATSAPP_STATUSES: Record<string, StatusVisual> = {
  connected: { label: 'Connected', bg: 'rgba(37, 211, 102, 0.12)', color: '#52bb89', border: 'rgba(82, 187, 137, 0.3)', dotColor: '#25d366' },
  pending_verification: { label: 'Pending Verification', bg: 'rgba(245, 158, 11, 0.12)', color: '#fbbf24', border: 'rgba(245, 158, 11, 0.3)', dotColor: '#f59e0b' },
  not_configured: { label: 'Not Configured', bg: 'rgba(100, 116, 139, 0.15)', color: '#94a3b8', border: 'rgba(100, 116, 139, 0.3)', dotColor: '#64748b' },
  error: { label: 'Connection Error', bg: 'rgba(239, 68, 68, 0.12)', color: '#f87171', border: 'rgba(239, 68, 68, 0.3)', dotColor: '#ef4444' },
  disabled: { label: 'Disabled', bg: 'rgba(100, 116, 139, 0.15)', color: '#94a3b8', border: 'rgba(100, 116, 139, 0.3)', dotColor: '#64748b' },
};

export const INVOICE_STATUSES: Record<string, StatusVisual> = {
  paid: { label: 'Paid', bg: 'rgba(37, 211, 102, 0.12)', color: '#52bb89', border: 'rgba(82, 187, 137, 0.3)' },
  pending: { label: 'Pending', bg: 'rgba(245, 158, 11, 0.12)', color: '#fbbf24', border: 'rgba(245, 158, 11, 0.3)' },
  failed: { label: 'Failed', bg: 'rgba(239, 68, 68, 0.12)', color: '#f87171', border: 'rgba(239, 68, 68, 0.3)' },
  refunded: { label: 'Refunded', bg: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: 'rgba(168, 85, 247, 0.3)' },
};

