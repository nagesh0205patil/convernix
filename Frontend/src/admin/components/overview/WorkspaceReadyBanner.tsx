import React from 'react';
import { CheckCircle2, MessageSquare, Plus, ArrowRight } from 'lucide-react';
import type { AdminSection, AdminSubTab } from '../../types';

interface WorkspaceReadyBannerProps {
  onNavigate: (section: AdminSection, subTab?: AdminSubTab) => void;
  onOpenInbox?: () => void;
}

export function WorkspaceReadyBanner({ onNavigate, onOpenInbox }: WorkspaceReadyBannerProps) {
  return (
    <div className="pm-workspace-ready-card" role="region" aria-label="Workspace Status">
      <div className="pm-ready-top">
        <div className="pm-ready-icon-wrap" aria-hidden="true">
          <CheckCircle2 size={24} color="#25d366" />
        </div>
        <div className="pm-ready-copy">
          <span className="pm-ready-badge">Production Ready</span>
          <h2>Your workspace is ready</h2>
          <p>
            Your organization profile, WhatsApp Business connection, team access policies, and billing credentials
            are verified and actively routing live customer inquiries.
          </p>
        </div>
      </div>

      <div className="pm-ready-actions">
        {onOpenInbox && (
          <button type="button" className="pm-primary-btn" onClick={onOpenInbox}>
            <MessageSquare size={14} /> Open Team Inbox
          </button>
        )}
        <button
          type="button"
          className="pm-secondary-btn"
          onClick={() => onNavigate('iam', 'users')}
        >
          <Plus size={14} /> Invite Team Members
        </button>
        <button
          type="button"
          className="pm-secondary-btn"
          onClick={() => onNavigate('settings', 'whatsapp')}
        >
          View Channel Status <ArrowRight size={13} />
        </button>
      </div>
    </div>
  );
}

