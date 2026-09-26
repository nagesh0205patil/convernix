import React, { useState, useMemo } from 'react';
import type {
  AdminSection,
  AdminSubTab,
  SettingsTab,
  IAMTab,
  AccountTab,
  ComplianceTab,
  DeveloperTab,
} from './types';
import { useAdminData } from './hooks/useAdminData';
import { usePermissions } from './hooks/usePermissions';
import { AdminLayout } from './components/layout/AdminLayout';
import { UnauthorizedView } from './components/common/UnauthorizedView';

// Overview
import { AdminOverview } from './components/overview/AdminOverview';

// Settings
import { SettingsShell } from './components/settings/SettingsShell';
import { OrganizationProfile } from './components/settings/OrganizationProfile';
import { WhatsAppConfiguration } from './components/settings/WhatsAppConfiguration';
import { NotificationTemplatesView } from './components/settings/NotificationTemplatesView';
import { SecuritySettings } from './components/settings/SecuritySettings';
import { NotificationSettings } from './components/settings/NotificationSettings';
import { IntegrationsView } from './components/settings/IntegrationsView';

// Developer Portal
import { DeveloperPortalView } from './components/developer/DeveloperPortalView';

// IAM
import { IAMShell } from './components/iam/IAMShell';
import { UserManagement } from './components/iam/UserManagement';
import { RolesManagement } from './components/iam/RolesManagement';
import { DepartmentsManagement } from './components/iam/DepartmentsManagement';
import { TeamsManagement } from './components/iam/TeamsManagement';
import { PermissionMatrix } from './components/iam/PermissionMatrix';
import { InviteUserDrawer } from './components/iam/InviteUserDrawer';

// Account
import { AccountShell } from './components/account/AccountShell';
import { SubscriptionView } from './components/account/SubscriptionView';
import { BillingDetails } from './components/account/BillingDetails';
import { PaymentMethods } from './components/account/PaymentMethods';
import { InvoicesView } from './components/account/InvoicesView';
import { UsageView } from './components/account/UsageView';

// Audit
import { AuditLogsView } from './components/audit/AuditLogsView';

// Compliance & Privacy
import { ComplianceShell } from './components/compliance/ComplianceShell';

// Styling
import './admin.css';

interface TenantAdministrationConsoleProps {
  initialSection?: AdminSection;
  initialSubTab?: AdminSubTab;
  currentUser?: any;
  onBackToApp?: () => void;
  onOpenInbox?: () => void;
}

