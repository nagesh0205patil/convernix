import React from 'react';
import {
  ChevronRight,
  ArrowLeft,
  Building2,
  ChevronLeft,
} from 'lucide-react';
import type { AdminSection, AdminSubTab, OrganizationProfileInfo } from '../../types';
import { ADMIN_NAV_SECTIONS } from '../../constants/navigation';

interface AdminSidebarProps {
  activeSection: AdminSection;
  activeSubTab: AdminSubTab;
  onNavigate: (section: AdminSection, subTab?: AdminSubTab) => void;
  orgProfile: OrganizationProfileInfo;
  onBackToApp?: () => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export function AdminSidebar({
  activeSection,
  activeSubTab,
  onNavigate,
  orgProfile,
  onBackToApp,
  collapsed,
  onToggleCollapse,
}: AdminSidebarProps) {
  return (
    <aside
      className={`pm-admin-sidebar ${collapsed ? 'collapsed' : ''}`}
      aria-label="Administration Navigation"
    >
      {/* Sidebar Header / Org Identifier */}
      <div className="pm-sidebar-header">
        <div className="pm-sidebar-org-wrap">
          <div className="pm-sidebar-org-avatar">
            {orgProfile.logo_url ? (
              <img src={orgProfile.logo_url} alt={orgProfile.name} className="pm-sidebar-logo-img" />
            ) : (
              <Building2 size={18} />
            )}
          </div>
          {!collapsed && (
            <div className="pm-sidebar-org-text">
              <div className="pm-sidebar-org-name" title={orgProfile.name}>
                {orgProfile.name || 'Convernix Admin'}
              </div>
              <div className="pm-sidebar-org-sub">Cloudtronix Enterprise</div>
            </div>
          )}
        </div>
        <button
          type="button"
          className="pm-sidebar-toggle-btn"
          onClick={onToggleCollapse}
          title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          aria-label={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      {/* Return to Workspace Quick Link */}
      {onBackToApp && (
        <div className="pm-sidebar-back-wrap">
          <button
            type="button"
            className="pm-sidebar-back-btn"
            onClick={onBackToApp}
            title="Return to Communication Hub"
          >
            <ArrowLeft size={15} />
            {!collapsed && <span>Return to Workspace</span>}
          </button>
        </div>
      )}

      {/* Main Navigation List */}
      <nav className="pm-sidebar-nav" aria-label="Admin Navigation Menu">
        {ADMIN_NAV_SECTIONS.map((section) => {
          const Icon = section.icon;
          const isActive = activeSection === section.key;

          return (
            <div key={section.key} className="pm-sidebar-group">
              <button
                type="button"
                className={`pm-sidebar-item ${isActive ? 'active' : ''}`}
                onClick={() => {
                  const defaultTab = section.defaultSubTab as AdminSubTab;
                  onNavigate(section.key, defaultTab);
                }}
                aria-current={isActive ? 'page' : undefined}
                title={section.label}
              >
                <Icon size={18} className="pm-sidebar-icon" />
                {!collapsed && <span className="pm-sidebar-label">{section.label}</span>}
              </button>

              {/* Subtabs if active and expanded */}
              {!collapsed && isActive && section.subTabs && section.subTabs.length > 0 && (
                <div className="pm-sidebar-subnav">
                  {section.subTabs.map((sub) => {
                    const isSubActive = activeSubTab === sub.key;
                    return (
                      <button
                        key={sub.key}
                        type="button"
                        className={`pm-sidebar-subitem ${isSubActive ? 'active' : ''}`}
                        onClick={() => onNavigate(section.key, sub.key as AdminSubTab)}
                        aria-current={isSubActive ? 'location' : undefined}
                      >
                        <span className="pm-sidebar-bullet" />
                        <span className="pm-sidebar-sublabel">{sub.label}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* Footer / System Status */}
      <div className="pm-sidebar-footer">
        {!collapsed ? (
          <div className="pm-sidebar-system-info">
            <div className="pm-sidebar-badge-row">
              <span className="pm-status-dot online" />
              <span className="pm-sidebar-sys-status">API Connected</span>
            </div>
            <div className="pm-sidebar-version">v2.4.0 · Cloudtronix SaaS</div>
          </div>
        ) : (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '8px 0' }}>
            <span className="pm-status-dot online" title="API Connected" />
          </div>
        )}
      </div>
    </aside>
  );
}

