import type {
  AdminUser,
  ApiKeyInfo,
  AuditLogEntry,
  BillingDetails,
  CreatedApiKeyResponse,
  DepartmentInfo,
  DiagnosticTestResult,
  IntegrationInfo,
  InvoiceItem,
  NotificationPreferences,
  NotificationTemplateInfo,
  NotificationTemplateVersionInfo,
  OnboardingStepItem,
  OrganizationProfile,
  PaymentCard,
  PlanInfo,
  RoleDefinition,
  SecurityPolicyInfo,
  SubscriptionPlanInfo,
  SupportAccessRequestInfo,
  TeamDepartment,
  UsageMetricItem,
  UserSessionInfo,
  WhatsAppConnectionState,
  ServiceAccountItem,
  ApiKeyItem,
  CreatedApiKeyResult,
  WebhookEndpointItem,
  WebhookDeliveryItem,
  ConnectorManifestItem,
  ConnectorInstanceItem,
  ConnectorFieldMappingItem,
  IntegrationApiLogItem,
} from '../types';

const API_BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '') + '/admin';

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('crm_access_token') || localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
  const mergedHeaders = {
    ...getAuthHeaders(),
    ...(options.headers || {}),
  };

  const res = await fetch(url, { ...options, headers: mergedHeaders });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    const errorMsg =
      errData.detail ||
      errData.message ||
      (errData.phone_number ? errData.phone_number[0] : null) ||
      (errData.email ? errData.email[0] : null) ||
      (errData.name ? errData.name[0] : null) ||
      `Request failed with status ${res.status}`;
    const err = new Error(errorMsg);
    (err as any).status = res.status;
    (err as any).data = errData;
    throw err;
  }
  return (await res.json()) as T;
}

