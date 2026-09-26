import React, { useState, useEffect } from 'react';
import {
  Terminal,
  Code2,
  Key,
  Webhook,
  Send,
  Play,
  Copy,
  Check,
  RefreshCw,
  Shield,
  Layers,
  FileCode,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ExternalLink,
  Search,
  BookOpen,
  Cpu,
} from 'lucide-react';
import { AdminPageHeader } from '../common/AdminPageHeader';
import { DataTable } from '../common/DataTable';
import { StatusBadge } from '../common/StatusBadge';
import { adminApi } from '../../services/adminApi';
import type { DeveloperTab, IntegrationApiLogItem } from '../../types';

interface DeveloperPortalViewProps {
  initialTab?: DeveloperTab;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  onNavigateToIntegrations?: () => void;
}

interface EndpointDefinition {
  id: string;
  name: string;
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  path: string;
  scope: string;
  description: string;
  defaultBody?: any;
  queryParams?: { name: string; description: string; default?: string }[];
}

const ENDPOINTS_CATALOG: EndpointDefinition[] = [
  {
    id: 'leads-list',
    name: 'List Leads',
    method: 'GET',
    path: '/leads/',
    scope: 'lead:read',
    description: 'Retrieve a cursor-paginated list of customer enquiries and CRM leads.',
    queryParams: [
      { name: 'search', description: 'Filter by name, phone, or email' },
      { name: 'status', description: 'Filter by lead status (new, contacted, qualified, lost)' },
      { name: 'page_size', description: 'Number of records per page (default: 20, max: 100)' },
    ],
  },
  {
    id: 'leads-create',
    name: 'Create Lead',
    method: 'POST',
    path: '/leads/',
    scope: 'lead:create',
    description: 'Ingest a new lead from an external source or CRM pipeline.',
    defaultBody: {
      phone_number: '+14155552671',
      name: 'Alex Mercer',
      email: 'alex.mercer@example.com',
      company: 'Mercer Logistics Corp',
      status: 'new',
      notes: 'Ingested via external CRM connector',
      custom_fields: {
        source_campaign: 'enterprise_q3',
      },
    },
  },
  {
    id: 'contacts-list',
    name: 'List Contacts',
    method: 'GET',
    path: '/contacts/',
    scope: 'contact:read',
    description: 'Fetch customer contact profiles and WhatsApp opt-in consent records.',
  },
  {
    id: 'contacts-create',
    name: 'Create Contact',
    method: 'POST',
    path: '/contacts/',
    scope: 'contact:create',
    description: 'Register a verified customer contact identity.',
    defaultBody: {
      phone_number: '+14155559812',
      name: 'Sarah Connor',
      email: 'sarah@cyberdyne.org',
      marketing_opt_in: true,
    },
  },
  {
    id: 'conversations-list',
    name: 'List Conversations',
    method: 'GET',
    path: '/conversations/',
    scope: 'conversation:read',
    description: 'Query WhatsApp conversation threads with status and message counts.',
  },
  {
    id: 'messages-send',
    name: 'Send WhatsApp Message',
    method: 'POST',
    path: '/messages/send/',
    scope: 'message:send',
    description: 'Dispatch an outbound WhatsApp message or notification. Supports Idempotency-Key.',
    defaultBody: {
      recipient: '+14155552671',
      message_type: 'text',
      content: 'Hello Alex! Your enterprise shipment #SH-9082 has been dispatched.',
      template_name: null,
    },
  },
  {
    id: 'tickets-list',
    name: 'List Support Tickets',
    method: 'GET',
    path: '/tickets/',
    scope: 'ticket:read',
    description: 'List support tickets, escalation levels, and resolution status.',
  },
  {
    id: 'tickets-create',
    name: 'Create Support Ticket',
    method: 'POST',
    path: '/tickets/',
    scope: 'ticket:create',
    description: 'Create a customer support ticket or enquiry.',
    defaultBody: {
      title: 'Billing Inquiry - Invoice #INV-2026-09',
      customer_phone: '+14155552671',
      customer_name: 'Alex Mercer',
      priority: 'high',
      description: 'Customer requests invoice clarification regarding additional agent seats.',
    },
  },
  {
    id: 'campaigns-list',
    name: 'List Campaigns',
    method: 'GET',
    path: '/campaigns/',
    scope: 'campaign:read',
    description: 'Retrieve marketing campaigns, delivery progress, and read rates.',
  },
  {
    id: 'templates-list',
    name: 'List WhatsApp Templates',
    method: 'GET',
    path: '/templates/',
    scope: 'campaign:read',
    description: 'Fetch approved Meta WhatsApp message templates.',
  },
  {
    id: 'analytics-overview',
    name: 'Analytics Overview',
    method: 'GET',
    path: '/analytics/',
    scope: 'analytics:read',
    description: 'Fetch platform metrics: message counts, active contacts, and delivery statistics.',
  },
  {
    id: 'webhooks-list',
    name: 'List Webhook Endpoints',
    method: 'GET',
    path: '/webhooks/',
    scope: 'webhook:read',
    description: 'List all registered outbound webhook subscriptions.',
  },
  {
    id: 'webhooks-create',
    name: 'Register Webhook Endpoint',
    method: 'POST',
    path: '/webhooks/',
    scope: 'webhook:manage',
    description: 'Register a new outbound webhook with selected event filters.',
    defaultBody: {
      name: 'Production Event Listener',
      url: 'https://example.com/webhooks/convernix',
      event_filters: ['lead.created', 'message.sent', 'ticket.created'],
      api_version: 'v1',
    },
  },
];

