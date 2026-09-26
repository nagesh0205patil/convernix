export type AdminSection = 'overview' | 'settings' | 'iam' | 'account' | 'audit' | 'compliance' | 'developer';

export type SettingsTab = 'organization' | 'whatsapp' | 'templates' | 'security' | 'notifications' | 'integrations';
export type IAMTab = 'users' | 'roles' | 'departments' | 'teams' | 'policies';
export type AccountTab = 'subscription' | 'billing' | 'payment-methods' | 'invoices' | 'usage';
export type ComplianceTab = 'telemetry' | 'kms' | 'ropa' | 'dsr' | 'retention' | 'incidents';
export type DeveloperTab = 'overview' | 'explorer' | 'webhooks' | 'sdk' | 'logs';

export type AdminSubTab = SettingsTab | IAMTab | AccountTab | ComplianceTab | DeveloperTab | '';

export interface OrganizationProfile {
  id?: number;
  organization_name: string;
  legal_business_name: string;
  org_id: string;
  slug?: string;
  tier?: string;
  tier_display?: string;
  industry: string;
  business_email: string;
  business_phone: string;
  website: string;
  country: string;
  state: string;
  city: string;
  postal_code: string;
  timezone: string;
  default_language: string;
  business_address: string;
  logo_url?: string;
  onboarding_completed: boolean;
  onboarding_steps: Record<string, boolean>;
}

export type WhatsAppStatus = 'not_configured' | 'pending_verification' | 'connected' | 'error' | 'disabled';

export interface WhatsAppConnectionState {
  connection_status: WhatsAppStatus;
  business_name: string;
  phone_number: string;
  business_account_id: string;
  phone_number_id: string;
  meta_business_account: string;
  meta_app_id: string;
  display_name: string;
  business_verification_status: 'Verified' | 'Pending' | 'Unverified';
  webhook_status: 'Active' | 'Inactive' | 'Degraded';
  webhook_url: string;
  last_sync: string;
  has_access_token?: boolean;
  has_app_secret?: boolean;
  has_verify_token?: boolean;
}

export interface DiagnosticCheck {
  name: string;
  status: 'success' | 'warning' | 'error' | 'pending';
  message: string;
}

export interface DiagnosticTestResult {
  overall_status: 'success' | 'error';
  checks: DiagnosticCheck[];
  timestamp: string;
}

export interface AdminUser {
  id: number;
  name: string;
  first_name?: string;
  last_name?: string;
  email: string;
  role: string;
  team: string;
  status: 'Active' | 'Invited' | 'Suspended' | 'Disabled';
  last_login: string;
  mfa: 'Enabled' | 'Pending' | 'Disabled';
  created: string;
}

export interface RoleDefinition {
  id: string | number;
  name: string;
  slug: string;
  description: string;
  is_system: boolean;
  user_count: number;
  permissions?: Record<string, string[]>;
  updated?: string;
}

export interface TeamDepartment {
  id: number;
  name: string;
  slug: string;
  description: string;
  manager: string;
  members_count: number;
  assigned_queues: string[];
  status: 'Active' | 'Inactive';
}

export interface SubscriptionPlanInfo {
  plan_name: string;
  status: 'Active' | 'Trial' | 'Suspended' | 'Past Due';
  billing_cycle: 'Monthly' | 'Annual';
  price: string;
  amount_raw: number;
  renewal_date: string;
  seats_included: number;
  numbers_included: number;
  allowance_conversations: string;
}

export interface BillingDetails {
  id?: number;
  legal_company_name: string;
  billing_email: string;
  tax_id: string;
  country: string;
  state: string;
  city: string;
  postal_code: string;
  address: string;
}

export interface PaymentCard {
  id: number;
  card_brand: string;
  last4: string;
  exp_month: number;
  exp_year: number;
  is_default: boolean;
  created_at?: string;
}

export interface InvoiceItem {
  id: number;
  invoice_number: string;
  billing_period: string;
  issue_date: string;
  amount: number | string;
  currency: string;
  status: 'paid' | 'pending' | 'failed' | 'refunded';
  payment_method_desc: string;
  pdf_url?: string;
}

export interface UsageMetricItem {
  key: string;
  label: string;
  used: number;
  total: number;
  unit: string;
  percent: number;
}

