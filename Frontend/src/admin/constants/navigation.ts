import {
  BarChart3,
  CreditCard,
  FileClock,
  KeyRound,
  LayoutGrid,
  Lock,
  MessageSquare,
  Radio,
  Settings,
  ShieldCheck,
  Sliders,
  UserCheck,
  Users,
  Webhook,
  Code2,
} from 'lucide-react';
import type { AdminSection, SettingsTab, IAMTab, AccountTab } from '../types';

export interface NavItemConfig {
  key: AdminSection;
  label: string;
  icon: typeof LayoutGrid;
  description: string;
  defaultSubTab?: string;
  subTabs?: { key: string; label: string; icon?: typeof Settings }[];
}

export const ADMIN_NAV_SECTIONS: NavItemConfig[] = [
  {
    key: 'overview',
    label: 'Overview',
    icon: LayoutGrid,
    description: 'Workspace readiness, onboarding tasks, and core summary metrics',
  },
  {
    key: 'settings',
    label: 'Settings',
    icon: Settings,
    description: 'Organization identity, WhatsApp Meta link, security, and alert preferences',
    defaultSubTab: 'organization',
    subTabs: [
      { key: 'organization', label: 'Organization Profile' },
      { key: 'whatsapp', label: 'WhatsApp Configuration' },
      { key: 'templates', label: 'Notification Templates' },
      { key: 'security', label: 'Security & API Keys' },
      { key: 'notifications', label: 'Notifications' },
      { key: 'integrations', label: 'Integrations' },
    ],
  },
  {
    key: 'iam',
    label: 'IAM',
    icon: Users,
    description: 'Identity, role definitions, routing teams, and granular access matrices',
    defaultSubTab: 'users',
    subTabs: [
      { key: 'users', label: 'Users' },
      { key: 'roles', label: 'Roles' },
      { key: 'departments', label: 'Departments & Routing' },
      { key: 'policies', label: 'Permission Policies' },
    ],
  },
  {
    key: 'account',
    label: 'Account',
    icon: CreditCard,
    description: 'Subscription tiers, tax & billing details, invoices, and quota capacity',
    defaultSubTab: 'subscription',
    subTabs: [
      { key: 'subscription', label: 'Subscription' },
      { key: 'billing', label: 'Billing Details' },
      { key: 'payment-methods', label: 'Payment Methods' },
      { key: 'invoices', label: 'Invoices' },
      { key: 'usage', label: 'Usage' },
    ],
  },
  {
    key: 'audit',
    label: 'Audit Logs',
    icon: FileClock,
    description: 'Immutable forensic event log of administrative activities',
  },
  {
    key: 'compliance',
    label: 'Security & Privacy',
    icon: ShieldCheck,
    description: 'ISO 27001/27701 & DPDP telemetry, KMS key rotation, DSR privacy requests, and retention',
    defaultSubTab: 'telemetry',
    subTabs: [
      { key: 'telemetry', label: 'Controls & Telemetry' },
      { key: 'kms', label: 'KMS & Envelope Keys' },
      { key: 'ropa', label: 'Data Inventory (ROPA)' },
      { key: 'dsr', label: 'Privacy Requests (DSR)' },
      { key: 'retention', label: 'Retention & Legal Holds' },
      { key: 'incidents', label: 'Security Incidents' },
    ],
  },
  {
    key: 'developer',
    label: 'Developer Portal',
    icon: Code2,
    description: 'API v1 documentation, live endpoint explorer, HMAC webhook verification, and SDKs',
    defaultSubTab: 'overview',
    subTabs: [
      { key: 'overview', label: 'API Overview & Auth' },
      { key: 'explorer', label: 'Interactive API Explorer' },
      { key: 'webhooks', label: 'Webhook HMAC Tester' },
      { key: 'sdk', label: 'SDK & Code Snippets' },
      { key: 'logs', label: 'Live API Logs' },
    ],
  },
];

