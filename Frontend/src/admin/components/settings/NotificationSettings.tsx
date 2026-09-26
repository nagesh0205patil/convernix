import React, { useState } from 'react';
import { Bell, Mail, ShieldAlert, CreditCard, MessageSquare, Server, Users, Send } from 'lucide-react';
import { AdminPageHeader } from '../common/AdminPageHeader';
import type { NotificationPreferences } from '../../types';

interface NotificationSettingsProps {
  preferences: NotificationPreferences;
  onSave: (data: Partial<NotificationPreferences>) => Promise<boolean>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export function NotificationSettings({ preferences, onSave, toast }: NotificationSettingsProps) {
  const [prefs, setPrefs] = useState<NotificationPreferences>(preferences);
  const [saving, setSaving] = useState(false);

  const categories = [
    {
      key: 'security',
      label: 'Security Alerts',
      desc: 'Suspicious logins, password changes, and elevated privilege alterations',
      icon: ShieldAlert,
      emailKey: 'security_email' as const,
      inappKey: 'security_inapp' as const,
    },
    {
      key: 'billing',
      label: 'Billing Alerts',
      desc: 'Invoice generation, successful renewals, and payment failure notifications',
      icon: CreditCard,
      emailKey: 'billing_email' as const,
      inappKey: 'billing_inapp' as const,
    },
    {
      key: 'whatsapp',
      label: 'WhatsApp Connection Alerts',
      desc: 'Token expiration warnings, webhook delivery drop-offs, and quality rating dips',
      icon: MessageSquare,
      emailKey: 'whatsapp_email' as const,
      inappKey: 'whatsapp_inapp' as const,
    },
    {
      key: 'system',
      label: 'System Alerts',
      desc: 'Scheduled maintenance, incident reports, and regional Cloud API latency updates',
      icon: Server,
      emailKey: 'system_email' as const,
      inappKey: 'system_inapp' as const,
    },
    {
      key: 'user',
      label: 'User Management Alerts',
      desc: 'Team invitations accepted, password resets, and user deactivations',
      icon: Users,
      emailKey: 'user_management_email' as const,
      inappKey: 'user_management_inapp' as const,
    },
    {
      key: 'campaign',
      label: 'Campaign Alerts',
      desc: 'Broadcast completion telemetry, high opt-out flags, and delivery thresholds',
      icon: Send,
      emailKey: 'campaign_email' as const,
      inappKey: 'campaign_inapp' as const,
    },
  ];

  const handleToggle = (key: keyof NotificationPreferences) => {
    setPrefs((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSave = async () => {
    setSaving(true);
    const ok = await onSave(prefs);
    setSaving(false);
    if (ok) {
      toast('Notification preferences saved successfully.', 'success');
    }
  };

  return (
    <div className="pm-settings-panel">
      <AdminPageHeader
        breadcrumbs={[
          { label: 'Administration' },
          { label: 'Settings' },
          { label: 'Notifications' },
        ]}
        title="Notification Settings"
        subtitle="Configure real-time administrator notification channels across security, billing, WhatsApp health, and campaigns."
        actions={
          <button
            type="button"
            className="pm-primary-btn"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Preferences'}
          </button>
        }
      />

      <div className="pm-info-card">
        <div className="pm-notification-table-header">
          <span>Alert Category</span>
          <div className="pm-channel-columns">
            <span>Email</span>
            <span>In-App</span>
          </div>
        </div>

        <div className="pm-notification-categories-list">
          {categories.map((cat) => {
            const Icon = cat.icon;
            const emailActive = prefs[cat.emailKey];
            const inappActive = prefs[cat.inappKey];

            return (
              <div key={cat.key} className="pm-notification-row-pro">
                <div className="pm-notif-info-col">
                  <div className="pm-notif-icon">
                    <Icon size={16} />
                  </div>
                  <div>
                    <strong>{cat.label}</strong>
                    <p>{cat.desc}</p>
                  </div>
                </div>

                <div className="pm-channel-columns">
                  <label className="pm-checkbox-label">
                    <input
                      type="checkbox"
                      checked={emailActive}
                      onChange={() => handleToggle(cat.emailKey)}
                    />
                    <span className="sr-only">Email for {cat.label}</span>
                  </label>

                  <label className="pm-checkbox-label">
                    <input
                      type="checkbox"
                      checked={inappActive}
                      onChange={() => handleToggle(cat.inappKey)}
                    />
                    <span className="sr-only">In-App for {cat.label}</span>
                  </label>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

