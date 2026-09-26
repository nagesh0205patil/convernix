import React from 'react';
import type { SettingsTab } from '../../types';

interface SettingsShellProps {
  activeTab: SettingsTab;
  onTabChange: (tab: SettingsTab) => void;
  children: React.ReactNode;
}

export function SettingsShell({ activeTab, onTabChange, children }: SettingsShellProps) {
  const tabs: { key: SettingsTab; label: string }[] = [
    { key: 'organization', label: 'Organization Profile' },
    { key: 'whatsapp', label: 'WhatsApp Configuration' },
    { key: 'templates', label: 'Notification Templates' },
    { key: 'security', label: 'Security & API Keys' },
    { key: 'notifications', label: 'Notifications' },
    { key: 'integrations', label: 'Integrations' },
  ];

  return (
    <div className="pm-module-shell">
      <nav className="pm-subtab-nav" aria-label="Settings sections">
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            className={`pm-subtab-btn ${activeTab === t.key ? 'active' : ''}`}
            onClick={() => onTabChange(t.key)}
            aria-current={activeTab === t.key ? 'page' : undefined}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <div className="pm-module-content">{children}</div>
    </div>
  );
}