export function DeveloperPortalView({
  initialTab = 'overview',
  toast,
  onNavigateToIntegrations,
}: DeveloperPortalViewProps) {
  const [activeTab, setActiveTab] = useState<DeveloperTab>(initialTab);

  // API Explorer state
  const [selectedEndpoint, setSelectedEndpoint] = useState<EndpointDefinition>(ENDPOINTS_CATALOG[0]);
  const [explorerApiKey, setExplorerApiKey] = useState('');
  const [explorerIdempotencyKey, setExplorerIdempotencyKey] = useState('');
  const [explorerBody, setExplorerBody] = useState<string>('');
  const [explorerLoading, setExplorerLoading] = useState(false);
  const [explorerResponse, setExplorerResponse] = useState<{
    status: number;
    statusText: string;
    headers: Record<string, string>;
    data: any;
  } | null>(null);

  // Webhook HMAC calculator state
  const [hmacSecret, setHmacSecret] = useState('whsec_demo_secret_key_84920');
  const [hmacTimestamp, setHmacTimestamp] = useState(String(Math.floor(Date.now() / 1000)));
  const [hmacPayload, setHmacPayload] = useState(
    JSON.stringify(
      {
        event_id: 'evt_98240f92b719488a',
        event_type: 'lead.created',
        timestamp: new Date().toISOString(),
        tenant_id: 'org_acme_corp',
        data: {
          id: 42,
          name: 'Alex Mercer',
          phone_number: '+14155552671',
          status: 'new',
        },
      },
      null,
      2
    )
  );
  const [computedSignature, setComputedSignature] = useState('');
  const [copiedSnippet, setCopiedSnippet] = useState<string | null>(null);

  // Live Logs state
  const [logs, setLogs] = useState<IntegrationApiLogItem[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  // Sync endpoint selection with explorer default body
  useEffect(() => {
    if (selectedEndpoint.defaultBody) {
      setExplorerBody(JSON.stringify(selectedEndpoint.defaultBody, null, 2));
    } else {
      setExplorerBody('');
    }
    setExplorerResponse(null);
  }, [selectedEndpoint]);

  // Compute HMAC-SHA256 signature live
  useEffect(() => {
    async function calculateSignature() {
      try {
        const canonical = `${hmacTimestamp}.${hmacPayload}`;
        const encoder = new TextEncoder();
        const keyData = encoder.encode(hmacSecret);
        const cryptoKey = await window.crypto.subtle.importKey(
          'raw',
          keyData,
          { name: 'HMAC', hash: 'SHA-256' },
          false,
          ['sign']
        );
        const signatureBuffer = await window.crypto.subtle.sign(
          'HMAC',
          cryptoKey,
          encoder.encode(canonical)
        );
        const hashArray = Array.from(new Uint8Array(signatureBuffer));
        const hashHex = hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
        setComputedSignature(`v1=${hashHex}`);
      } catch {
        setComputedSignature('Error computing HMAC signature');
      }
    }
    if (window.crypto && window.crypto.subtle) {
      calculateSignature();
    }
  }, [hmacSecret, hmacTimestamp, hmacPayload]);

  // Load API logs
  const loadLogs = async () => {
    setLogsLoading(true);
    try {
      const res = await adminApi.getIntegrationApiLogs();
      setLogs(res.results || []);
    } catch (err: any) {
      toast(err.message || 'Failed to load API logs', 'error');
    } finally {
      setLogsLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'logs') {
      loadLogs();
    }
  }, [activeTab]);

  // Copy helper
  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSnippet(label);
    toast(`Copied ${label} to clipboard`, 'info');
    setTimeout(() => setCopiedSnippet(null), 2500);
  };

  // Generate random Idempotency Key
  const handleGenerateIdempotencyKey = () => {
    const key = `idem_${crypto.randomUUID().replace(/-/g, '')}`;
    setExplorerIdempotencyKey(key);
    toast('Generated UUID Idempotency-Key', 'info');
  };

  // Execute request in API explorer
  const handleExecuteExplorer = async () => {
    setExplorerLoading(true);
    setExplorerResponse(null);
    try {
      let parsedBody: any = undefined;
      if (explorerBody.trim() && ['POST', 'PUT', 'PATCH'].includes(selectedEndpoint.method)) {
        try {
          parsedBody = JSON.parse(explorerBody);
        } catch {
          toast('Request body must be valid JSON', 'error');
          setExplorerLoading(false);
          return;
        }
      }

      const customHeaders: Record<string, string> = {};
      if (explorerApiKey.trim()) {
        customHeaders['X-API-Key'] = explorerApiKey.trim();
      }
      if (explorerIdempotencyKey.trim()) {
        customHeaders['Idempotency-Key'] = explorerIdempotencyKey.trim();
      }

      const res = await adminApi.executeV1ApiRequest(
        selectedEndpoint.method,
        selectedEndpoint.path,
        parsedBody,
        customHeaders
      );

      setExplorerResponse(res);
      if (res.status >= 200 && res.status < 300) {
        toast(`Request successful: ${res.status} ${res.statusText}`, 'success');
      } else {
        toast(`Request completed with ${res.status} ${res.statusText}`, 'error');
      }
    } catch (err: any) {
      toast(err.message || 'Execution error', 'error');
    } finally {
      setExplorerLoading(false);
    }
  };

  return (
    <div className="pm-settings-panel">
      {/* Page Header */}
      <AdminPageHeader
        breadcrumbs={[
          { label: 'Administration' },
          { label: 'Developer Platform' },
          { label: 'Developer Portal' },
        ]}
        title="Convernix Developer Portal & API Explorer"
        subtitle="Versioned REST API v1 documentation, live interactive explorer, HMAC webhook verification tools, and production SDK snippets."
        actions={
          onNavigateToIntegrations ? (
            <button
              type="button"
              className="pm-secondary-btn"
              onClick={onNavigateToIntegrations}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Key size={14} />
              <span>Manage API Keys & Webhooks</span>
            </button>
          ) : undefined
        }
      />

      {/* Developer Sub-Nav */}
      <div className="pm-sub-nav" style={{ marginBottom: '24px' }}>
        <button
          type="button"
          className={`pm-sub-nav-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <BookOpen size={15} />
          <span>API Overview & Auth</span>
        </button>
        <button
          type="button"
          className={`pm-sub-nav-btn ${activeTab === 'explorer' ? 'active' : ''}`}
          onClick={() => setActiveTab('explorer')}
        >
          <Play size={15} />
          <span>Interactive API Explorer</span>
        </button>
        <button
          type="button"
          className={`pm-sub-nav-btn ${activeTab === 'webhooks' ? 'active' : ''}`}
          onClick={() => setActiveTab('webhooks')}
        >
          <Webhook size={15} />
          <span>Webhook Tester & HMAC</span>
        </button>
        <button
          type="button"
          className={`pm-sub-nav-btn ${activeTab === 'sdk' ? 'active' : ''}`}
          onClick={() => setActiveTab('sdk')}
        >
          <Code2 size={15} />
          <span>SDK & Code Snippets</span>
        </button>
        <button
          type="button"
          className={`pm-sub-nav-btn ${activeTab === 'logs' ? 'active' : ''}`}
          onClick={() => setActiveTab('logs')}
        >
          <Terminal size={15} />
          <span>Live API Logs</span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: API OVERVIEW & AUTHENTICATION */}
      {/* ========================================================================= */}
      {activeTab === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Base URL & Intro Card */}
          <div
            style={{
              background: 'var(--pm-surface)',
              border: '1px solid var(--pm-border)',
              borderRadius: 'var(--pm-radius)',
              padding: '24px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
              <div>
                <h3 style={{ margin: '0 0 6px', fontSize: '18px' }}>Convernix Public REST API v1</h3>
                <p style={{ margin: 0, fontSize: '13px', color: 'var(--pm-text-muted)' }}>
                  Enterprise-grade REST endpoints with cursor pagination, token-bucket rate limiting, idempotency locks, and SSRF-hardened webhooks.
                </p>
              </div>
              <div
                style={{
                  background: 'var(--pm-surface-alt)',
                  border: '1px solid var(--pm-border)',
                  borderRadius: '6px',
                  padding: '8px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                }}
              >
                <span style={{ fontSize: '12px', color: 'var(--pm-text-muted)' }}>Base Endpoint:</span>
                <code style={{ fontSize: '13px', color: 'var(--pm-primary)' }}>https://api.convernix.com/api/v1/</code>
                <button
                  type="button"
                  className="pm-secondary-btn small"
                  onClick={() => handleCopy('https://api.convernix.com/api/v1/', 'Base URL')}
                >
                  <Copy size={12} />
                </button>
              </div>
            </div>
          </div>

          {/* Core Principles Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
            <div
              style={{
                background: 'var(--pm-surface)',
                border: '1px solid var(--pm-border)',
                borderRadius: 'var(--pm-radius)',
                padding: '20px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--pm-primary)', marginBottom: '10px' }}>
                <Key size={18} />
                <h4 style={{ margin: 0, fontSize: '15px' }}>Authentication</h4>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--pm-text-muted)', lineHeight: '1.5' }}>
                Pass your API key in either the <code>X-API-Key</code> or <code>Authorization</code> header:
              </p>
              <pre
                style={{
                  background: 'rgba(0,0,0,0.3)',
                  padding: '10px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  marginTop: '8px',
                }}
              >
                X-API-Key: cvx_live_a1b2c3d4...
                <br />
                Authorization: Bearer cvx_live_a1b2c3d4...
              </pre>
            </div>

            <div
              style={{
                background: 'var(--pm-surface)',
                border: '1px solid var(--pm-border)',
                borderRadius: 'var(--pm-radius)',
                padding: '20px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--pm-warning)', marginBottom: '10px' }}>
                <Clock size={18} />
                <h4 style={{ margin: 0, fontSize: '15px' }}>Rate Limiting</h4>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--pm-text-muted)', lineHeight: '1.5' }}>
                Distributed token bucket limiter. When exceeded, returns HTTP 429 Too Many Requests with headers:
              </p>
              <pre
                style={{
                  background: 'rgba(0,0,0,0.3)',
                  padding: '10px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  marginTop: '8px',
                }}
              >
                X-RateLimit-Limit: 120
                <br />
                X-RateLimit-Remaining: 119
                <br />
                Retry-After: 60
              </pre>
            </div>

            <div
              style={{
                background: 'var(--pm-surface)',
                border: '1px solid var(--pm-border)',
                borderRadius: 'var(--pm-radius)',
                padding: '20px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--pm-success)', marginBottom: '10px' }}>
                <Shield size={18} />
                <h4 style={{ margin: 0, fontSize: '15px' }}>Idempotency Engine</h4>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--pm-text-muted)', lineHeight: '1.5' }}>
                Safely retry message sending or lead creation by attaching an <code>Idempotency-Key</code> header:
              </p>
              <pre
                style={{
                  background: 'rgba(0,0,0,0.3)',
                  padding: '10px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  marginTop: '8px',
                }}
              >
                Idempotency-Key: e8a9134a-921c-4b6e...
              </pre>
            </div>
          </div>

          {/* Standard Status Codes & Error Envelope */}
          <div
            style={{
              background: 'var(--pm-surface)',
              border: '1px solid var(--pm-border)',
              borderRadius: 'var(--pm-radius)',
              padding: '20px',
            }}
          >
            <h4 style={{ margin: '0 0 12px', fontSize: '15px' }}>Standard JSON Response Envelopes</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div>
                <span style={{ fontSize: '12px', color: 'var(--pm-success)', fontWeight: 600 }}>
                  Success Response (HTTP 200 / 201)
                </span>
                <pre
                  style={{
                    background: 'rgba(0,0,0,0.3)',
                    padding: '12px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    marginTop: '6px',
                  }}
                >
{`{
  "pagination": {
    "count": 42,
    "page": 1,
    "total_pages": 3,
    "next": "https://api.convernix.com/api/v1/leads/?page=2",
    "previous": null
  },
  "results": [ ... ]
}`}
                </pre>
              </div>

              <div>
                <span style={{ fontSize: '12px', color: 'var(--pm-danger)', fontWeight: 600 }}>
                  Error Response (HTTP 4xx / 5xx)
                </span>
                <pre
                  style={{
                    background: 'rgba(0,0,0,0.3)',
                    padding: '12px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    marginTop: '6px',
                  }}
                >
{`{
  "error": {
    "code": "insufficient_scope",
    "message": "Required one of: message:send",
    "request_id": "req_88f912ca902b"
  }
}`}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: INTERACTIVE API EXPLORER */}
      {/* ========================================================================= */}
      {activeTab === 'explorer' && (
        <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: '20px' }}>
          {/* Endpoint Catalog Sidebar */}
          <div
            style={{
              background: 'var(--pm-surface)',
              border: '1px solid var(--pm-border)',
              borderRadius: 'var(--pm-radius)',
              padding: '16px',
              maxHeight: '75vh',
              overflowY: 'auto',
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--pm-text-muted)', marginBottom: '10px' }}>
              API Endpoints ({ENDPOINTS_CATALOG.length})
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {ENDPOINTS_CATALOG.map((ep) => {
                const isSelected = selectedEndpoint.id === ep.id;
                const methodColor =
                  ep.method === 'GET'
                    ? '#3b82f6'
                    : ep.method === 'POST'
                    ? '#10b981'
                    : '#f59e0b';

                return (
                  <button
                    key={ep.id}
                    type="button"
                    onClick={() => setSelectedEndpoint(ep)}
                    style={{
                      textAlign: 'left',
                      padding: '8px 10px',
                      borderRadius: '6px',
                      background: isSelected ? 'rgba(147, 132, 242, 0.15)' : 'transparent',
                      border: isSelected ? '1px solid var(--pm-primary)' : '1px solid transparent',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                    }}
                  >
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        color: methodColor,
                        width: '38px',
                        flexShrink: 0,
                      }}
                    >
                      {ep.method}
                    </span>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <div style={{ fontSize: '13px', fontWeight: isSelected ? 600 : 400 }}>{ep.name}</div>
                      <div style={{ fontSize: '10px', color: 'var(--pm-text-dim)' }}>{ep.path}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Interactive Request & Response Workspace */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Request Builder */}
            <div
              style={{
                background: 'var(--pm-surface)',
                border: '1px solid var(--pm-border)',
                borderRadius: 'var(--pm-radius)',
                padding: '20px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <span
                  style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontWeight: 700,
                    fontSize: '12px',
                    background:
                      selectedEndpoint.method === 'GET'
                        ? 'rgba(59, 130, 246, 0.2)'
                        : 'rgba(16, 185, 129, 0.2)',
                    color:
                      selectedEndpoint.method === 'GET'
                        ? '#3b82f6'
                        : '#10b981',
                  }}
                >
                  {selectedEndpoint.method}
                </span>
                <code style={{ fontSize: '14px', fontWeight: 600, color: 'var(--pm-text)' }}>
                  /api/v1{selectedEndpoint.path}
                </code>
                <span style={{ fontSize: '11px', background: 'rgba(255,255,255,0.06)', padding: '2px 8px', borderRadius: '4px', marginLeft: 'auto' }}>
                  Scope: {selectedEndpoint.scope}
                </span>
              </div>

              <p style={{ fontSize: '13px', color: 'var(--pm-text-muted)', margin: '0 0 16px' }}>
                {selectedEndpoint.description}
              </p>

              {/* Custom Header Overrides */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', marginBottom: '4px' }}>
                    API Key Header (<code>X-API-Key</code>)
                  </label>
                  <input
                    type="text"
                    placeholder="cvx_live_... (leave empty to use session auth)"
                    value={explorerApiKey}
                    onChange={(e) => setExplorerApiKey(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      fontSize: '12px',
                      background: 'var(--pm-surface-alt)',
                      border: '1px solid var(--pm-border)',
                      borderRadius: 'var(--pm-radius-sm)',
                    }}
                  />
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <label style={{ fontSize: '12px' }}>
                      Idempotency-Key Header
                    </label>
                    <button
                      type="button"
                      onClick={handleGenerateIdempotencyKey}
                      style={{ fontSize: '11px', color: 'var(--pm-primary)' }}
                    >
                      Generate Key
                    </button>
                  </div>
                  <input
                    type="text"
                    placeholder="e.g. idem_8a92f0b..."
                    value={explorerIdempotencyKey}
                    onChange={(e) => setExplorerIdempotencyKey(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      fontSize: '12px',
                      background: 'var(--pm-surface-alt)',
                      border: '1px solid var(--pm-border)',
                      borderRadius: 'var(--pm-radius-sm)',
                    }}
                  />
                </div>
              </div>

              {/* Request Body (for POST/PUT) */}
              {['POST', 'PUT', 'PATCH'].includes(selectedEndpoint.method) && (
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
                    Request Body (JSON)
                  </label>
                  <textarea
                    rows={6}
                    value={explorerBody}
                    onChange={(e) => setExplorerBody(e.target.value)}
                    style={{
                      width: '100%',
                      fontFamily: 'monospace',
                      fontSize: '12px',
                      padding: '10px',
                      background: 'var(--pm-surface-alt)',
                      border: '1px solid var(--pm-border)',
                      borderRadius: 'var(--pm-radius-sm)',
                    }}
                  />
                </div>
              )}

              {/* Execute Action */}
              <button
                type="button"
                className="pm-primary-btn"
                onClick={handleExecuteExplorer}
                disabled={explorerLoading}
                style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                <Play size={14} className={explorerLoading ? 'pm-spin' : ''} />
                <span>{explorerLoading ? 'Dispatching Request...' : 'Send Live Request'}</span>
              </button>
            </div>

            {/* Live Response Viewer */}
            {explorerResponse && (
              <div
                style={{
                  background: 'var(--pm-surface)',
                  border: '1px solid var(--pm-border)',
                  borderRadius: 'var(--pm-radius)',
                  padding: '20px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <h4 style={{ margin: 0, fontSize: '15px' }}>Response</h4>
                    <span
                      style={{
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: 700,
                        background:
                          explorerResponse.status >= 200 && explorerResponse.status < 300
                            ? 'rgba(16, 185, 129, 0.15)'
                            : 'rgba(239, 68, 68, 0.15)',
                        color:
                          explorerResponse.status >= 200 && explorerResponse.status < 300
                            ? 'var(--pm-success)'
                            : 'var(--pm-danger)',
                      }}
                    >
                      HTTP {explorerResponse.status} {explorerResponse.statusText}
                    </span>
                    {explorerResponse.headers['x-request-id'] && (
                      <span style={{ fontSize: '11px', color: 'var(--pm-text-dim)' }}>
                        Request ID: {explorerResponse.headers['x-request-id']}
                      </span>
                    )}
                  </div>
                  <button
                    type="button"
                    className="pm-secondary-btn small"
                    onClick={() => handleCopy(JSON.stringify(explorerResponse.data, null, 2), 'Response Body')}
                    style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                  >
                    <Copy size={12} />
                    <span>Copy JSON</span>
                  </button>
                </div>

                <pre
                  style={{
                    background: 'rgba(0,0,0,0.3)',
                    padding: '12px',
                    borderRadius: '6px',
                    fontFamily: 'monospace',
                    fontSize: '12px',
                    maxHeight: '340px',
                    overflowY: 'auto',
                    margin: 0,
                  }}
                >
                  {typeof explorerResponse.data === 'object'
                    ? JSON.stringify(explorerResponse.data, null, 2)
                    : explorerResponse.data}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: WEBHOOK TESTER & HMAC VERIFIER */}
      {/* ========================================================================= */}
      {activeTab === 'webhooks' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div
            style={{
              background: 'var(--pm-surface)',
              border: '1px solid var(--pm-border)',
              borderRadius: 'var(--pm-radius)',
              padding: '24px',
            }}
          >
            <h3 style={{ margin: '0 0 8px', fontSize: '18px' }}>
              HMAC-SHA256 Webhook Signature Calculator & Verifier
            </h3>
            <p style={{ margin: 0, fontSize: '13px', color: 'var(--pm-text-muted)' }}>
              All Convernix outbound webhooks are signed using a canonical header: <code>timestamp + "." + raw_body</code>. Test your local verification implementation here.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', margin: '20px 0' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
                  Webhook Signing Secret Key
                </label>
                <input
                  type="text"
                  value={hmacSecret}
                  onChange={(e) => setHmacSecret(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    fontFamily: 'monospace',
                    fontSize: '12px',
                    background: 'var(--pm-surface-alt)',
                    border: '1px solid var(--pm-border)',
                    borderRadius: 'var(--pm-radius-sm)',
                  }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <label style={{ fontSize: '12px', fontWeight: 600 }}>
                    Timestamp (Unix Seconds)
                  </label>
                  <button
                    type="button"
                    style={{ fontSize: '11px', color: 'var(--pm-primary)' }}
                    onClick={() => setHmacTimestamp(String(Math.floor(Date.now() / 1000)))}
                  >
                    Set Current Time
                  </button>
                </div>
                <input
                  type="text"
                  value={hmacTimestamp}
                  onChange={(e) => setHmacTimestamp(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    fontFamily: 'monospace',
                    fontSize: '12px',
                    background: 'var(--pm-surface-alt)',
                    border: '1px solid var(--pm-border)',
                    borderRadius: 'var(--pm-radius-sm)',
                  }}
                />
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
                Raw Request Body
              </label>
              <textarea
                rows={7}
                value={hmacPayload}
                onChange={(e) => setHmacPayload(e.target.value)}
                style={{
                  width: '100%',
                  fontFamily: 'monospace',
                  fontSize: '12px',
                  padding: '10px',
                  background: 'var(--pm-surface-alt)',
                  border: '1px solid var(--pm-border)',
                  borderRadius: 'var(--pm-radius-sm)',
                }}
              />
            </div>

            {/* Computed Canonical Signature */}
            <div
              style={{
                background: 'rgba(147, 132, 242, 0.08)',
                border: '1px solid var(--pm-primary-glow)',
                borderRadius: 'var(--pm-radius-sm)',
                padding: '14px 18px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--pm-primary)' }}>
                  Computed X-Convernix-Signature Header
                </span>
                <button
                  type="button"
                  className="pm-secondary-btn small"
                  onClick={() => handleCopy(computedSignature, 'Signature Header')}
                >
                  <Copy size={12} />
                  <span>Copy</span>
                </button>
              </div>
              <code
                style={{
                  fontSize: '13px',
                  fontFamily: 'monospace',
                  color: 'var(--pm-text)',
                  wordBreak: 'break-all',
                }}
              >
                {computedSignature}
              </code>
            </div>
          </div>

          {/* Verification Code Reference */}
          <div
            style={{
              background: 'var(--pm-surface)',
              border: '1px solid var(--pm-border)',
              borderRadius: 'var(--pm-radius)',
              padding: '20px',
            }}
          >
            <h4 style={{ margin: '0 0 12px', fontSize: '15px' }}>
              Constant-Time Signature Verification Implementations
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600 }}>Node.js / Express</span>
                  <button
                    type="button"
                    style={{ fontSize: '11px', color: 'var(--pm-primary)' }}
                    onClick={() =>
                      handleCopy(
                        `const crypto = require('crypto');

function verifyConvernixSignature(secret, rawBody, timestamp, signatureHeader) {
  const canonical = timestamp + '.' + rawBody;
  const hmac = crypto.createHmac('sha256', secret);
  const expectedSig = 'v1=' + hmac.update(canonical).digest('hex');
  return crypto.timingSafeEqual(Buffer.from(signatureHeader), Buffer.from(expectedSig));
}`,
                        'Node.js Snippet'
                      )
                    }
                  >
                    Copy
                  </button>
                </div>
                <pre
                  style={{
                    background: 'rgba(0,0,0,0.3)',
                    padding: '10px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    overflowX: 'auto',
                  }}
                >
{`const crypto = require('crypto');

function verifyConvernixSignature(secret, rawBody, timestamp, signatureHeader) {
  const canonical = timestamp + '.' + rawBody;
  const hmac = crypto.createHmac('sha256', secret);
  const expected = 'v1=' + hmac.update(canonical).digest('hex');
  return crypto.timingSafeEqual(
    Buffer.from(signatureHeader),
    Buffer.from(expected)
  );
}`}
                </pre>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600 }}>Python / FastAPI / Flask</span>
                  <button
                    type="button"
                    style={{ fontSize: '11px', color: 'var(--pm-primary)' }}
                    onClick={() =>
                      handleCopy(
                        `import hmac
import hashlib

def verify_convernix_signature(secret: str, raw_body: bytes, timestamp: str, signature_header: str) -> bool:
    canonical = f"{timestamp}.".encode('utf-8') + raw_body
    computed = "v1=" + hmac.new(secret.encode('utf-8'), canonical, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature_header)`,
                        'Python Snippet'
                      )
                    }
                  >
                    Copy
                  </button>
                </div>
                <pre
                  style={{
                    background: 'rgba(0,0,0,0.3)',
                    padding: '10px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    overflowX: 'auto',
                  }}
                >
{`import hmac, hashlib

def verify_convernix_signature(secret, raw_body, timestamp, sig_header):
    canonical = f"{timestamp}.".encode() + raw_body
    computed = "v1=" + hmac.new(
        secret.encode(), canonical, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, sig_header)`}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: SDK & CODE EXAMPLES */}
      {/* ========================================================================= */}
      {activeTab === 'sdk' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Example 1: Send WhatsApp Message */}
          <div
            style={{
              background: 'var(--pm-surface)',
              border: '1px solid var(--pm-border)',
              borderRadius: 'var(--pm-radius)',
              padding: '20px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div>
                <h4 style={{ margin: '0 0 4px', fontSize: '15px' }}>
                  1. Send an Outbound WhatsApp Message with Idempotency
                </h4>
                <p style={{ margin: 0, fontSize: '12px', color: 'var(--pm-text-muted)' }}>
                  Dispatches an enterprise WhatsApp notification. Repeating with the same <code>Idempotency-Key</code> is guaranteed duplicate-safe.
                </p>
              </div>
              <button
                type="button"
                className="pm-secondary-btn small"
                onClick={() =>
                  handleCopy(
                    `import requests

url = "https://api.convernix.com/api/v1/messages/send/"
headers = {
    "X-API-Key": "cvx_live_YOUR_KEY_HERE",
    "Idempotency-Key": "idem_unique_msg_id_1029",
    "Content-Type": "application/json"
}
payload = {
    "recipient": "+14155552671",
    "message_type": "text",
    "content": "Hello! Your appointment is confirmed for tomorrow at 10 AM."
}

response = requests.post(url, json=payload, headers=headers)
print(response.status_code, response.json())`,
                    'Python Message Snippet'
                  )
                }
              >
                <Copy size={12} />
                <span>Copy Python</span>
              </button>
            </div>

            <pre
              style={{
                background: 'rgba(0,0,0,0.3)',
                padding: '12px',
                borderRadius: '6px',
                fontSize: '12px',
                fontFamily: 'monospace',
                overflowX: 'auto',
                margin: 0,
              }}
            >
{`import requests

url = "https://api.convernix.com/api/v1/messages/send/"
headers = {
    "X-API-Key": "cvx_live_YOUR_KEY_HERE",
    "Idempotency-Key": "idem_unique_msg_id_1029",
    "Content-Type": "application/json"
}
payload = {
    "recipient": "+14155552671",
    "message_type": "text",
    "content": "Hello! Your appointment is confirmed for tomorrow at 10 AM."
}

response = requests.post(url, json=payload, headers=headers)
print(response.status_code, response.json())`}
            </pre>
          </div>

          {/* Example 2: Ingest CRM Lead */}
          <div
            style={{
              background: 'var(--pm-surface)',
              border: '1px solid var(--pm-border)',
              borderRadius: 'var(--pm-radius)',
              padding: '20px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div>
                <h4 style={{ margin: '0 0 4px', fontSize: '15px' }}>
                  2. Ingest Inbound CRM Leads (JavaScript / Node.js)
                </h4>
                <p style={{ margin: 0, fontSize: '12px', color: 'var(--pm-text-muted)' }}>
                  Capture incoming website forms and route directly into Convernix WhatsApp CRM pipeline.
                </p>
              </div>
              <button
                type="button"
                className="pm-secondary-btn small"
                onClick={() =>
                  handleCopy(
                    `const res = await fetch('https://api.convernix.com/api/v1/leads/', {
  method: 'POST',
  headers: {
    'X-API-Key': process.env.CONVERNIX_API_KEY,
    'Idempotency-Key': crypto.randomUUID(),
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    phone_number: '+14155552671',
    name: 'Alex Mercer',
    email: 'alex.mercer@example.com',
    status: 'new'
  })
});
const data = await res.json();
console.log('Lead created:', data);`,
                    'Node.js Lead Snippet'
                  )
                }
              >
                <Copy size={12} />
                <span>Copy JS</span>
              </button>
            </div>

            <pre
              style={{
                background: 'rgba(0,0,0,0.3)',
                padding: '12px',
                borderRadius: '6px',
                fontSize: '12px',
                fontFamily: 'monospace',
                overflowX: 'auto',
                margin: 0,
              }}
            >
{`const res = await fetch('https://api.convernix.com/api/v1/leads/', {
  method: 'POST',
  headers: {
    'X-API-Key': process.env.CONVERNIX_API_KEY,
    'Idempotency-Key': crypto.randomUUID(),
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    phone_number: '+14155552671',
    name: 'Alex Mercer',
    email: 'alex.mercer@example.com',
    status: 'new'
  })
});
const data = await res.json();
console.log('Lead created:', data);`}
            </pre>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 5: LIVE API LOGS */}
      {/* ========================================================================= */}
      {activeTab === 'logs' && (
        <div
          style={{
            background: 'var(--pm-surface)',
            border: '1px solid var(--pm-border)',
            borderRadius: 'var(--pm-radius)',
            padding: '20px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>Live Inbound Request Stream</h3>
              <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--pm-text-muted)' }}>
                Near real-time visibility into all calls made to /api/v1/ endpoints with latency and client IP metadata.
              </p>
            </div>
            <button
              type="button"
              className="pm-secondary-btn small"
              onClick={loadLogs}
              disabled={logsLoading}
            >
              <RefreshCw size={13} className={logsLoading ? 'pm-spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>

          <DataTable<IntegrationApiLogItem>
            columns={[
              {
                key: 'timestamp',
                header: 'Time',
                render: (l) => new Date(l.timestamp).toLocaleTimeString(),
              },
              {
                key: 'method',
                header: 'Method',
                render: (l) => (
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      color: l.method === 'GET' ? '#3b82f6' : '#10b981',
                      background: 'rgba(255,255,255,0.06)',
                      padding: '2px 6px',
                      borderRadius: '4px',
                    }}
                  >
                    {l.method}
                  </span>
                ),
              },
              {
                key: 'path',
                header: 'Path',
                render: (l) => <code style={{ fontSize: '12px' }}>{l.path}</code>,
              },
              {
                key: 'status',
                header: 'HTTP Code',
                render: (l) => (
                  <span
                    style={{
                      fontSize: '12px',
                      fontWeight: 600,
                      color:
                        l.status_code >= 200 && l.status_code < 300
                          ? 'var(--pm-success)'
                          : 'var(--pm-danger)',
                    }}
                  >
                    {l.status_code}
                  </span>
                ),
              },
              {
                key: 'duration',
                header: 'Latency',
                render: (l) => `${l.duration_ms} ms`,
              },
              {
                key: 'ip_address',
                header: 'Client IP',
                render: (l) => l.ip_address,
              },
              {
                key: 'request_id',
                header: 'Correlation ID',
                render: (l) => (
                  <span style={{ fontSize: '11px', color: 'var(--pm-text-dim)' }}>
                    {l.request_id?.slice(0, 16)}...
                  </span>
                ),
              },
            ]}
            data={logs}
            emptyMessage="No API logs recorded yet."
          />
        </div>
      )}
    </div>
  );
}

export default DeveloperPortalView;

