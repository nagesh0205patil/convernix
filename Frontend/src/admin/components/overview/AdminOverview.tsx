import React from 'react';
import {
  MessageSquare,
  Users,
  CreditCard,
  ShieldCheck,
  Plus,
  ArrowUpRight,
} from 'lucide-react';
import { AdminPageHeader } from '../common/AdminPageHeader';
import { MetricCard } from '../common/MetricCard';
import { StatusBadge } from '../common/StatusBadge';
import { SetupChecklist } from './SetupChecklist';
import { WorkspaceReadyBanner } from './WorkspaceReadyBanner';
import type {
  AdminSection,
  AdminSubTab,
  AuditLogEntry,
  OnboardingStepItem,
  SubscriptionPlanInfo,
  WhatsAppConnectionState,
  AdminUser,
} from '../../types';

interface AdminOverviewProps {
  tenant: any;
  user: any;
  whatsapp: WhatsAppConnectionState;
  users: AdminUser[];
  subscription: SubscriptionPlanInfo;
  auditLogs: AuditLogEntry[];
  onboarding: { steps: OnboardingStepItem[]; completion_percentage: number; is_ready: boolean };
  onNavigate: (section: AdminSection, subTab?: AdminSubTab) => void;
  onOpenInviteModal: () => void;
  onOpenInbox?: () => void;
}

export function AdminOverview({
  tenant,
  user: _user,
  whatsapp,
  users,
  subscription,
  auditLogs,
  onboarding,
  onNavigate,
  onOpenInviteModal,
  onOpenInbox,
}: AdminOverviewProps) {
  const activeUsersCount = users.filter((u) => u.status === 'Active').length;
  const pendingUsersCount = users.filter((u) => u.status === 'Invited').length;
  const isConnected = whatsapp.connection_status === 'connected';

  return (
    <div className="pm-overview-page">
      <AdminPageHeader
        title="Administration"
        subtitle={`Manage ${tenant?.organization_name || 'organization'} settings, WhatsApp integration, users, security, permissions, and billing.`}
        actions={
          <button type="button" className="pm-primary-btn" onClick={onOpenInviteModal}>
            <Plus size={14} /> Invite User
          </button>
        }
      />

      {/* Onboarding progress vs Workspace Ready */}
      {onboarding.is_ready || onboarding.completion_percentage === 100 ? (
        <WorkspaceReadyBanner onNavigate={onNavigate} onOpenInbox={onOpenInbox} />
      ) : (
        <SetupChecklist
          steps={onboarding.steps}
          completionPercentage={onboarding.completion_percentage}
          onNavigate={onNavigate}
        />
      )}

      {/* Enterprise Summary Cards */}
      <div className="pm-admin-cards-grid">
        {/* WhatsApp Connection */}
        <MetricCard
          title="WhatsApp Connection"
          icon={MessageSquare}
          value={
            <div className="pm-card-status-row">
              <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
              <StatusBadge
                status={whatsapp.connection_status}
                type="whatsapp"
                labelOverride={isConnected ? 'Live Channel' : 'Disconnected'}
              />
            </div>
          }
          meta={`${whatsapp.business_name} · ${whatsapp.phone_number || 'No number connected'}`}
          info={`WABA: ${whatsapp.business_account_id || 'Pending'} · Webhook: ${whatsapp.webhook_status} · Last sync: ${whatsapp.last_sync}`}
          actionLabel="Manage Configuration"
          onAction={() => onNavigate('settings', 'whatsapp')}
        />

        {/* Team Members */}
        <MetricCard
          title="Team Members"
          icon={Users}
          value={`${activeUsersCount} Active Users`}
          meta={`${pendingUsersCount} Pending Invitation${pendingUsersCount === 1 ? '' : 's'}`}
          info="Managed with least-privilege role policies and team queues"
          actionLabel="Manage Users"
          onAction={() => onNavigate('iam', 'users')}
        />

        {/* Subscription */}
        <MetricCard
          title="Subscription"
          icon={CreditCard}
          value={`${subscription.plan_name} Plan`}
          meta={`Next billing date: ${subscription.renewal_date}`}
          info={`${subscription.price} · ${subscription.seats_included} seats included · ${subscription.allowance_conversations}`}
          actionLabel="Manage Subscription"
          onAction={() => onNavigate('account', 'subscription')}
        />

        {/* Security */}
        <MetricCard
          title="Security"
          icon={ShieldCheck}
          value="MFA Enforced"
          meta="Password policy compliant"
          info="2 active sessions · Last security review: 14 September 2026"
          actionLabel="Security Settings"
          onAction={() => onNavigate('settings', 'security')}
        />
      </div>

      {/* Recent Administrative Activity */}
      <div className="pm-admin-recent-activity">
        <div className="pm-section-head-pro">
          <div>
            <h3>Recent Administrative Activity</h3>
            <p>Auditable actions executed by organization operators and system services</p>
          </div>
          <button
            type="button"
            className="pm-secondary-btn small"
            onClick={() => onNavigate('audit')}
          >
            View All Audit Logs <ArrowUpRight size={12} />
          </button>
        </div>

        <div className="pm-table-scroll">
          <table className="pm-enterprise-table compact">
            <thead>
              <tr>
                <th scope="col">Actor</th>
                <th scope="col">Action</th>
                <th scope="col">Resource</th>
                <th scope="col">Date/Time</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.slice(0, 5).map((log) => (
                <tr key={log.id}>
                  <td>
                    <strong>{log.actor_name}</strong>
                  </td>
                  <td>{log.action}</td>
                  <td>
                    <code>{log.resource}</code>
                  </td>
                  <td>{log.created_at}</td>
                  <td>
                    <StatusBadge status={log.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

