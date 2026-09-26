export interface PermissionAction {
  key: string;
  label: string;
  description?: string;
}

export interface PermissionModule {
  key: string;
  label: string;
  actions: PermissionAction[];
}

export const PERMISSION_MODULES: PermissionModule[] = [
  {
    key: 'dashboard',
    label: 'Dashboard',
    actions: [
      { key: 'view_dashboard', label: 'View Dashboard', description: 'Access dashboard summary and performance tiles' },
    ],
  },
  {
    key: 'conversations',
    label: 'Conversations',
    actions: [
      { key: 'view_conversations', label: 'View Conversations', description: 'Browse and inspect customer conversations' },
      { key: 'reply_conversations', label: 'Reply to Conversations', description: 'Send chat replies, files, and notes' },
      { key: 'assign_conversations', label: 'Assign Conversations', description: 'Reassign queue conversations to team members' },
      { key: 'close_conversations', label: 'Close Conversations', description: 'Mark active conversations resolved' },
      { key: 'delete_conversations', label: 'Delete Conversations', description: 'Permanently remove conversation threads' },
    ],
  },
  {
    key: 'contacts',
    label: 'Contacts',
    actions: [
      { key: 'view_contacts', label: 'View Contacts', description: 'Search and inspect customer directory records' },
      { key: 'create_contacts', label: 'Create Contacts', description: 'Manually add new customer records' },
      { key: 'edit_contacts', label: 'Edit Contacts', description: 'Update customer details and custom attributes' },
      { key: 'delete_contacts', label: 'Delete Contacts', description: 'Remove customer contact profiles' },
      { key: 'export_contacts', label: 'Export Contacts', description: 'Download CSV and Excel contact lists' },
    ],
  },
  {
    key: 'campaigns',
    label: 'Campaigns',
    actions: [
      { key: 'view_campaigns', label: 'View Campaigns', description: 'Inspect campaign rosters and delivery telemetry' },
      { key: 'create_campaigns', label: 'Create Campaigns', description: 'Draft new broadcast messages' },
      { key: 'approve_campaigns', label: 'Approve Campaigns', description: 'Authorize scheduled broadcasts for dispatch' },
      { key: 'send_campaigns', label: 'Send Campaigns', description: 'Execute live broadcast message delivery' },
      { key: 'delete_campaigns', label: 'Delete Campaigns', description: 'Cancel and delete broadcast campaigns' },
    ],
  },
  {
    key: 'templates',
    label: 'Templates',
    actions: [
      { key: 'view_templates', label: 'View Templates', description: 'Review pre-approved WhatsApp message formats' },
      { key: 'create_templates', label: 'Create Templates', description: 'Author new message templates with variables' },
      { key: 'submit_templates', label: 'Submit Templates', description: 'Submit drafts to Meta for review and approval' },
      { key: 'delete_templates', label: 'Delete Templates', description: 'Decommission rejected or obsolete templates' },
    ],
  },
  {
    key: 'automation',
    label: 'Automation',
    actions: [
      { key: 'view_workflows', label: 'View Workflows', description: 'Inspect inbound bot and trigger definitions' },
      { key: 'create_workflows', label: 'Create Workflows', description: 'Construct new routing and auto-reply rules' },
      { key: 'edit_workflows', label: 'Edit Workflows', description: 'Modify conditions, business hours, and actions' },
      { key: 'publish_workflows', label: 'Publish Workflows', description: 'Activate automated workflows live' },
      { key: 'delete_workflows', label: 'Delete Workflows', description: 'Remove routing workflows' },
    ],
  },
  {
    key: 'analytics',
    label: 'Analytics',
    actions: [
      { key: 'view_analytics', label: 'View Analytics', description: 'Review response times, resolution rates, and traffic' },
      { key: 'export_reports', label: 'Export Reports', description: 'Generate and download executive PDF/CSV metrics' },
    ],
  },
  {
    key: 'administration',
    label: 'Administration',
    actions: [
      { key: 'manage_organization', label: 'Manage Organization', description: 'Update company profile, brand logo, and locale' },
      { key: 'manage_whatsapp', label: 'Manage WhatsApp', description: 'Connect/disconnect Meta accounts and manage phone numbers' },
      { key: 'manage_users', label: 'Manage Users', description: 'Invite, suspend, and deactivate operators' },
      { key: 'manage_roles', label: 'Manage Roles', description: 'Configure custom roles and permission policies' },
      { key: 'manage_billing', label: 'Manage Billing', description: 'Upgrade plans, manage payment methods, and invoices' },
      { key: 'view_audit_logs', label: 'View Audit Logs', description: 'Inspect forensic immutable activity trails' },
    ],
  },
];

export const DEFAULT_ROLE_MATRICES: Record<string, string[]> = {
  owner: PERMISSION_MODULES.flatMap((m) => m.actions.map((a) => a.key)),
  admin: PERMISSION_MODULES.flatMap((m) => m.actions.map((a) => a.key)).filter(
    (k) => k !== 'delete_conversations' // Least privilege protection for non-owners
  ),
  manager: [
    'view_dashboard',
    'view_conversations',
    'reply_conversations',
    'assign_conversations',
    'close_conversations',
    'view_contacts',
    'create_contacts',
    'edit_contacts',
    'export_contacts',
    'view_campaigns',
    'create_campaigns',
    'view_templates',
    'create_templates',
    'view_workflows',
    'edit_workflows',
    'view_analytics',
    'export_reports',
    'manage_users',
    'view_audit_logs',
  ],
  agent: [
    'view_dashboard',
    'view_conversations',
    'reply_conversations',
    'close_conversations',
    'view_contacts',
    'create_contacts',
    'view_templates',
  ],
  billing_admin: [
    'view_dashboard',
    'manage_billing',
    'view_analytics',
    'view_audit_logs',
  ],
  read_only: [
    'view_dashboard',
    'view_conversations',
    'view_contacts',
    'view_campaigns',
    'view_templates',
    'view_workflows',
    'view_analytics',
    'view_audit_logs',
  ],
};

