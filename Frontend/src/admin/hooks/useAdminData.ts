import { useState, useEffect, useCallback } from 'react';
import { adminApi } from '../services/adminApi';
import type {
  AdminUser,
  AuditLogEntry,
  BillingDetails,
  DiagnosticTestResult,
  InvoiceItem,
  NotificationPreferences,
  OnboardingStepItem,
  OrganizationProfile,
  PaymentCard,
  RoleDefinition,
  SubscriptionPlanInfo,
  TeamDepartment,
  UsageMetricItem,
  UserSessionInfo,
  WhatsAppConnectionState,
} from '../types';

export function useAdminData(tenant: any, toast: (msg: string, type?: 'success' | 'error' | 'info') => void) {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // State slices
  const [orgProfile, setOrgProfile] = useState<OrganizationProfile>({
    organization_name: tenant?.name || 'Cloudtronix Demo Pvt Ltd',
    legal_business_name: 'Cloudtronix Solutions Pvt Ltd',
    org_id: 'ORG-CLD-2048',
    industry: 'Technology',
    business_email: 'hello@cloudtronix.io',
    business_phone: '+91 98765 43210',
    website: 'https://cloudtronix.io',
    country: 'India',
    state: 'Maharashtra',
    city: 'Pune',
    postal_code: '411057',
    timezone: 'Asia/Kolkata',
    default_language: 'English',
    business_address: 'B-204, Blue Ridge Commerce Park, Pune, Maharashtra 411057',
    onboarding_completed: false,
    onboarding_steps: {
      profile: true,
      whatsapp: true,
      invite_team: false,
      roles: false,
      billing: false,
    },
  });

  const [whatsapp, setWhatsapp] = useState<WhatsAppConnectionState>({
    connection_status: 'connected',
    business_name: 'Cloudtronix Support',
    phone_number: '+91 98765 43210',
    business_account_id: 'WB-01-2048',
    phone_number_id: 'PNID_987654321',
    meta_business_account: 'Cloudtronix Meta Business',
    meta_app_id: '89102432890',
    display_name: 'Cloudtronix Support Channel',
    business_verification_status: 'Verified',
    webhook_status: 'Active',
    webhook_url: 'https://convernix.example/api/whatsapp/webhook/',
    last_sync: '2 minutes ago',
    has_access_token: true,
    has_app_secret: true,
    has_verify_token: true,
  });

  const [users, setUsers] = useState<AdminUser[]>([
    { id: 1, name: 'Amit Sharma', email: 'amit@cloudtronix.io', role: 'owner', team: 'Operations', status: 'Active', last_login: 'Today · 09:42', mfa: 'Enabled', created: '2026-09-01' },
    { id: 2, name: 'Neha Patil', email: 'neha@cloudtronix.io', role: 'admin', team: 'Support', status: 'Active', last_login: 'Yesterday · 16:25', mfa: 'Enabled', created: '2026-09-03' },
    { id: 3, name: 'Rahul Verma', email: 'rahul@cloudtronix.io', role: 'agent', team: 'Sales', status: 'Active', last_login: '2 days ago · 11:09', mfa: 'Enabled', created: '2026-09-05' },
    { id: 4, name: 'Support User', email: 'support@cloudtronix.io', role: 'agent', team: 'Support', status: 'Invited', last_login: 'Never', mfa: 'Pending', created: '2026-09-15' },
  ]);

  const [roles, setRoles] = useState<{ system_roles: RoleDefinition[]; custom_roles: RoleDefinition[] }>({
    system_roles: [
      { id: 'owner', name: 'Owner', slug: 'owner', description: 'Full administrative control across the tenant.', is_system: true, user_count: 1 },
      { id: 'admin', name: 'Administrator', slug: 'admin', description: 'Full organization configuration, user management, and WhatsApp setup.', is_system: true, user_count: 1 },
      { id: 'manager', name: 'Manager', slug: 'manager', description: 'Manage conversations, team routing, reports, and agents.', is_system: true, user_count: 0 },
      { id: 'agent', name: 'Agent', slug: 'agent', description: 'Customer conversations, contact lookup, and template usage.', is_system: true, user_count: 2 },
      { id: 'billing_admin', name: 'Billing Administrator', slug: 'billing_admin', description: 'Manage subscription, invoices, payments, and billing profile.', is_system: true, user_count: 0 },
      { id: 'read_only', name: 'Read Only', slug: 'read_only', description: 'View-only access to analytics, audit logs, and directory.', is_system: true, user_count: 0 },
    ],
    custom_roles: [],
  });

  const [teams, setTeams] = useState<TeamDepartment[]>([
    { id: 1, name: 'Sales', slug: 'sales', description: 'Department queue routing and operational ownership for sales workflows.', manager: 'Rahul Verma', members_count: 4, assigned_queues: ['+91 98765 43210 (Sales)'], status: 'Active' },
    { id: 2, name: 'Support', slug: 'support', description: 'Department queue routing and operational ownership for support workflows.', manager: 'Neha Patil', members_count: 6, assigned_queues: ['+91 98765 43210 (Support)'], status: 'Active' },
    { id: 3, name: 'Finance', slug: 'finance', description: 'Department queue routing and operational ownership for finance workflows.', manager: 'Unassigned', members_count: 2, assigned_queues: ['+91 98765 43210 (Finance)'], status: 'Active' },
    { id: 4, name: 'Operations', slug: 'operations', description: 'Department queue routing and operational ownership for operations workflows.', manager: 'Amit Sharma', members_count: 3, assigned_queues: ['+91 98765 43210 (Operations)'], status: 'Active' },
    { id: 5, name: 'Marketing', slug: 'marketing', description: 'Department queue routing and operational ownership for marketing workflows.', manager: 'Unassigned', members_count: 2, assigned_queues: ['+91 98765 43210 (Marketing)'], status: 'Active' },
  ]);

  const [subscription, setSubscription] = useState<SubscriptionPlanInfo>({
    plan_name: 'Professional',
    status: 'Active',
    billing_cycle: 'Monthly',
    price: '₹9,999 / month',
    amount_raw: 9999,
    renewal_date: '20 October 2026',
    seats_included: 10,
    numbers_included: 3,
    allowance_conversations: '25,000 monthly conversations',
  });

  const [billing, setBilling] = useState<BillingDetails>({
    legal_company_name: 'Cloudtronix Solutions Pvt Ltd',
    billing_email: 'billing@cloudtronix.io',
    tax_id: '27AABCC1234D1ZQ',
    country: 'India',
    state: 'Maharashtra',
    city: 'Pune',
    postal_code: '411057',
    address: 'B-204, Blue Ridge Commerce Park, Pune, Maharashtra 411057',
  });

  const [paymentMethods, setPaymentMethods] = useState<PaymentCard[]>([
    { id: 1, card_brand: 'Visa', last4: '4242', exp_month: 12, exp_year: 2029, is_default: true },
  ]);

  const [invoices, setInvoices] = useState<InvoiceItem[]>([
    { id: 1, invoice_number: 'INV-2026-014', billing_period: 'Sep 2026', issue_date: '15 Sep 2026', amount: '₹9,999', currency: 'INR', status: 'paid', payment_method_desc: 'Visa •••• 4242' },
    { id: 2, invoice_number: 'INV-2026-013', billing_period: 'Aug 2026', issue_date: '15 Aug 2026', amount: '₹9,999', currency: 'INR', status: 'paid', payment_method_desc: 'Visa •••• 4242' },
    { id: 3, invoice_number: 'INV-2026-012', billing_period: 'Jul 2026', issue_date: '15 Jul 2026', amount: '₹9,999', currency: 'INR', status: 'paid', payment_method_desc: 'Visa •••• 4242' },
  ]);

  const [usage, setUsage] = useState<{ metrics: UsageMetricItem[]; alerts: string[] }>({
    metrics: [
      { key: 'team_members', label: 'Team Members', used: 8, total: 10, unit: 'seats', percent: 80 },
      { key: 'whatsapp_numbers', label: 'WhatsApp Numbers', used: 2, total: 3, unit: 'numbers', percent: 66 },
      { key: 'conversations', label: 'Monthly Conversations', used: 14250, total: 25000, unit: 'conversations', percent: 57 },
      { key: 'campaigns', label: 'Campaign Messages', used: 40200, total: 100000, unit: 'messages', percent: 40 },
      { key: 'storage', label: 'Storage', used: 2.4, total: 10.0, unit: 'GB', percent: 24 },
    ],
    alerts: ['You have used 80% of your team seats capacity.'],
  });

  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([
    { id: 1, actor_name: 'Amit Sharma', action: 'Invited user', module: 'IAM', resource: 'Support User', ip_address: '10.0.10.42', status: 'Success', created_at: 'Today · 09:42' },
    { id: 2, actor_name: 'Neha Patil', action: 'Role updated', module: 'IAM', resource: 'Operations Manager', ip_address: '10.0.10.18', status: 'Success', created_at: 'Yesterday · 16:25' },
    { id: 3, actor_name: 'System', action: 'WhatsApp number connected', module: 'Settings', resource: '+91 98765 43210', ip_address: '127.0.0.1', status: 'Success', created_at: '2 days ago · 10:18' },
    { id: 4, actor_name: 'Rahul Verma', action: 'Payment method updated', module: 'Account', resource: 'Visa •••• 4242', ip_address: '10.0.10.21', status: 'Success', created_at: '4 days ago · 11:09' },
    { id: 5, actor_name: 'System', action: 'Subscription renewed', module: 'Account', resource: 'Professional Plan', ip_address: '127.0.0.1', status: 'Success', created_at: '7 days ago · 08:31' },
  ]);

  const [securitySessions, setSecuritySessions] = useState<UserSessionInfo[]>([
    { id: 1, device: 'MacBook Pro 16" (macOS Sequoia)', browser: 'Chrome 129.0', location: 'Pune, Maharashtra, India', ip_address: '10.0.2.15', is_current: true, last_active: 'Active now' },
    { id: 2, device: 'Apple iPhone 15 Pro (iOS 18)', browser: 'Mobile Safari', location: 'Mumbai, Maharashtra, India', ip_address: '103.21.14.88', is_current: false, last_active: '11:18 AM' },
  ]);

  const [notifications, setNotifications] = useState<NotificationPreferences>({
    security_email: true,
    security_inapp: true,
    billing_email: true,
    billing_inapp: true,
    whatsapp_email: true,
    whatsapp_inapp: true,
    system_email: true,
    system_inapp: true,
    user_management_email: true,
    user_management_inapp: true,
    campaign_email: true,
    campaign_inapp: true,
  });

  const [onboarding, setOnboarding] = useState<{ steps: OnboardingStepItem[]; completion_percentage: number; is_ready: boolean }>({
    steps: [
      { key: 'profile', name: 'Organization profile', desc: 'Business identity and contact details', status: 'completed', route: 'settings', tab: 'organization', cta: 'Review' },
      { key: 'whatsapp', name: 'Connect WhatsApp Business', desc: 'Meta account and phone number connection', status: 'completed', route: 'settings', tab: 'whatsapp', cta: 'Configure WhatsApp' },
      { key: 'invite_team', name: 'Invite team members', desc: 'Add owners, admins, and agents', status: 'pending', route: 'iam', tab: 'users', cta: 'Invite User' },
      { key: 'roles', name: 'Configure roles and permissions', desc: 'Apply least-privilege access policy', status: 'pending', route: 'iam', tab: 'policies', cta: 'Configure Policies' },
      { key: 'billing', name: 'Add billing information', desc: 'Subscription and payment preferences', status: 'pending', route: 'account', tab: 'billing', cta: 'Add Billing' },
    ],
    completion_percentage: 40,
    is_ready: false,
  });

  // Fetch live data from backend with fallback preservation
  const refreshAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [orgRes, waRes, usersRes, rolesRes, teamsRes, subRes, billRes, pmRes, invRes, usageRes, auditRes, secRes, notifRes, onbRes] =
        await Promise.allSettled([
          adminApi.getOrganization(),
          adminApi.getWhatsApp(),
          adminApi.getUsers(),
          adminApi.getRoles(),
          adminApi.getTeams(),
          adminApi.getSubscription(),
          adminApi.getBilling(),
          adminApi.getPaymentMethods(),
          adminApi.getInvoices(),
          adminApi.getUsage(),
          adminApi.getAuditLogs(),
          adminApi.getSecurity(),
          adminApi.getNotifications(),
          adminApi.getOnboarding(),
        ]);

      if (orgRes.status === 'fulfilled') setOrgProfile(orgRes.value);
      if (waRes.status === 'fulfilled') setWhatsapp(waRes.value);
      if (usersRes.status === 'fulfilled' && usersRes.value.users) setUsers(usersRes.value.users);
      if (rolesRes.status === 'fulfilled') setRoles(rolesRes.value);
      if (teamsRes.status === 'fulfilled' && teamsRes.value.teams) setTeams(teamsRes.value.teams);
      if (subRes.status === 'fulfilled') setSubscription(subRes.value);
      if (billRes.status === 'fulfilled') setBilling(billRes.value);
      if (pmRes.status === 'fulfilled' && pmRes.value.payment_methods) setPaymentMethods(pmRes.value.payment_methods);
      if (invRes.status === 'fulfilled' && invRes.value.invoices) setInvoices(invRes.value.invoices);
      if (usageRes.status === 'fulfilled') setUsage(usageRes.value);
      if (auditRes.status === 'fulfilled' && auditRes.value.audit_logs) setAuditLogs(auditRes.value.audit_logs);
      if (secRes.status === 'fulfilled' && secRes.value.sessions) setSecuritySessions(secRes.value.sessions);
      if (notifRes.status === 'fulfilled') setNotifications(notifRes.value);
      if (onbRes.status === 'fulfilled') setOnboarding(onbRes.value);
    } catch (err: any) {
      setError(err.message || 'Failed to sync administrative data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  // Mutations
  const updateOrgProfile = async (updates: Partial<OrganizationProfile>) => {
    try {
      const res = await adminApi.updateOrganization(updates);
      setOrgProfile(res);
      toast('Organization settings updated successfully.', 'success');
      return true;
    } catch (err: any) {
      toast(err.message || 'Failed to update organization settings.', 'error');
      return false;
    }
  };

  const connectWhatsApp = async (payload: any) => {
    try {
      await adminApi.connectWhatsApp(payload);
      setWhatsapp((prev) => ({
        ...prev,
        connection_status: 'connected',
        phone_number: payload.phone_number || payload.business_phone || prev.phone_number,
        display_name: payload.display_name || prev.display_name,
        business_account_id: payload.business_account_id || prev.business_account_id,
        phone_number_id: payload.phone_number_id || prev.phone_number_id,
        last_sync: 'Just now',
      }));
      toast('WhatsApp Business connected successfully.', 'success');
      refreshAll();
      return true;
    } catch (err: any) {
      toast(err.message || 'Failed to connect WhatsApp account.', 'error');
      return false;
    }
  };

  const testWhatsAppConnection = async (): Promise<DiagnosticTestResult | null> => {
    try {
      const res = await adminApi.testWhatsApp();
      toast('WhatsApp connection verified successfully.', 'success');
      return res;
    } catch (err: any) {
      toast(err.message || 'Connection test failed.', 'error');
      return null;
    }
  };

  const disconnectWhatsApp = async () => {
    try {
      await adminApi.disconnectWhatsApp();
      setWhatsapp((prev) => ({
        ...prev,
        connection_status: 'not_configured',
        phone_number: '',
        webhook_status: 'Inactive',
      }));
      toast('WhatsApp Business disconnected.', 'info');
      refreshAll();
      return true;
    } catch (err: any) {
      toast(err.message || 'Failed to disconnect WhatsApp.', 'error');
      return false;
    }
  };

  const inviteUser = async (data: { email: string; first_name: string; last_name: string; role: string; team: string }) => {
    try {
      await adminApi.inviteUser(data);
      toast('Invitation sent successfully.', 'success');
      refreshAll();
      return true;
    } catch (err: any) {
      toast(err.message || 'Failed to send invitation.', 'error');
      return false;
    }
  };

  const updateUserRole = async (userId: number, updates: Partial<AdminUser>) => {
    try {
      await adminApi.updateUser(userId, updates);
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, ...updates } : u)));
      toast('User updated successfully.', 'success');
      return true;
    } catch (err: any) {
      toast(err.message || 'Failed to update user.', 'error');
      return false;
    }
  };

  const deactivateUser = async (userId: number) => {
    try {
      await adminApi.deactivateUser(userId);
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, status: 'Disabled' } : u)));
      toast('User deactivated.', 'info');
      return true;
    } catch (err: any) {
      toast(err.message || 'Failed to deactivate user.', 'error');
      return false;
    }
  };

  const createRole = async (roleData: { name: string; description: string; permissions: Record<string, string[]> }) => {
    try {
      const res = await adminApi.createRole(roleData);
      setRoles((prev) => ({ ...prev, custom_roles: [...prev.custom_roles, res] }));
      toast(`Role "${roleData.name}" created successfully.`, 'success');
      return true;
    } catch (err: any) {
      toast(err.message || 'Failed to create role.', 'error');
      return false;
    }
  };

  const createTeam = async (teamData: { name: string; description?: string }) => {
    try {
      const res = await adminApi.createTeam(teamData);
      setTeams((prev) => [...prev, res]);
      toast(`Team "${teamData.name}" created successfully.`, 'success');
      return true;
    } catch (err: any) {
      toast(err.message || 'Failed to create team.', 'error');
      return false;
    }
  };

  const updateBillingInfo = async (billingData: Partial<BillingDetails>) => {
    try {
      const res = await adminApi.updateBilling(billingData);
      setBilling(res);
      toast('Billing information saved successfully.', 'success');
      return true;
    } catch (err: any) {
      toast(err.message || 'Failed to save billing information.', 'error');
      return false;
    }
  };

  const addPaymentMethod = async (cardData: any) => {
    try {
      const res = await adminApi.addPaymentMethod(cardData);
      setPaymentMethods((prev) => [res, ...prev.map((c) => ({ ...c, is_default: false }))]);
      toast('Payment method added.', 'success');
      return true;
    } catch (err: any) {
      toast(err.message || 'Failed to add payment method.', 'error');
      return false;
    }
  };

  const updateNotifications = async (notifData: Partial<NotificationPreferences>) => {
    try {
      const res = await adminApi.updateNotifications(notifData);
      setNotifications(res);
      toast('Notification preferences saved.', 'success');
      return true;
    } catch (err: any) {
      toast(err.message || 'Failed to save notification preferences.', 'error');
      return false;
    }
  };

  const completeStep = async (stepKey: string) => {
    try {
      await adminApi.completeOnboardingStep(stepKey);
      setOnboarding((prev) => {
        const nextSteps = prev.steps.map((s) => (s.key === stepKey ? { ...s, status: 'completed' as const } : s));
        const done = nextSteps.filter((s) => s.status === 'completed').length;
        const pct = Math.round((done / nextSteps.length) * 100);
        return {
          steps: nextSteps,
          completion_percentage: pct,
          is_ready: pct === 100,
        };
      });
    } catch {
      // Optimistic local update
      setOnboarding((prev) => {
        const nextSteps = prev.steps.map((s) => (s.key === stepKey ? { ...s, status: 'completed' as const } : s));
        const done = nextSteps.filter((s) => s.status === 'completed').length;
        const pct = Math.round((done / nextSteps.length) * 100);
        return {
          steps: nextSteps,
          completion_percentage: pct,
          is_ready: pct === 100,
        };
      });
    }
  };

  return {
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
  };
}