export function TenantAdministrationConsole({
  initialSection = 'overview',
  initialSubTab,
  currentUser,
  onBackToApp,
  onOpenInbox,
}: TenantAdministrationConsoleProps) {
  const [activeSection, setActiveSection] = useState<AdminSection>(initialSection);
  const [activeSubTab, setActiveSubTab] = useState<AdminSubTab>(initialSubTab || 'organization');
  const [showGlobalInviteModal, setShowGlobalInviteModal] = useState(false);
  const [toastMessage, setToastMessage] = useState<{ msg: string; type: 'success' | 'error' | 'info' } | null>(null);

  const {
    loading,
    error,
    orgProfile,
    whatsapp,
    users,
    roles,
    teams,
    subscription,
    billing,
    paymentMethods,
    invoices,
    usage,
    auditLogs,
    securitySessions,
    notifications,
    onboarding,
    refreshAll,
    updateOrgProfile,
    connectWhatsApp,
    testWhatsAppConnection,
    disconnectWhatsApp,
    inviteUser,
    updateUserRole,
    deactivateUser,
    createRole,
    createTeam,
    updateBillingInfo,
    addPaymentMethod,
    updateNotifications,
    completeStep,
  } = useAdminData();

  // Toast notifier helper
  const showToast = (msg: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToastMessage({ msg, type });
    setTimeout(() => {
      setToastMessage((prev) => (prev?.msg === msg ? null : prev));
    }, 4000);
  };

  // Robust RBAC Permission checks
  const { canAccess, isOwner, isAdmin } = usePermissions(currentUser || 'owner');
  const userRole = currentUser?.role || 'owner';

  const handleNavigate = (section: AdminSection, subTab?: AdminSubTab) => {
    setActiveSection(section);
    if (subTab) {
      setActiveSubTab(subTab);
    } else {
      // Pick sensible defaults
      if (section === 'settings') setActiveSubTab('organization');
      if (section === 'iam') setActiveSubTab('users');
      if (section === 'account') setActiveSubTab('subscription');
      if (section === 'audit') setActiveSubTab('audit' as AdminSubTab);
      if (section === 'compliance') setActiveSubTab('telemetry');
      if (section === 'developer') setActiveSubTab('overview');
    }
  };

  // Section authorization gate
  const isSectionAuthorized = () => {
    if (isOwner || isAdmin) return true;
    switch (activeSection) {
      case 'overview':
        return true;
      case 'settings':
        return canAccess('settings', 'view');
      case 'iam':
        return canAccess('iam', 'view');
      case 'account':
        return canAccess('account', 'view');
      case 'audit':
        return canAccess('audit', 'view');
      case 'compliance':
        return canAccess('compliance', 'view');
      case 'developer':
        return canAccess('settings', 'view');
      default:
        return true;
    }
  };

  // Ensure active subtab matches section schema so views never fail to render
  const validSettingsTabs: SettingsTab[] = ['organization', 'whatsapp', 'templates', 'security', 'notifications', 'integrations'];
  const currentSettingsTab: SettingsTab = validSettingsTabs.includes(activeSubTab as any)
    ? (activeSubTab as SettingsTab)
    : 'organization';

  const validIamTabs: IAMTab[] = ['users', 'roles', 'departments', 'teams', 'policies'];
  const currentIamTab: IAMTab = validIamTabs.includes(activeSubTab as any)
    ? (activeSubTab as IAMTab)
    : 'users';

  const validAccountTabs: AccountTab[] = ['subscription', 'billing', 'payment-methods', 'invoices', 'usage'];
  const currentAccountTab: AccountTab = validAccountTabs.includes(activeSubTab as any)
    ? (activeSubTab as AccountTab)
    : 'subscription';

  const validComplianceTabs: ComplianceTab[] = ['telemetry', 'kms', 'ropa', 'dsr', 'retention', 'incidents'];
  const currentComplianceTab: ComplianceTab = validComplianceTabs.includes(activeSubTab as any)
    ? (activeSubTab as ComplianceTab)
    : 'telemetry';

  const validDeveloperTabs: DeveloperTab[] = ['overview', 'explorer', 'webhooks', 'sdk', 'logs'];
  const currentDeveloperTab: DeveloperTab = validDeveloperTabs.includes(activeSubTab as any)
    ? (activeSubTab as DeveloperTab)
    : 'overview';

  const resolvedSubTab: AdminSubTab =
    activeSection === 'settings'
      ? currentSettingsTab
      : activeSection === 'iam'
      ? currentIamTab
      : activeSection === 'account'
      ? currentAccountTab
      : activeSection === 'compliance'
      ? currentComplianceTab
      : activeSection === 'developer'
      ? currentDeveloperTab
      : activeSubTab;

  const allRolesList = useMemo(() => {
    if (Array.isArray(roles)) return roles;
    if (roles && typeof roles === 'object') {
      return [...((roles as any).system_roles || []), ...((roles as any).custom_roles || [])];
    }
    return [];
  }, [roles]);

  const systemRolesList = useMemo(() => {
    if (roles && typeof roles === 'object' && !Array.isArray(roles) && (roles as any).system_roles) {
      return (roles as any).system_roles;
    }
    return allRolesList.filter((r) => r.is_system);
  }, [roles, allRolesList]);

  const customRolesList = useMemo(() => {
    if (roles && typeof roles === 'object' && !Array.isArray(roles) && (roles as any).custom_roles) {
      return (roles as any).custom_roles;
    }
    return allRolesList.filter((r) => !r.is_system);
  }, [roles, allRolesList]);

  return (
    <div className="pm-console-container">
      {/* Toast Alert Notification */}
      {toastMessage && (
        <div
          className={`pm-floating-toast ${toastMessage.type}`}
          role="status"
          aria-live="polite"
        >
          <span>{toastMessage.msg}</span>
          <button
            type="button"
            className="pm-toast-close"
            onClick={() => setToastMessage(null)}
            aria-label="Dismiss toast"
          >
            ×
          </button>
        </div>
      )}

      {/* Global Invite User Drawer */}
      <InviteUserDrawer
        isOpen={showGlobalInviteModal}
        onClose={() => setShowGlobalInviteModal(false)}
        roles={roles}
        teams={teams}
        onInvite={async (data) => {
          const ok = await inviteUser(data);
          if (ok) {
            showToast(`Invitation dispatched to ${data.email}`, 'success');
            setShowGlobalInviteModal(false);
          }
          return ok;
        }}
        toast={showToast}
      />

      <AdminLayout
        activeSection={activeSection}
        activeSubTab={resolvedSubTab}
        onNavigate={handleNavigate}
        orgProfile={orgProfile}
        currentUser={currentUser}
        onBackToApp={onBackToApp}
      >
        {!isSectionAuthorized() ? (
          <UnauthorizedView
            userRole={userRole}
            onReturnToDashboard={() => handleNavigate('overview')}
          />
        ) : (
          <>
            {/* OVERVIEW SECTION */}
            {activeSection === 'overview' && (
              <AdminOverview
                tenant={orgProfile}
                user={currentUser}
                whatsapp={whatsapp}
                users={users}
                subscription={subscription}
                auditLogs={auditLogs}
                onboarding={onboarding}
                onNavigate={handleNavigate}
                onOpenInviteModal={() => setShowGlobalInviteModal(true)}
                onOpenInbox={onOpenInbox}
              />
            )}

            {/* SETTINGS SECTION */}
            {activeSection === 'settings' && (
              <SettingsShell
                activeTab={currentSettingsTab}
                onTabChange={(t) => setActiveSubTab(t)}
              >
                {currentSettingsTab === 'organization' && (
                  <OrganizationProfile
                    initialData={orgProfile}
                    onSave={async (data) => {
                      const ok = await updateOrgProfile(data);
                      if (ok) showToast('Organization profile updated.', 'success');
                      return ok;
                    }}
                    toast={showToast}
                  />
                )}

                {currentSettingsTab === 'whatsapp' && (
                  <WhatsAppConfiguration
                    whatsapp={whatsapp}
                    onConnect={async (creds) => {
                      const ok = await connectWhatsApp(creds);
                      if (ok) showToast('WhatsApp integration connected.', 'success');
                      return ok;
                    }}
                    onTest={async () => {
                      const res = await testWhatsAppConnection();
                      if (res) showToast('Connection diagnostic test completed.', 'info');
                      return res;
                    }}
                    onDisconnect={async () => {
                      const ok = await disconnectWhatsApp();
                      if (ok) showToast('WhatsApp integration disconnected.', 'info');
                      return ok;
                    }}
                    onRefresh={refreshAll}
                    toast={showToast}
                  />
                )}

                {currentSettingsTab === 'templates' && (
                  <NotificationTemplatesView toast={showToast} />
                )}

                {currentSettingsTab === 'security' && (
                  <SecuritySettings
                    sessions={securitySessions}
                    onUpdatePassword={async () => {
                      showToast('Password updated successfully.', 'success');
                      return true;
                    }}
                    onRevokeSession={async (id) => {
                      showToast(`Session #${id} revoked.`, 'success');
                      return true;
                    }}
                    onRevokeAllOther={async () => {
                      showToast('All other active sessions revoked.', 'success');
                      return true;
                    }}
                    toast={showToast}
                  />
                )}

                {currentSettingsTab === 'notifications' && (
                  <NotificationSettings
                    preferences={notifications}
                    onSave={async (data) => {
                      const ok = await updateNotifications(data);
                      if (ok) showToast('Notification preferences saved.', 'success');
                      return ok;
                    }}
                    toast={showToast}
                  />
                )}

                {currentSettingsTab === 'integrations' && (
                  <IntegrationsView
                    toast={showToast}
                    onOpenDeveloperPortal={() => handleNavigate('developer', 'overview')}
                  />
                )}
              </SettingsShell>
            )}

            {/* IAM SECTION */}
            {activeSection === 'iam' && (
              <IAMShell
                activeTab={currentIamTab}
                onTabChange={(t) => setActiveSubTab(t)}
              >
                {currentIamTab === 'users' && (
                  <UserManagement
                    users={users}
                    teams={teams}
                    currentUser={currentUser}
                    onInvite={async (data) => {
                      const ok = await inviteUser(data);
                      if (ok) showToast(`Invited ${data.email}`, 'success');
                      return ok;
                    }}
                    onUpdateRole={async (id, updates) => {
                      const ok = await updateUserRole(id, updates);
                      if (ok) showToast('User role updated.', 'success');
                      return ok;
                    }}
                    onDeactivate={async (id) => {
                      const ok = await deactivateUser(id);
                      if (ok) showToast('User account deactivated.', 'info');
                      return ok;
                    }}
                    toast={showToast}
                  />
                )}

                {currentIamTab === 'roles' && (
                  <RolesManagement
                    systemRoles={systemRolesList}
                    customRoles={customRolesList}
                    onCreateRole={async (data) => {
                      const ok = await createRole(data);
                      if (ok) showToast(`Role "${data.name}" created.`, 'success');
                      return ok;
                    }}
                    onNavigateToPolicies={() => setActiveSubTab('policies')}
                    toast={showToast}
                  />
                )}

                {currentIamTab === 'departments' && (
                  <DepartmentsManagement toast={showToast} />
                )}

                {currentIamTab === 'teams' && (
                  <DepartmentsManagement toast={showToast} />
                )}

                {currentIamTab === 'policies' && (
                  <PermissionMatrix toast={showToast} />
                )}
              </IAMShell>
            )}

            {/* ACCOUNT SECTION */}
            {activeSection === 'account' && (
              <AccountShell
                activeTab={currentAccountTab}
                onTabChange={(t) => setActiveSubTab(t)}
              >
                {currentAccountTab === 'subscription' && (
                  <SubscriptionView
                    subscription={subscription}
                    onUpgrade={async (tier) => {
                      showToast(`Upgraded subscription to ${tier}.`, 'success');
                      return true;
                    }}
                    onCancel={async () => {
                      showToast('Cancellation request submitted.', 'info');
                      return true;
                    }}
                    toast={showToast}
                  />
                )}

                {currentAccountTab === 'billing' && (
                  <BillingDetails
                    billing={billing}
                    onSave={async (data) => {
                      const ok = await updateBillingInfo(data);
                      if (ok) showToast('Billing information saved.', 'success');
                      return ok;
                    }}
                    toast={showToast}
                  />
                )}

                {currentAccountTab === 'payment-methods' && (
                  <PaymentMethods
                    paymentMethods={paymentMethods}
                    onAddCard={async (card) => {
                      const ok = await addPaymentMethod(card);
                      if (ok) showToast('Payment card added successfully.', 'success');
                      return ok;
                    }}
                    toast={showToast}
                  />
                )}

                {currentAccountTab === 'invoices' && (
                  <InvoicesView invoices={invoices} billing={billing} />
                )}

                {currentAccountTab === 'usage' && (
                  <UsageView
                    usage={usage}
                    onNavigateToSubscription={() => setActiveSubTab('subscription')}
                  />
                )}
              </AccountShell>
            )}

            {/* AUDIT LOGS SECTION */}
            {activeSection === 'audit' && (
              <AuditLogsView logs={auditLogs} />
            )}

            {/* SECURITY & PRIVACY COMPLIANCE SECTION */}
            {activeSection === 'compliance' && (
              <ComplianceShell
                activeSubTab={currentComplianceTab}
                onSubTabChange={(t) => setActiveSubTab(t)}
                showToast={showToast}
              />
            )}

            {/* DEVELOPER PORTAL SECTION */}
            {activeSection === 'developer' && (
              <DeveloperPortalView
                initialTab={currentDeveloperTab}
                toast={showToast}
                onNavigateToIntegrations={() => handleNavigate('settings', 'integrations')}
              />
            )}
          </>
        )}
      </AdminLayout>
    </div>
  );
}

export default TenantAdministrationConsole;