export interface AuditLogEntry {
  id: number;
  actor_name: string;
  actor_email?: string;
  action: string;
  module: string;
  resource: string;
  ip_address: string;
  status: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface UserSessionInfo {
  id: number;
  device: string;
  browser: string;
  location: string;
  ip_address: string;
  is_current: boolean;
  last_active: string;
}

export interface NotificationPreferences {
  security_email: boolean;
  security_inapp: boolean;
  billing_email: boolean;
  billing_inapp: boolean;
  whatsapp_email: boolean;
  whatsapp_inapp: boolean;
  system_email: boolean;
  system_inapp: boolean;
  user_management_email: boolean;
  user_management_inapp: boolean;
  campaign_email: boolean;
  campaign_inapp: boolean;
}

export interface OnboardingStepItem {
  key: string;
  name: string;
  desc: string;
  status: 'completed' | 'pending';
  route: AdminSection;
  tab: AdminSubTab;
  cta: string;
}

export interface DepartmentInfo {
  id: number;
  name: string;
  slug: string;
  description: string;
  manager?: number | null;
  manager_name?: string;
  business_hours?: Record<string, any>;
  is_active: boolean;
  is_archived: boolean;
  archived_at?: string | null;
  member_count: number;
}

export interface NotificationTemplateVersionInfo {
  id: number;
  version: number;
  content: string;
  variables: string[];
  change_summary: string;
  published_by_name?: string;
  published_at: string;
}

export interface NotificationTemplateInfo {
  id: number;
  name: string;
  event_type: string;
  channel: string;
  status: 'draft' | 'published' | 'archived';
  current_version: number;
  latest_version?: NotificationTemplateVersionInfo | null;
  created_at: string;
  updated_at: string;
}

export interface ApiKeyInfo {
  id: number;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  expires_at?: string | null;
  last_used_at?: string | null;
  revoked_at?: string | null;
  creator_name?: string;
  created_at: string;
}

export interface CreatedApiKeyResponse extends ApiKeyInfo {
  plaintext_key: string;
}

export interface SecurityPolicyInfo {
  mfa_required: boolean;
  password_min_length: number;
  password_require_special: boolean;
  session_duration_minutes: number;
  ip_allowlist: string[];
  updated_at?: string;
}

export interface PlanLimitInfo {
  metric_code: string;
  max_value: number;
}

export interface PlanInfo {
  id: number;
  code: string;
  name: string;
  tier: string;
  price_inr: string | number;
  billing_interval: string;
  is_active: boolean;
  entitlements: string[];
  limits: PlanLimitInfo[];
}

export interface IntegrationInfo {
  id: number;
  integration_type: string;
  name: string;
  status: string;
  config: Record<string, any>;
  has_credentials: boolean;
  last_sync_at?: string | null;
  last_error?: string;
  updated_at: string;
}

export interface SupportAccessRequestInfo {
  id: number;
  tenant: number;
  tenant_name?: string;
  platform_user_email?: string;
  reason: string;
  ticket_reference: string;
  requested_scopes: string[];
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  approved_at?: string | null;
  expires_at?: string | null;
  created_at: string;
}

// ==========================================
// CONVERNIX INTEGRATIONS & DEVELOPER PORTAL
// ==========================================

export interface ServiceAccountItem {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'disabled';
  created_by?: string;
  created_at: string;
  updated_at: string;
  key_count?: number;
}

export interface ApiKeyItem {
  id: string;
  service_account_id?: string;
  service_account_name?: string;
  key_prefix: string;
  scopes: string[];
  allowed_ips: string[];
  status: 'active' | 'revoked' | 'expired';
  expires_at: string | null;
  last_used_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface CreatedApiKeyResult {
  id: string;
  service_account_id: string;
  key_prefix: string;
  plaintext_key: string;
  scopes: string[];
  allowed_ips: string[];
  expires_at: string | null;
  created_at: string;
  message?: string;
}

export interface WebhookEndpointItem {
  id: string;
  name: string;
  url: string;
  status: 'active' | 'disabled';
  event_filters: string[];
  api_version: string;
  created_by?: string;
  created_at: string;
  updated_at: string;
  secret_preview?: string;
}

export interface WebhookDeliveryItem {
  id: string;
  endpoint_id: string;
  endpoint_url?: string;
  endpoint_name?: string;
  event_id: string;
  event_type: string;
  attempt_number: number;
  http_status: number | null;
  duration_ms: number;
  error_category: string;
  error_message: string;
  status: 'pending' | 'success' | 'failed' | 'dlq';
  next_retry_at: string | null;
  created_at: string;
  request_headers?: Record<string, string>;
  request_body?: any;
  response_headers?: Record<string, string>;
  response_body?: string;
}

export interface ConnectorManifestItem {
  id: string;
  name: string;
  category: string;
  description: string;
  capabilities: string[];
  auth_type: string;
  logo_url?: string;
}

export interface ConnectorInstanceItem {
  id: string;
  connector_id: string;
  name: string;
  status: 'connected' | 'error' | 'disconnected';
  sync_direction: 'inbound' | 'outbound' | 'bidirectional';
  auto_sync_enabled: boolean;
  sync_interval_minutes: number;
  last_sync_at: string | null;
  last_error: string;
  health_status: 'healthy' | 'degraded' | 'failing';
  config: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ConnectorFieldMappingItem {
  id?: string;
  local_object_type: string;
  remote_object_type: string;
  local_field: string;
  remote_field: string;
  transform_type: 'direct' | 'enum_map' | 'default_value' | 'boolean_cast' | 'number_cast' | 'date_format';
  transform_config?: Record<string, any>;
}

export interface IntegrationApiLogItem {
  id: string;
  timestamp: string;
  request_id: string;
  principal_type: string;
  principal_id: string;
  method: string;
  path: string;
  status_code: number;
  duration_ms: number;
  ip_address: string;
  user_agent: string;
  error_message?: string;
}