export const adminApi = {
  // Organization Profile
  async getOrganization(): Promise<OrganizationProfile> {
    return request<OrganizationProfile>('/organization/');
  },

  async updateOrganization(data: Partial<OrganizationProfile>): Promise<OrganizationProfile> {
    return request<OrganizationProfile>('/organization/', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // WhatsApp Business
  async getWhatsApp(): Promise<WhatsAppConnectionState> {
    return request<WhatsAppConnectionState>('/whatsapp/');
  },

  async connectWhatsApp(data: Record<string, any>): Promise<{ message: string; status: string }> {
    return request<{ message: string; status: string }>('/whatsapp/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async testWhatsApp(): Promise<DiagnosticTestResult> {
    return request<DiagnosticTestResult>('/whatsapp/?action=test', {
      method: 'POST',
      body: JSON.stringify({ action: 'test' }),
    });
  },

  async disconnectWhatsApp(): Promise<{ message: string; status: string }> {
    return request<{ message: string; status: string }>('/whatsapp/?action=disconnect', {
      method: 'POST',
      body: JSON.stringify({ action: 'disconnect' }),
    });
  },

  // IAM Users
  async getUsers(): Promise<{ users: AdminUser[] }> {
    return request<{ users: AdminUser[] }>('/users/');
  },

  async inviteUser(data: { email: string; first_name: string; last_name: string; role: string; team: string }): Promise<any> {
    return request('/users/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateUser(id: number, data: Partial<AdminUser>): Promise<any> {
    return request(`/users/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async deactivateUser(id: number): Promise<any> {
    return request(`/users/${id}/`, {
      method: 'DELETE',
    });
  },

  // Roles
  async getRoles(): Promise<{ system_roles: RoleDefinition[]; custom_roles: RoleDefinition[] }> {
    return request<{ system_roles: RoleDefinition[]; custom_roles: RoleDefinition[] }>('/roles/');
  },

  async createRole(data: { name: string; description: string; permissions: Record<string, string[]> }): Promise<RoleDefinition> {
    return request<RoleDefinition>('/roles/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Teams
  async getTeams(): Promise<{ teams: TeamDepartment[] }> {
    return request<{ teams: TeamDepartment[] }>('/teams/');
  },

  async createTeam(data: { name: string; description?: string }): Promise<TeamDepartment> {
    return request<TeamDepartment>('/teams/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Account & Subscription
  async getSubscription(): Promise<SubscriptionPlanInfo> {
    return request<SubscriptionPlanInfo>('/subscription/');
  },

  async upgradeSubscription(tier: string): Promise<{ message: string }> {
    return request<{ message: string }>('/subscription/', {
      method: 'POST',
      body: JSON.stringify({ action: 'upgrade', tier }),
    });
  },

  async cancelSubscription(reason?: string): Promise<{ message: string }> {
    return request<{ message: string }>('/subscription/', {
      method: 'POST',
      body: JSON.stringify({ action: 'cancel', reason }),
    });
  },

  // Billing
  async getBilling(): Promise<BillingDetails> {
    return request<BillingDetails>('/billing/');
  },

  async updateBilling(data: Partial<BillingDetails>): Promise<BillingDetails> {
    return request<BillingDetails>('/billing/', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // Payment Methods
  async getPaymentMethods(): Promise<{ payment_methods: PaymentCard[] }> {
    return request<{ payment_methods: PaymentCard[] }>('/payment-methods/');
  },

  async addPaymentMethod(data: { card_brand: string; last4: string; exp_month: number; exp_year: number; is_default: boolean }): Promise<PaymentCard> {
    return request<PaymentCard>('/payment-methods/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Invoices
  async getInvoices(): Promise<{ invoices: InvoiceItem[] }> {
    return request<{ invoices: InvoiceItem[] }>('/invoices/');
  },

  // Usage
  async getUsage(): Promise<{ metrics: UsageMetricItem[]; alerts: string[] }> {
    return request<{ metrics: UsageMetricItem[]; alerts: string[] }>('/usage/');
  },

  // Audit Logs
  async getAuditLogs(params?: { module?: string }): Promise<{ audit_logs: AuditLogEntry[] }> {
    const query = params?.module ? `?module=${encodeURIComponent(params.module)}` : '';
    return request<{ audit_logs: AuditLogEntry[] }>(`/audit-logs/${query}`);
  },

  getAuditExportUrl(): string {
    return `${API_BASE}/audit-logs/?export=csv`;
  },

  // Security
  async getSecurity(): Promise<{
    mfa_enabled: boolean;
    authenticator_app: string;
    email_otp: string;
    password_policy: string;
    last_security_review: string;
    sessions: UserSessionInfo[];
  }> {
    return request('/security/');
  },

  async updatePassword(data: { current_password: string; new_password: string; confirm_password: string }): Promise<any> {
    return request('/security/', {
      method: 'POST',
      body: JSON.stringify({ action: 'update_password', ...data }),
    });
  },

  async revokeSession(sessionId: number): Promise<any> {
    return request('/security/', {
      method: 'POST',
      body: JSON.stringify({ action: 'revoke_session', session_id: sessionId }),
    });
  },

  async revokeAllOtherSessions(): Promise<any> {
    return request('/security/', {
      method: 'POST',
      body: JSON.stringify({ action: 'revoke_all_other' }),
    });
  },

  // Notifications
  async getNotifications(): Promise<NotificationPreferences> {
    return request<NotificationPreferences>('/notifications/');
  },

  async updateNotifications(data: Partial<NotificationPreferences>): Promise<NotificationPreferences> {
    return request<NotificationPreferences>('/notifications/', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // Onboarding
  async getOnboarding(): Promise<{ steps: OnboardingStepItem[]; completion_percentage: number; is_ready: boolean }> {
    return request<{ steps: OnboardingStepItem[]; completion_percentage: number; is_ready: boolean }>('/onboarding/');
  },

  async completeOnboardingStep(stepKey: string): Promise<any> {
    return request('/onboarding/', {
      method: 'POST',
      body: JSON.stringify({ step_key: stepKey }),
    });
  },

  // Departments
  async getDepartments(params?: { include_archived?: boolean; search?: string }): Promise<{ departments: DepartmentInfo[] }> {
    const queryParts = [];
    if (params?.include_archived) queryParts.push('include_archived=true');
    if (params?.search) queryParts.push(`search=${encodeURIComponent(params.search)}`);
    const q = queryParts.length ? `?${queryParts.join('&')}` : '';
    return request<{ departments: DepartmentInfo[] }>(`/departments/${q}`);
  },

  async createDepartment(data: {
    name: string;
    description?: string;
    manager_id?: number;
    business_hours?: Record<string, any>;
  }): Promise<DepartmentInfo> {
    return request<DepartmentInfo>('/departments/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateDepartment(id: number, data: Partial<DepartmentInfo>): Promise<DepartmentInfo> {
    return request<DepartmentInfo>(`/departments/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async archiveDepartment(id: number): Promise<{ message: string }> {
    return request<{ message: string }>(`/departments/${id}/`, {
      method: 'DELETE',
    });
  },

  // Notification Templates
  async getTemplates(): Promise<{
    templates: NotificationTemplateInfo[];
    allowed_variables: { variable: string; description: string }[];
  }> {
    return request<{
      templates: NotificationTemplateInfo[];
      allowed_variables: { variable: string; description: string }[];
    }>('/templates/');
  },

  async getTemplate(id: number): Promise<{
    template: NotificationTemplateInfo;
    versions: NotificationTemplateVersionInfo[];
    allowed_variables: { variable: string; description: string }[];
  }> {
    return request<{
      template: NotificationTemplateInfo;
      versions: NotificationTemplateVersionInfo[];
      allowed_variables: { variable: string; description: string }[];
    }>(`/templates/${id}/`);
  },

  async createTemplate(data: {
    name: string;
    event_type: string;
    channel?: string;
    content: string;
  }): Promise<NotificationTemplateInfo> {
    return request<NotificationTemplateInfo>('/templates/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateTemplate(
    id: number,
    data: { name?: string; event_type?: string; channel?: string; content?: string; change_summary?: string }
  ): Promise<NotificationTemplateInfo> {
    return request<NotificationTemplateInfo>(`/templates/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async publishTemplate(id: number, data?: { content?: string; change_summary?: string }): Promise<NotificationTemplateInfo> {
    return request<NotificationTemplateInfo>(`/templates/${id}/publish/`, {
      method: 'POST',
      body: JSON.stringify(data || {}),
    });
  },

  async previewTemplate(
    content: string,
    custom_data?: Record<string, any>,
    id?: number
  ): Promise<{ rendered: string; variables: string[]; is_valid: boolean }> {
    const endpoint = id ? `/templates/${id}/preview/` : '/templates/preview/';
    return request<{ rendered: string; variables: string[]; is_valid: boolean }>(endpoint, {
      method: 'POST',
      body: JSON.stringify({ content, custom_data }),
    });
  },

  async rollbackTemplate(id: number, target_version: number): Promise<NotificationTemplateInfo> {
    return request<NotificationTemplateInfo>(`/templates/${id}/rollback/`, {
      method: 'POST',
      body: JSON.stringify({ target_version }),
    });
  },

  async deleteTemplate(id: number): Promise<{ message: string }> {
    return request<{ message: string }>(`/templates/${id}/`, {
      method: 'DELETE',
    });
  },

  // API Keys
  async getApiKeys(): Promise<{ api_keys: ApiKeyInfo[] }> {
    return request<{ api_keys: ApiKeyInfo[] }>('/api-keys/');
  },

  async createApiKey(data: { name: string; scopes?: string[]; expires_in_days?: number }): Promise<CreatedApiKeyResponse> {
    return request<CreatedApiKeyResponse>('/api-keys/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async revokeApiKey(id: number): Promise<{ message: string }> {
    return request<{ message: string }>(`/api-keys/${id}/`, {
      method: 'DELETE',
    });
  },

  // Security Policy
  async getSecurityPolicy(): Promise<SecurityPolicyInfo> {
    return request<SecurityPolicyInfo>('/security/policy/');
  },

  async updateSecurityPolicy(data: Partial<SecurityPolicyInfo>): Promise<SecurityPolicyInfo> {
    return request<SecurityPolicyInfo>('/security/policy/', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // Plans & Subscription
  async getPlans(): Promise<{ plans: PlanInfo[] }> {
    return request<{ plans: PlanInfo[] }>('/plans/');
  },

  async upgradePlan(plan_code: string): Promise<{ message: string; subscription: any }> {
    return request<{ message: string; subscription: any }>('/subscription/upgrade/', {
      method: 'POST',
      body: JSON.stringify({ plan_code }),
    });
  },

  async getUsageMetrics(): Promise<{
    metrics: UsageMetricItem[];
    alerts: string[];
    subscription?: any;
  }> {
    return request<{
      metrics: UsageMetricItem[];
      alerts: string[];
      subscription?: any;
    }>('/usage/metrics/');
  },

  // Integrations
  async getIntegrations(): Promise<{ integrations: IntegrationInfo[] }> {
    return request<{ integrations: IntegrationInfo[] }>('/integrations/');
  },

  async connectIntegration(data: {
    integration_type: string;
    name?: string;
    credentials?: string;
    config?: Record<string, any>;
  }): Promise<IntegrationInfo> {
    return request<IntegrationInfo>('/integrations/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async testIntegration(id: number): Promise<{ status: string; message: string }> {
    return request<{ status: string; message: string }>(`/integrations/${id}/test/`, {
      method: 'POST',
    });
  },

  async disconnectIntegration(id: number): Promise<{ message: string }> {
    return request<{ message: string }>(`/integrations/${id}/`, {
      method: 'DELETE',
    });
  },

  // Support Access Elevation
  async getSupportRequests(): Promise<{ requests: SupportAccessRequestInfo[] }> {
    return request<{ requests: SupportAccessRequestInfo[] }>('/support/requests/');
  },

  async approveSupportRequest(id: number): Promise<{ message: string }> {
    return request<{ message: string }>(`/support/requests/${id}/approve/`, {
      method: 'POST',
    });
  },

  async rejectSupportRequest(id: number): Promise<{ message: string }> {
    return request<{ message: string }>(`/support/requests/${id}/reject/`, {
      method: 'POST',
    });
  },

  // --- Modern Convernix Integrations & Developer Platform ---

  // Service Accounts
  async getServiceAccounts(): Promise<{ results: ServiceAccountItem[] }> {
    return request<{ results: ServiceAccountItem[] }>('/integrations/service-accounts/');
  },
  async createServiceAccount(data: { name: string; description?: string }): Promise<ServiceAccountItem> {
    return request<ServiceAccountItem>('/integrations/service-accounts/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  async updateServiceAccount(id: string, data: Partial<ServiceAccountItem>): Promise<ServiceAccountItem> {
    return request<ServiceAccountItem>(`/integrations/service-accounts/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },
  async deleteServiceAccount(id: string): Promise<{ message?: string }> {
    return request<{ message?: string }>(`/integrations/service-accounts/${id}/`, {
      method: 'DELETE',
    });
  },

  // API Keys
  async getApiKeys(): Promise<{ results: ApiKeyItem[] }> {
    return request<{ results: ApiKeyItem[] }>('/integrations/api-keys/');
  },
  async createApiKey(data: {
    service_account_id?: string;
    environment?: 'live' | 'test';
    scopes?: string[];
    allowed_ips?: string[];
    expires_in_days?: number | null;
  }): Promise<CreatedApiKeyResult> {
    return request<CreatedApiKeyResult>('/integrations/api-keys/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  async revokeApiKey(id: string, reason?: string): Promise<{ message: string }> {
    return request<{ message: string }>(`/integrations/api-keys/${id}/revoke/`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  },
  async rotateApiKey(id: string): Promise<CreatedApiKeyResult> {
    return request<CreatedApiKeyResult>(`/integrations/api-keys/${id}/rotate/`, {
      method: 'POST',
    });
  },

  // Webhook Endpoints
  async getWebhookEndpoints(): Promise<{ results: WebhookEndpointItem[] }> {
    return request<{ results: WebhookEndpointItem[] }>('/integrations/webhooks/');
  },
  async createWebhookEndpoint(data: {
    name: string;
    url: string;
    event_filters?: string[];
    api_version?: string;
  }): Promise<WebhookEndpointItem & { signing_secret?: string }> {
    return request<WebhookEndpointItem & { signing_secret?: string }>('/integrations/webhooks/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  async updateWebhookEndpoint(id: string, data: Partial<WebhookEndpointItem>): Promise<WebhookEndpointItem> {
    return request<WebhookEndpointItem>(`/integrations/webhooks/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },
  async deleteWebhookEndpoint(id: string): Promise<{ message?: string }> {
    return request<{ message?: string }>(`/integrations/webhooks/${id}/`, {
      method: 'DELETE',
    });
  },
  async rotateWebhookSecret(id: string): Promise<{ id: string; signing_secret: string; message: string }> {
    return request<{ id: string; signing_secret: string; message: string }>(`/integrations/webhooks/${id}/rotate-secret/`, {
      method: 'POST',
    });
  },
  async testWebhookPing(id: string): Promise<{ status: string; http_status?: number; duration_ms?: number; response_snippet?: string; message?: string }> {
    return request<{ status: string; http_status?: number; duration_ms?: number; response_snippet?: string; message?: string }>(`/integrations/webhooks/${id}/test/`, {
      method: 'POST',
    });
  },

  // Webhook Deliveries
  async getWebhookDeliveries(params?: { endpoint_id?: string; status?: string }): Promise<{ results: WebhookDeliveryItem[] }> {
    const query = new URLSearchParams();
    if (params?.endpoint_id) query.set('endpoint_id', params.endpoint_id);
    if (params?.status) query.set('status', params.status);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request<{ results: WebhookDeliveryItem[] }>(`/integrations/webhooks/deliveries/${qs}`);
  },
  async replayWebhookDelivery(id: string): Promise<{ message: string; delivery_id: string; status: string; http_status?: number }> {
    return request<{ message: string; delivery_id: string; status: string; http_status?: number }>(`/integrations/webhooks/deliveries/${id}/replay/`, {
      method: 'POST',
    });
  },

  // Connectors
  async getConnectorMarketplace(): Promise<{ connectors: ConnectorManifestItem[] }> {
    return request<{ connectors: ConnectorManifestItem[] }>('/integrations/integrations/marketplace/');
  },
  async getConnectorInstances(): Promise<{ results: ConnectorInstanceItem[] }> {
    return request<{ results: ConnectorInstanceItem[] }>('/integrations/integrations/instances/');
  },
  async createConnectorInstance(data: {
    connector_id: string;
    name?: string;
    config?: Record<string, any>;
    sync_direction?: string;
  }): Promise<ConnectorInstanceItem> {
    return request<ConnectorInstanceItem>('/integrations/integrations/instances/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  async updateConnectorInstance(id: string, data: Partial<ConnectorInstanceItem>): Promise<ConnectorInstanceItem> {
    return request<ConnectorInstanceItem>(`/integrations/integrations/instances/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },
  async deleteConnectorInstance(id: string): Promise<{ message?: string }> {
    return request<{ message?: string }>(`/integrations/integrations/instances/${id}/`, {
      method: 'DELETE',
    });
  },
  async testConnectorInstance(id: string): Promise<{ status: string; message: string; details?: any }> {
    return request<{ status: string; message: string; details?: any }>(`/integrations/integrations/instances/${id}/test/`, {
      method: 'POST',
    });
  },
  async getConnectorFieldMappings(instanceId: string): Promise<{ mappings: ConnectorFieldMappingItem[] }> {
    return request<{ mappings: ConnectorFieldMappingItem[] }>(`/integrations/integrations/instances/${instanceId}/mappings/`);
  },
  async saveConnectorFieldMappings(instanceId: string, mappings: ConnectorFieldMappingItem[]): Promise<{ mappings: ConnectorFieldMappingItem[]; message: string }> {
    return request<{ mappings: ConnectorFieldMappingItem[]; message: string }>(`/integrations/integrations/instances/${instanceId}/mappings/`, {
      method: 'POST',
      body: JSON.stringify({ mappings }),
    });
  },

  // Logs
  async getIntegrationApiLogs(params?: { status?: string; method?: string; path?: string }): Promise<{ results: IntegrationApiLogItem[] }> {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.method) query.set('method', params.method);
    if (params?.path) query.set('path', params.path);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request<{ results: IntegrationApiLogItem[] }>(`/integrations/logs/api/${qs}`);
  },
  async getIntegrationAuditLogs(): Promise<{ results: any[] }> {
    return request<{ results: any[] }>('/integrations/logs/audit/');
  },

  // Live Explorer V1 Caller (Supports custom headers such as X-API-Key and custom methods)
  async executeV1ApiRequest(
    method: string,
    path: string,
    body?: any,
    customHeaders?: Record<string, string>
  ): Promise<{ status: number; statusText: string; headers: Record<string, string>; data: any }> {
    const cleanPath = path.startsWith('/') ? path : '/' + path;
    const url = `/api/v1${cleanPath}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...customHeaders,
    };
    if (!headers['Authorization'] && !headers['X-API-Key']) {
      const token = localStorage.getItem('crm_access_token') || localStorage.getItem('token');
      if (token) headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(url, {
      method,
      headers,
      body: body && ['POST', 'PUT', 'PATCH'].includes(method) ? JSON.stringify(body) : undefined,
    });

    const responseHeaders: Record<string, string> = {};
    res.headers.forEach((val, key) => {
      responseHeaders[key] = val;
    });

    let data: any;
    try {
      data = await res.json();
    } catch {
      data = await res.text();
    }

    return {
      status: res.status,
      statusText: res.statusText,
      headers: responseHeaders,
      data,
    };
  },
};

