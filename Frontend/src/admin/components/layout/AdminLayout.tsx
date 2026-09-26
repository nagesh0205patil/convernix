import React, { useState } from 'react';
import { AdminSidebar } from './AdminSidebar';
import { Breadcrumbs } from '../common/Breadcrumbs';
import type { AdminSection, AdminSubTab, OrganizationProfileInfo, UserInfo } from '../../types';
import { ADMIN_NAV_SECTIONS } from '../../constants/navigation';
import { Menu, X, Shield, HelpCircle } from 'lucide-react';

interface AdminLayoutProps {
  activeSection: AdminSection;
  activeSubTab: AdminSubTab;
  onNavigate: (section: AdminSection, subTab?: AdminSubTab) => void;
  orgProfile: OrganizationProfileInfo;
  currentUser?: UserInfo | null;
  onBackToApp?: () => void;
  children: React.ReactNode;
}

export function AdminLayout({
  activeSection,
  activeSubTab,
  onNavigate,
  orgProfile,
  currentUser,
  onBackToApp,
  children,
}: AdminLayoutProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Generate breadcrumb items
  const currentSectionConfig = ADMIN_NAV_SECTIONS.find((s) => s.key === activeSection);
  const currentSubTabConfig = currentSectionConfig?.subTabs?.find((sub) => sub.key === activeSubTab);

  const breadcrumbs = [
    { label: 'Admin Console', onClick: () => onNavigate('overview') },
    {
      label: currentSectionConfig ? currentSectionConfig.label : activeSection,
      onClick:
        currentSectionConfig?.defaultSubTab
          ? () => onNavigate(activeSection, currentSectionConfig.defaultSubTab as AdminSubTab)
          : undefined,
    },
  ];

  if (currentSubTabConfig && activeSection !== 'overview' && activeSection !== 'audit') {
    breadcrumbs.push({ label: currentSubTabConfig.label });
  }

  return (
    <div className={`pm-admin-root ${mobileOpen ? 'mobile-nav-open' : ''}`}>
      {/* Mobile Drawer Backdrop */}
      {mobileOpen && (
        <div
          className="pm-mobile-backdrop"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <div className={`pm-sidebar-container ${mobileOpen ? 'mobile-visible' : ''}`}>
        <AdminSidebar
          activeSection={activeSection}
          activeSubTab={activeSubTab}
          onNavigate={(sec, sub) => {
            onNavigate(sec, sub);
            setMobileOpen(false);
          }}
          orgProfile={orgProfile}
          onBackToApp={onBackToApp}
          collapsed={collapsed}
          onToggleCollapse={() => setCollapsed(!collapsed)}
        />
      </div>

      {/* Main Content Area */}
      <div className="pm-admin-main">
        {/* Top Navbar */}
        <header className="pm-admin-topbar">
          <div className="pm-topbar-left">
            <button
              type="button"
              className="pm-mobile-menu-btn"
              onClick={() => setMobileOpen(!mobileOpen)}
              aria-label="Toggle navigation menu"
            >
              {mobileOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
            <Breadcrumbs items={breadcrumbs} />
          </div>

          <div className="pm-topbar-right">
            <div className="pm-topbar-role-badge">
              <Shield size={13} style={{ color: 'var(--pm-primary)' }} />
              <span>Tenant Admin</span>
            </div>

            <a
              href="https://developers.facebook.com/docs/whatsapp"
              target="_blank"
              rel="noopener noreferrer"
              className="pm-topbar-help-link"
              title="Meta WhatsApp Business API Documentation"
            >
              <HelpCircle size={15} />
              <span className="pm-topbar-help-text">Docs</span>
            </a>

            {currentUser && (
              <div className="pm-topbar-user" title={`${currentUser.name} (${currentUser.email})`}>
                <div className="pm-topbar-user-avatar">
                  {currentUser.name ? currentUser.name.charAt(0).toUpperCase() : 'U'}
                </div>
                <span className="pm-topbar-user-name">{currentUser.name}</span>
              </div>
            )}
          </div>
        </header>

        {/* Scrollable Content Container */}
        <main className="pm-admin-body" id="admin-main-content">
          <div className="pm-admin-inner">{children}</div>
        </main>
      </div>
    </div>
  );
}
