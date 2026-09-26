import React from 'react';
import type { AccountTab } from '../../types';

interface AccountShellProps {
  activeTab: AccountTab;
  onTabChange: (tab: AccountTab) => void;
  children: React.ReactNode;
}

export function AccountShell({ activeTab, onTabChange, children }: AccountShellProps) {
  const tabs: { key: AccountTab; label: string }[] = [
    { key: 'subscription', label: 'Subscription' },
    { key: 'billing', label: 'Billing Details' },
    { key: 'payment-methods', label: 'Payment Methods' },
    { key: 'invoices', label: 'Invoices' },
    { key: 'usage', label: 'Usage' },
  ];

  return (
    <div className="pm-module-shell">
      <nav className="pm-subtab-nav" aria-label="Account sections">
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

