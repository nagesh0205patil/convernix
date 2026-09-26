import React from 'react';
import type { IAMTab } from '../../types';

interface IAMShellProps {
  activeTab: IAMTab;
  onTabChange: (tab: IAMTab) => void;
  children: React.ReactNode;
}

export function IAMShell({ activeTab, onTabChange, children }: IAMShellProps) {
  const tabs: { key: IAMTab; label: string }[] = [
    { key: 'users', label: 'Users' },
    { key: 'roles', label: 'Roles' },
    { key: 'departments', label: 'Departments & Routing' },
    { key: 'policies', label: 'Permission Policies' },
  ];

  return (
    <div className="pm-module-shell">
      <nav className="pm-subtab-nav" aria-label="IAM sections">
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

