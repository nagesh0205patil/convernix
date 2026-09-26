import React, { useState, useEffect, useMemo } from 'react';
import {
  Webhook,
  Plus,
  CheckCircle2,
  ExternalLink,
  RefreshCw,
  Key,
  Shield,
  Layers,
  Plug,
  Terminal,
  Activity,
  AlertTriangle,
  Copy,
  Check,
  Play,
  RotateCw,
  Trash2,
  Eye,
  EyeOff,
  Filter,
  Search,
  FileText,
  Sliders,
  Database,
  ArrowRight,
  XCircle,
  Clock,
  Send,
  Lock,
} from 'lucide-react';
import { AdminPageHeader } from '../common/AdminPageHeader';
import { StatusBadge } from '../common/StatusBadge';
import { DataTable, type Column } from '../common/DataTable';
import { ConfirmationDialog } from '../common/ConfirmationDialog';
import { adminApi } from '../../services/adminApi';
import type {
  ServiceAccountItem,
  ApiKeyItem,
  CreatedApiKeyResult,
  WebhookEndpointItem,
  WebhookDeliveryItem,
  ConnectorManifestItem,
  ConnectorInstanceItem,
  ConnectorFieldMappingItem,
  IntegrationApiLogItem,
} from '../../types';

interface IntegrationsViewProps {
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  onOpenDeveloperPortal?: () => void;
}

type IntegrationTab =
  | 'marketplace'
  | 'connected'
  | 'api_keys'
  | 'webhooks'
  | 'deliveries'
  | 'logs'
  | 'audit';

export function IntegrationsView({ toast, onOpenDeveloperPortal }: IntegrationsViewProps) {
  const [activeTab, setActiveTab] = useState<IntegrationTab>('marketplace');
  const [loading, setLoading] = useState<boolean>(false);

  // Data states
  const [marketplace, setMarketplace] = useState<ConnectorManifestItem[]>([]);
  const [instances, setInstances] = useState<ConnectorInstanceItem[]>([]);
  const [serviceAccounts, setServiceAccounts] = useState<ServiceAccountItem[]>([]);
  const [apiKeys, setApiKeys] = useState<ApiKeyItem[]>([]);
  const [webhooks, setWebhooks] = useState<WebhookEndpointItem[]>([]);
  const [deliveries, setDeliveries] = useState<WebhookDeliveryItem[]>([]);
  const [apiLogs, setApiLogs] = useState<IntegrationApiLogItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  // Search & filter
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');

  // Modals & Drawers
  const [showCreateAccountModal, setShowCreateAccountModal] = useState(false);
  const [showCreateKeyModal, setShowCreateKeyModal] = useState(false);
  const [showCreatedKeyRevealModal, setShowCreatedKeyRevealModal] = useState(false);
  const [revealedKeyResult, setRevealedKeyResult] = useState<CreatedApiKeyResult | null>(null);
  const [keyCopied, setKeyCopied] = useState(false);

  const [showCreateWebhookModal, setShowCreateWebhookModal] = useState(false);
  const [showRevealedWebhookSecret, setShowRevealedWebhookSecret] = useState<{ id: string; secret: string } | null>(null);
  const [inspectDelivery, setInspectDelivery] = useState<WebhookDeliveryItem | null>(null);

  const [showConnectModal, setShowConnectModal] = useState<ConnectorManifestItem | null>(null);
  const [showFieldMappingModal, setShowFieldMappingModal] = useState<ConnectorInstanceItem | null>(null);
  const [fieldMappings, setFieldMappings] = useState<ConnectorFieldMappingItem[]>([]);

  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    danger?: boolean;
    confirmText?: string;
    onConfirm: () => Promise<void>;
  }>({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: async () => {},
  });

  // Forms
  const [newAccountName, setNewAccountName] = useState('');
  const [newAccountDesc, setNewAccountDesc] = useState('');

  const [newKeyServiceAccountId, setNewKeyServiceAccountId] = useState('');
  const [newKeyEnv, setNewKeyEnv] = useState<'live' | 'test'>('live');
  const [newKeyExpiresDays, setNewKeyExpiresDays] = useState<number | null>(90);
  const [newKeyIpAllowlist, setNewKeyIpAllowlist] = useState('');
  const [newKeyScopes, setNewKeyScopes] = useState<string[]>([
    'lead:read',
    'contact:read',
    'conversation:read',
    'message:read',
  ]);

  const [newWebhookName, setNewWebhookName] = useState('');
  const [newWebhookUrl, setNewWebhookUrl] = useState('');
  const [newWebhookVersion, setNewWebhookVersion] = useState('v1');
  const [newWebhookEvents, setNewWebhookEvents] = useState<string[]>([
    'lead.created',
    'message.received',
    'message.sent',
    'ticket.created',
  ]);

  const [connectName, setConnectName] = useState('');
  const [connectSyncDir, setConnectSyncDir] = useState<'inbound' | 'outbound' | 'bidirectional'>('bidirectional');
  const [connectConfigJson, setConnectConfigJson] = useState('{}');

  // Load initial data
  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [mktRes, instRes, saRes, keysRes, whRes, delivRes, logsRes, auditRes] = await Promise.allSettled([
        adminApi.getConnectorMarketplace(),
        adminApi.getConnectorInstances(),
        adminApi.getServiceAccounts(),
        adminApi.getApiKeys(),
        adminApi.getWebhookEndpoints(),
        adminApi.getWebhookDeliveries(),
        adminApi.getIntegrationApiLogs(),
        adminApi.getIntegrationAuditLogs(),
      ]);

      if (mktRes.status === 'fulfilled') setMarketplace(mktRes.value.connectors || []);
      if (instRes.status === 'fulfilled') setInstances(instRes.value.results || []);
      if (saRes.status === 'fulfilled') setServiceAccounts(saRes.value.results || []);
      if (keysRes.status === 'fulfilled') setApiKeys(keysRes.value.results || []);
      if (whRes.status === 'fulfilled') setWebhooks(whRes.value.results || []);
      if (delivRes.status === 'fulfilled') setDeliveries(delivRes.value.results || []);
      if (logsRes.status === 'fulfilled') setApiLogs(logsRes.value.results || []);
      if (auditRes.status === 'fulfilled') setAuditLogs(auditRes.value.results || []);
    } catch (err: any) {
      toast(err.message || 'Failed to load integration resources', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Helper copy to clipboard
  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setKeyCopied(true);
    toast('Copied to clipboard', 'info');
    setTimeout(() => setKeyCopied(false), 2500);
  };

  // Service Account handlers
  const handleCreateServiceAccount = async () => {
    if (!newAccountName.trim()) {
      toast('Service account name is required', 'error');
      return;
    }
    try {
      const res = await adminApi.createServiceAccount({
        name: newAccountName.trim(),
        description: newAccountDesc.trim(),
      });
      toast(`Service Account "${res.name}" created`, 'success');
      setNewAccountName('');
      setNewAccountDesc('');
      setShowCreateAccountModal(false);
      loadAllData();
    } catch (err: any) {
      toast(err.message || 'Failed to create service account', 'error');
    }
  };

  const handleDeleteServiceAccount = (id: string, name: string) => {
    setConfirmDialog({
      isOpen: true,
      title: 'Delete Service Account',
      message: `Are you sure you want to delete service account "${name}"? All associated API keys will be immediately revoked.`,
      danger: true,
      confirmText: 'Delete & Revoke Keys',
      onConfirm: async () => {
        try {
          await adminApi.deleteServiceAccount(id);
          toast(`Service account "${name}" deleted`, 'success');
          setConfirmDialog((p) => ({ ...p, isOpen: false }));
          loadAllData();
        } catch (err: any) {
          toast(err.message || 'Failed to delete service account', 'error');
        }
      },
    });
  };

  // API Key handlers
  const handleCreateApiKey = async () => {
    try {
      const allowed_ips = newKeyIpAllowlist
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);

      const res = await adminApi.createApiKey({
        service_account_id: newKeyServiceAccountId || undefined,
        environment: newKeyEnv,
        scopes: newKeyScopes,
        allowed_ips,
        expires_in_days: newKeyExpiresDays,
      });

      setShowCreateKeyModal(false);
      setRevealedKeyResult(res);
      setShowCreatedKeyRevealModal(true);
      loadAllData();
    } catch (err: any) {
      toast(err.message || 'Failed to create API key', 'error');
    }
  };

  const handleRevokeApiKey = (id: string, prefix: string) => {
    setConfirmDialog({
      isOpen: true,
      title: 'Revoke API Key',
      message: `Are you sure you want to revoke API Key ${prefix}...? Applications using this key will immediately receive HTTP 401 Unauthorized.`,
      danger: true,
      confirmText: 'Revoke Key Now',
      onConfirm: async () => {
        try {
          await adminApi.revokeApiKey(id, 'Admin manual revocation');
          toast('API Key revoked successfully', 'success');
          setConfirmDialog((p) => ({ ...p, isOpen: false }));
          loadAllData();
        } catch (err: any) {
          toast(err.message || 'Failed to revoke API key', 'error');
        }
      },
    });
  };

  const handleRotateApiKey = async (id: string, prefix: string) => {
    setConfirmDialog({
      isOpen: true,
      title: 'Rotate API Key',
      message: `Rotating key ${prefix}... will generate a new secret and immediately revoke the old key. Proceed?`,
      danger: true,
      confirmText: 'Rotate Key',
      onConfirm: async () => {
        try {
          const res = await adminApi.rotateApiKey(id);
          setConfirmDialog((p) => ({ ...p, isOpen: false }));
          setRevealedKeyResult(res);
          setShowCreatedKeyRevealModal(true);
          loadAllData();
        } catch (err: any) {
          toast(err.message || 'Failed to rotate API key', 'error');
        }
      },
    });
  };

  // Webhook handlers
  const handleCreateWebhook = async () => {
    if (!newWebhookName.trim() || !newWebhookUrl.trim()) {
      toast('Endpoint Name and Destination URL are required', 'error');
      return;
    }
    try {
      const res = await adminApi.createWebhookEndpoint({
        name: newWebhookName.trim(),
        url: newWebhookUrl.trim(),
        event_filters: newWebhookEvents,
        api_version: newWebhookVersion,
      });

      toast(`Webhook endpoint "${res.name}" registered`, 'success');
      setShowCreateWebhookModal(false);
      setNewWebhookName('');
      setNewWebhookUrl('');
      if (res.signing_secret) {
        setShowRevealedWebhookSecret({ id: res.id, secret: res.signing_secret });
      }
      loadAllData();
    } catch (err: any) {
      toast(err.message || 'Failed to register webhook endpoint', 'error');
    }
  };

  const handleRotateWebhookSecret = (id: string, name: string) => {
    setConfirmDialog({
      isOpen: true,
      title: 'Rotate Webhook Secret',
      message: `Rotate HMAC signing secret for "${name}"? You will need to update your consumer verification code with the new secret.`,
      danger: true,
      confirmText: 'Rotate Secret',
      onConfirm: async () => {
        try {
          const res = await adminApi.rotateWebhookSecret(id);
          setConfirmDialog((p) => ({ ...p, isOpen: false }));
          setShowRevealedWebhookSecret({ id, secret: res.signing_secret });
          toast('Webhook signing secret rotated', 'success');
        } catch (err: any) {
          toast(err.message || 'Failed to rotate webhook secret', 'error');
        }
      },
    });
  };

  const handleTestWebhookPing = async (id: string, name: string) => {
    toast(`Dispatching diagnostic test ping to "${name}"...`, 'info');
    try {
      const res = await adminApi.testWebhookPing(id);
      if (res.status === 'success') {
        toast(`Test ping succeeded! HTTP ${res.http_status} (${res.duration_ms}ms)`, 'success');
      } else {
        toast(`Test ping failed: ${res.message || 'Destination rejected delivery'}`, 'error');
      }
      loadAllData();
    } catch (err: any) {
      toast(err.message || 'Failed to dispatch test ping', 'error');
    }
  };

  const handleReplayDelivery = async (deliveryId: string) => {
    try {
      toast('Replaying webhook delivery attempt...', 'info');
      const res = await adminApi.replayWebhookDelivery(deliveryId);
      toast(`Replay triggered: ${res.status} (Delivery #${res.delivery_id.slice(0, 8)})`, 'success');
      loadAllData();
    } catch (err: any) {
      toast(err.message || 'Failed to replay delivery', 'error');
    }
  };

  const handleDeleteWebhook = (id: string, name: string) => {
    setConfirmDialog({
      isOpen: true,
      title: 'Delete Webhook Endpoint',
      message: `Delete webhook endpoint "${name}"? No further events will be dispatched to this URL.`,
      danger: true,
      confirmText: 'Delete Endpoint',
      onConfirm: async () => {
        try {
          await adminApi.deleteWebhookEndpoint(id);
          toast(`Endpoint "${name}" deleted`, 'success');
          setConfirmDialog((p) => ({ ...p, isOpen: false }));
          loadAllData();
        } catch (err: any) {
          toast(err.message || 'Failed to delete webhook endpoint', 'error');
        }
      },
    });
  };

  // Connector handlers
  const handleConnectConnector = async () => {
    if (!showConnectModal) return;
    try {
      let parsedConfig = {};
      try {
        parsedConfig = JSON.parse(connectConfigJson);
      } catch {
        toast('Configuration must be valid JSON', 'error');
        return;
      }

      await adminApi.createConnectorInstance({
        connector_id: showConnectModal.id,
        name: connectName.trim() || showConnectModal.name,
        sync_direction: connectSyncDir,
        config: parsedConfig,
      });

      toast(`Connected ${showConnectModal.name} successfully`, 'success');
      setShowConnectModal(null);
      setConnectName('');
      setConnectConfigJson('{}');
      loadAllData();
    } catch (err: any) {
      toast(err.message || 'Failed to connect integration', 'error');
    }
  };

  const handleTestConnector = async (id: string, name: string) => {
    toast(`Testing connection to ${name}...`, 'info');
    try {
      const res = await adminApi.testConnectorInstance(id);
      if (res.status === 'success') {
        toast(`Connection test passed: ${res.message}`, 'success');
      } else {
        toast(`Connection degraded: ${res.message}`, 'error');
      }
      loadAllData();
    } catch (err: any) {
      toast(err.message || 'Connection test failed', 'error');
    }
  };

  const handleDisconnectConnector = (id: string, name: string) => {
    setConfirmDialog({
      isOpen: true,
      title: 'Disconnect Connector',
      message: `Are you sure you want to disconnect ${name}? Active syncing will halt immediately.`,
      danger: true,
      confirmText: 'Disconnect',
      onConfirm: async () => {
        try {
          await adminApi.deleteConnectorInstance(id);
          toast(`Disconnected ${name}`, 'info');
          setConfirmDialog((p) => ({ ...p, isOpen: false }));
          loadAllData();
        } catch (err: any) {
          toast(err.message || 'Failed to disconnect connector', 'error');
        }
      },
    });
  };

  const handleOpenFieldMappings = async (instance: ConnectorInstanceItem) => {
    setShowFieldMappingModal(instance);
    try {
      const res = await adminApi.getConnectorFieldMappings(instance.id);
      setFieldMappings(res.mappings || []);
    } catch (err: any) {
      toast('Failed to load field mappings', 'error');
    }
  };

  const handleSaveFieldMappings = async () => {
    if (!showFieldMappingModal) return;
    try {
      await adminApi.saveConnectorFieldMappings(showFieldMappingModal.id, fieldMappings);
      toast('Field mappings saved successfully', 'success');
      setShowFieldMappingModal(null);
    } catch (err: any) {
      toast(err.message || 'Failed to save field mappings', 'error');
    }
  };

  // Filtered Marketplace
  const filteredMarketplace = useMemo(() => {
    return marketplace.filter((m) => {
      const matchesSearch =
        m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.category.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory =
        categoryFilter === 'all' || m.category.toLowerCase() === categoryFilter.toLowerCase();
      return matchesSearch && matchesCategory;
    });
  }, [marketplace, searchQuery, categoryFilter]);

  // All Available Granular Scopes
  const scopeCategories = [
    {
      category: 'Leads & CRM Enquiries',
      scopes: [
        { code: 'lead:read', desc: 'Read leads and pipeline status' },
        { code: 'lead:create', desc: 'Create incoming leads' },
        { code: 'lead:update', desc: 'Modify lead details and stages' },
      ],
    },
    {
      category: 'Contacts & Customer Identity',
      scopes: [
        { code: 'contact:read', desc: 'View customer contacts' },
        { code: 'contact:create', desc: 'Create new contacts' },
        { code: 'contact:update', desc: 'Update contact info and consent' },
      ],
    },
    {
      category: 'Conversations & WhatsApp Messaging',
      scopes: [
        { code: 'conversation:read', desc: 'Read conversation history' },
        { code: 'message:read', desc: 'Read WhatsApp messages' },
        { code: 'message:send', desc: 'Dispatch WhatsApp messages' },
      ],
    },
    {
      category: 'Support & Tickets',
      scopes: [
        { code: 'ticket:read', desc: 'View support tickets' },
        { code: 'ticket:create', desc: 'Create support tickets' },
        { code: 'ticket:update', desc: 'Assign and resolve tickets' },
      ],
    },
    {
      category: 'Campaigns & Marketing',
      scopes: [
        { code: 'campaign:read', desc: 'View campaigns and templates' },
        { code: 'campaign:create', desc: 'Create marketing campaigns' },
        { code: 'campaign:execute', desc: 'Trigger campaign execution' },
      ],
    },
    {
      category: 'Webhooks & Connectors',
      scopes: [
        { code: 'webhook:read', desc: 'View webhooks and logs' },
        { code: 'webhook:manage', desc: 'Manage endpoints and secrets' },
        { code: 'integration:read', desc: 'View installed connectors' },
        { code: 'integration:manage', desc: 'Configure external connectors' },
        { code: 'analytics:read', desc: 'Access usage and analytics' },
      ],
    },
  ];

  const allAvailableEvents = [
    { code: 'lead.created', label: 'Lead Created' },
    { code: 'lead.updated', label: 'Lead Updated' },
    { code: 'lead.assigned', label: 'Lead Assigned' },
    { code: 'contact.created', label: 'Contact Created' },
    { code: 'contact.updated', label: 'Contact Updated' },
    { code: 'conversation.created', label: 'Conversation Started' },
    { code: 'conversation.closed', label: 'Conversation Closed' },
    { code: 'message.received', label: 'WhatsApp Message Received' },
    { code: 'message.sent', label: 'WhatsApp Message Sent' },
    { code: 'message.delivered', label: 'WhatsApp Message Delivered' },
    { code: 'message.read', label: 'WhatsApp Message Read' },
    { code: 'message.failed', label: 'WhatsApp Message Failed' },
    { code: 'ticket.created', label: 'Ticket Created' },
    { code: 'ticket.resolved', label: 'Ticket Resolved' },
    { code: 'campaign.started', label: 'Campaign Started' },
    { code: 'campaign.completed', label: 'Campaign Completed' },
  ];

  return (
    <div className="pm-settings-panel">
      {/* Page Header */}
      <AdminPageHeader
        breadcrumbs={[
          { label: 'Administration' },
          { label: 'Settings' },
          { label: 'Integrations & API' },
        ]}
        title="Integrations, Webhooks & API Connectors"
        subtitle="Secure enterprise integration gateway for CRMs, ERPs, inbound/outbound webhooks, service accounts, and API automation."
        actions={
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {onOpenDeveloperPortal && (
              <button
                type="button"
                className="pm-secondary-btn"
                onClick={onOpenDeveloperPortal}
                style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                <Terminal size={14} />
                <span>Developer Portal</span>
              </button>
            )}
            <button
              type="button"
              className="pm-secondary-btn"
              onClick={loadAllData}
              disabled={loading}
              title="Refresh all integrations"
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <RefreshCw size={14} className={loading ? 'pm-spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>
        }
      />

      {/* Internal Navigation Tabs */}
      <div className="pm-sub-nav" style={{ marginBottom: '24px' }}>
        <button
          type="button"
          className={`pm-sub-nav-btn ${activeTab === 'marketplace' ? 'active' : ''}`}
          onClick={() => setActiveTab('marketplace')}
        >
          <Plug size={15} />
          <span>Marketplace ({marketplace.length})</span>
        </button>
        <button
          type="button"
          className={`pm-sub-nav-btn ${activeTab === 'connected' ? 'active' : ''}`}
          onClick={() => setActiveTab('connected')}
        >
          <Layers size={15} />
          <span>Connected Apps ({instances.length})</span>
        </button>
        <button
          type="button"
          className={`pm-sub-nav-btn ${activeTab === 'api_keys' ? 'active' : ''}`}
          onClick={() => setActiveTab('api_keys')}
        >
          <Key size={15} />
          <span>API Keys & Service Accounts ({apiKeys.length})</span>
        </button>
        <button
          type="button"
          className={`pm-sub-nav-btn ${activeTab === 'webhooks' ? 'active' : ''}`}
          onClick={() => setActiveTab('webhooks')}
        >
          <Webhook size={15} />
          <span>Webhooks ({webhooks.length})</span>
        </button>
        <button
          type="button"
          className={`pm-sub-nav-btn ${activeTab === 'deliveries' ? 'active' : ''}`}
          onClick={() => setActiveTab('deliveries')}
        >
          <Activity size={15} />
          <span>Delivery History & DLQ ({deliveries.length})</span>
        </button>
        <button
          type="button"
          className={`pm-sub-nav-btn ${activeTab === 'logs' ? 'active' : ''}`}
          onClick={() => setActiveTab('logs')}
        >
          <FileText size={15} />
          <span>API Logs ({apiLogs.length})</span>
        </button>
        <button
          type="button"
          className={`pm-sub-nav-btn ${activeTab === 'audit' ? 'active' : ''}`}
          onClick={() => setActiveTab('audit')}
        >
          <Shield size={15} />
          <span>Audit Trail ({auditLogs.length})</span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: MARKETPLACE & DIRECTORY */}
      {/* ========================================================================= */}
      {activeTab === 'marketplace' && (
        <div>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '16px',
              gap: '12px',
              flexWrap: 'wrap',
            }}
          >
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flex: 1 }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  background: 'var(--pm-surface)',
                  border: '1px solid var(--pm-border)',
                  borderRadius: 'var(--pm-radius-sm)',
                  padding: '6px 12px',
                  width: '320px',
                  gap: '8px',
                }}
              >
                <Search size={14} color="var(--pm-text-muted)" />
                <input
                  type="text"
                  placeholder="Search connectors by name or keyword..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    outline: 'none',
                    fontSize: '13px',
                    width: '100%',
                  }}
                />
              </div>

              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                style={{
                  background: 'var(--pm-surface)',
                  border: '1px solid var(--pm-border)',
                  borderRadius: 'var(--pm-radius-sm)',
                  padding: '8px 12px',
                  fontSize: '13px',
                }}
              >
                <option value="all">All Categories</option>
                <option value="CRM">CRM & Pipelines</option>
                <option value="Automation">Workflow Automation</option>
                <option value="Collaboration">Collaboration & Alerts</option>
                <option value="Custom">Custom REST & Webhooks</option>
              </select>
            </div>

            <div style={{ fontSize: '13px', color: 'var(--pm-text-muted)' }}>
              Showing {filteredMarketplace.length} certified connectors
            </div>
          </div>

          <div className="pm-integrations-grid">
            {filteredMarketplace.map((conn) => {
              const connectedInstance = instances.find((inst) => inst.connector_id === conn.id);
              const isConnected = !!connectedInstance;

              return (
                <div key={conn.id} className="pm-integration-card-pro">
                  <div className="pm-integration-card-head">
                    <div>
                      <span className="pm-integration-category">{conn.category}</span>
                      <h4 style={{ margin: '4px 0 0', fontSize: '16px', fontWeight: 600 }}>
                        {conn.name}
                      </h4>
                    </div>
                    <StatusBadge
                      status={isConnected ? 'active' : 'pending'}
                      labelOverride={isConnected ? 'Connected' : 'Available'}
                    />
                  </div>

                  <p className="pm-integration-desc" style={{ marginTop: '8px', minHeight: '38px' }}>
                    {conn.description}
                  </p>

                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', margin: '12px 0' }}>
                    {conn.capabilities?.map((cap) => (
                      <span
                        key={cap}
                        style={{
                          fontSize: '11px',
                          background: 'rgba(255,255,255,0.05)',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          color: 'var(--pm-text-muted)',
                        }}
                      >
                        {cap}
                      </span>
                    ))}
                  </div>

                  <div className="pm-integration-footer">
                    <span style={{ fontSize: '11px', color: 'var(--pm-text-dim)' }}>
                      Auth: {conn.auth_type.toUpperCase()}
                    </span>
                    {isConnected ? (
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <button
                          type="button"
                          className="pm-secondary-btn small"
                          onClick={() => handleTestConnector(connectedInstance.id, conn.name)}
                        >
                          Test
                        </button>
                        <button
                          type="button"
                          className="pm-secondary-btn small"
                          onClick={() => handleOpenFieldMappings(connectedInstance)}
                        >
                          Mappings
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        className="pm-primary-btn small"
                        onClick={() => {
                          setShowConnectModal(conn);
                          setConnectName(conn.name);
                        }}
                      >
                        Install Connector
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: CONNECTED APPS */}
      {/* ========================================================================= */}
      {activeTab === 'connected' && (
        <div>
          {instances.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: '48px 24px',
                background: 'var(--pm-surface)',
                borderRadius: 'var(--pm-radius)',
                border: '1px solid var(--pm-border)',
              }}
            >
              <Plug size={40} color="var(--pm-text-dim)" style={{ marginBottom: '12px' }} />
              <h3>No Integrations Connected Yet</h3>
              <p style={{ color: 'var(--pm-text-muted)', maxWidth: '440px', margin: '8px auto 20px' }}>
                Connect your CRM, automation suites, or alert tools to automatically synchronize leads,
                contacts, and WhatsApp conversations.
              </p>
              <button
                type="button"
                className="pm-primary-btn"
                onClick={() => setActiveTab('marketplace')}
              >
                Browse Connector Marketplace
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {instances.map((inst) => (
                <div
                  key={inst.id}
                  style={{
                    background: 'var(--pm-surface)',
                    border: '1px solid var(--pm-border)',
                    borderRadius: 'var(--pm-radius)',
                    padding: '18px 22px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '16px',
                  }}
                >
                  <div style={{ display: 'flex', gap: '14px', alignItems: 'center' }}>
                    <div
                      style={{
                        width: '42px',
                        height: '42px',
                        borderRadius: '8px',
                        background: 'rgba(147, 132, 242, 0.15)',
                        color: 'var(--pm-primary)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <Plug size={22} />
                    </div>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <h4 style={{ margin: 0, fontSize: '15px' }}>{inst.name}</h4>
                        <StatusBadge
                          status={inst.status === 'connected' ? 'active' : 'error'}
                          labelOverride={inst.health_status}
                        />
                      </div>
                      <div
                        style={{
                          fontSize: '12px',
                          color: 'var(--pm-text-muted)',
                          marginTop: '4px',
                          display: 'flex',
                          gap: '12px',
                        }}
                      >
                        <span>ID: {inst.connector_id}</span>
                        <span>Sync: {inst.sync_direction}</span>
                        <span>Interval: {inst.sync_interval_minutes}m</span>
                        <span>Last sync: {inst.last_sync_at ? new Date(inst.last_sync_at).toLocaleString() : 'Never'}</span>
                      </div>
                      {inst.last_error && (
                        <div
                          style={{
                            fontSize: '11px',
                            color: 'var(--pm-danger)',
                            marginTop: '4px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <AlertTriangle size={12} />
                          <span>{inst.last_error}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <button
                      type="button"
                      className="pm-secondary-btn small"
                      onClick={() => handleTestConnector(inst.id, inst.name)}
                    >
                      Test Connection
                    </button>
                    <button
                      type="button"
                      className="pm-secondary-btn small"
                      onClick={() => handleOpenFieldMappings(inst)}
                    >
                      Field Mappings
                    </button>
                    <button
                      type="button"
                      className="pm-secondary-btn small danger"
                      onClick={() => handleDisconnectConnector(inst.id, inst.name)}
                    >
                      Disconnect
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: API KEYS & SERVICE ACCOUNTS */}
      {/* ========================================================================= */}
      {activeTab === 'api_keys' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
          {/* Service Accounts Block */}
          <div
            style={{
              background: 'var(--pm-surface)',
              border: '1px solid var(--pm-border)',
              borderRadius: 'var(--pm-radius)',
              padding: '20px',
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '16px',
              }}
            >
              <div>
                <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>Service Accounts</h3>
                <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--pm-text-muted)' }}>
                  Tenant-scoped machine identities for daemon jobs, microservices, and external integrations.
                </p>
              </div>
              <button
                type="button"
                className="pm-primary-btn small"
                onClick={() => setShowCreateAccountModal(true)}
              >
                <Plus size={14} />
                <span>Create Service Account</span>
              </button>
            </div>

            {serviceAccounts.length === 0 ? (
              <p style={{ fontSize: '13px', color: 'var(--pm-text-dim)', textAlign: 'center', padding: '16px 0' }}>
                No service accounts created yet.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {serviceAccounts.map((sa) => (
                  <div
                    key={sa.id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '10px 14px',
                      background: 'rgba(255,255,255,0.02)',
                      border: '1px solid var(--pm-border-subtle)',
                      borderRadius: '6px',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontWeight: 600, fontSize: '14px' }}>{sa.name}</span>
                        <StatusBadge
                          status={sa.status === 'active' ? 'active' : 'disabled'}
                          labelOverride={sa.status}
                        />
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--pm-text-muted)', marginTop: '2px' }}>
                        {sa.description || 'No description provided'} • Created: {new Date(sa.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <button
                      type="button"
                      className="pm-secondary-btn small danger"
                      onClick={() => handleDeleteServiceAccount(sa.id, sa.name)}
                      title="Delete service account and revoke all its keys"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* API Keys Block */}
          <div
            style={{
              background: 'var(--pm-surface)',
              border: '1px solid var(--pm-border)',
              borderRadius: 'var(--pm-radius)',
              padding: '20px',
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '16px',
              }}
            >
              <div>
                <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>API Keys</h3>
                <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--pm-text-muted)' }}>
                  Cryptographically hashed credentials prefixed with <code>cvx_live_</code> or <code>cvx_test_</code>. Plaintext keys are shown only once upon creation.
                </p>
              </div>
              <button
                type="button"
                className="pm-primary-btn small"
                onClick={() => setShowCreateKeyModal(true)}
              >
                <Plus size={14} />
                <span>Generate New API Key</span>
              </button>
            </div>

            <DataTable<ApiKeyItem>
              columns={[
                {
                  key: 'key_prefix',
                  header: 'Key Prefix',
                  render: (k) => (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Key size={13} color="var(--pm-primary)" />
                      <code style={{ fontSize: '13px', color: 'var(--pm-primary)' }}>
                        {k.key_prefix}...
                      </code>
                    </div>
                  ),
                },
                {
                  key: 'service_account',
                  header: 'Service Account',
                  render: (k) => k.service_account_name || 'Tenant Default',
                },
                {
                  key: 'scopes',
                  header: 'Granted Scopes',
                  render: (k) => (
                    <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', maxWidth: '240px' }}>
                      {k.scopes.slice(0, 3).map((s) => (
                        <span
                          key={s}
                          style={{
                            fontSize: '10px',
                            background: 'rgba(255,255,255,0.06)',
                            padding: '1px 6px',
                            borderRadius: '3px',
                          }}
                        >
                          {s}
                        </span>
                      ))}
                      {k.scopes.length > 3 && (
                        <span style={{ fontSize: '10px', color: 'var(--pm-text-dim)' }}>
                          +{k.scopes.length - 3} more
                        </span>
                      )}
                    </div>
                  ),
                },
                {
                  key: 'allowed_ips',
                  header: 'IP Restrictions',
                  render: (k) =>
                    k.allowed_ips?.length > 0 ? (
                      <span style={{ fontSize: '12px' }}>{k.allowed_ips.join(', ')}</span>
                    ) : (
                      <span style={{ fontSize: '12px', color: 'var(--pm-text-dim)' }}>Any IP (Unrestricted)</span>
                    ),
                },
                {
                  key: 'last_used',
                  header: 'Last Used',
                  render: (k) =>
                    k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : 'Never',
                },
                {
                  key: 'status',
                  header: 'Status',
                  render: (k) => (
                    <StatusBadge
                      status={k.status === 'active' ? 'active' : 'disabled'}
                      labelOverride={k.status}
                    />
                  ),
                },
                {
                  key: 'actions',
                  header: '',
                  align: 'right',
                  render: (k) =>
                    k.status === 'active' ? (
                      <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                        <button
                          type="button"
                          className="pm-secondary-btn small"
                          onClick={() => handleRotateApiKey(k.id, k.key_prefix)}
                          title="Rotate key (replaces with new secret)"
                        >
                          Rotate
                        </button>
                        <button
                          type="button"
                          className="pm-secondary-btn small danger"
                          onClick={() => handleRevokeApiKey(k.id, k.key_prefix)}
                          title="Revoke key immediately"
                        >
                          Revoke
                        </button>
                      </div>
                    ) : (
                      <span style={{ fontSize: '12px', color: 'var(--pm-text-dim)' }}>Revoked</span>
                    ),
                },
              ]}
              data={apiKeys}
              emptyMessage="No API keys generated yet. Click 'Generate New API Key' above to get started."
            />
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: WEBHOOK ENDPOINTS */}
      {/* ========================================================================= */}
      {activeTab === 'webhooks' && (
        <div
          style={{
            background: 'var(--pm-surface)',
            border: '1px solid var(--pm-border)',
            borderRadius: 'var(--pm-radius)',
            padding: '20px',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '16px',
            }}
          >
            <div>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>Outbound Webhooks</h3>
              <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--pm-text-muted)' }}>
                Real-time event notification endpoints signed with HMAC-SHA256 with transactional outbox delivery and SSRF protection.
              </p>
            </div>
            <button
              type="button"
              className="pm-primary-btn small"
              onClick={() => setShowCreateWebhookModal(true)}
            >
              <Plus size={14} />
              <span>Add Webhook Endpoint</span>
            </button>
          </div>

          <DataTable<WebhookEndpointItem>
            columns={[
              {
                key: 'name',
                header: 'Endpoint Name',
                render: (wh) => (
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '14px' }}>{wh.name}</div>
                    <code style={{ fontSize: '11px', color: 'var(--pm-text-muted)' }}>{wh.url}</code>
                  </div>
                ),
              },
              {
                key: 'events',
                header: 'Subscribed Events',
                render: (wh) => (
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', maxWidth: '300px' }}>
                    {wh.event_filters.map((ev) => (
                      <span
                        key={ev}
                        style={{
                          fontSize: '10px',
                          background: 'rgba(255,255,255,0.06)',
                          padding: '1px 6px',
                          borderRadius: '3px',
                        }}
                      >
                        {ev}
                      </span>
                    ))}
                  </div>
                ),
              },
              {
                key: 'version',
                header: 'API Version',
                render: (wh) => (
                  <span style={{ fontSize: '12px', fontWeight: 500 }}>{wh.api_version}</span>
                ),
              },
              {
                key: 'status',
                header: 'Status',
                render: (wh) => (
                  <StatusBadge
                    status={wh.status === 'active' ? 'active' : 'disabled'}
                    labelOverride={wh.status}
                  />
                ),
              },
              {
                key: 'actions',
                header: '',
                align: 'right',
                render: (wh) => (
                  <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                    <button
                      type="button"
                      className="pm-secondary-btn small"
                      onClick={() => handleTestWebhookPing(wh.id, wh.name)}
                      title="Send test ping event"
                    >
                      <Play size={12} />
                      <span>Ping</span>
                    </button>
                    <button
                      type="button"
                      className="pm-secondary-btn small"
                      onClick={() => handleRotateWebhookSecret(wh.id, wh.name)}
                      title="Rotate signing secret"
                    >
                      <RotateCw size={12} />
                      <span>Secret</span>
                    </button>
                    <button
                      type="button"
                      className="pm-secondary-btn small danger"
                      onClick={() => handleDeleteWebhook(wh.id, wh.name)}
                      title="Delete endpoint"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                ),
              },
            ]}
            data={webhooks}
            emptyMessage="No webhook endpoints configured. Click 'Add Webhook Endpoint' to start receiving events."
          />
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 5: WEBHOOK DELIVERIES & DLQ */}
      {/* ========================================================================= */}
      {activeTab === 'deliveries' && (
        <div
          style={{
            background: 'var(--pm-surface)',
            border: '1px solid var(--pm-border)',
            borderRadius: 'var(--pm-radius)',
            padding: '20px',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '16px',
            }}
          >
            <div>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>
                Webhook Deliveries & Dead Letter Queue (DLQ)
              </h3>
              <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--pm-text-muted)' }}>
                Track delivery latency, HTTP response statuses, exponential backoff retries, and trigger manual replays.
              </p>
            </div>
            <button
              type="button"
              className="pm-secondary-btn small"
              onClick={loadAllData}
              disabled={loading}
            >
              <RefreshCw size={13} className={loading ? 'pm-spin' : ''} />
              <span>Refresh Log</span>
            </button>
          </div>

          <DataTable<WebhookDeliveryItem>
            columns={[
              {
                key: 'event_type',
                header: 'Event Type',
                render: (d) => (
                  <div>
                    <span style={{ fontWeight: 600, fontSize: '13px' }}>{d.event_type}</span>
                    <div style={{ fontSize: '11px', color: 'var(--pm-text-dim)' }}>
                      ID: {d.event_id?.slice(0, 16)}...
                    </div>
                  </div>
                ),
              },
              {
                key: 'endpoint',
                header: 'Destination Endpoint',
                render: (d) => (
                  <div style={{ maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <span style={{ fontSize: '13px' }}>{d.endpoint_name || 'Webhook'}</span>
                    <div style={{ fontSize: '11px', color: 'var(--pm-text-muted)' }}>{d.endpoint_url}</div>
                  </div>
                ),
              },
              {
                key: 'http_status',
                header: 'HTTP Code',
                render: (d) => {
                  const is2xx = d.http_status && d.http_status >= 200 && d.http_status < 300;
                  return (
                    <span
                      style={{
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: 600,
                        background: is2xx ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                        color: is2xx ? 'var(--pm-success)' : 'var(--pm-danger)',
                      }}
                    >
                      {d.http_status ? `HTTP ${d.http_status}` : 'ERR / TIMEOUT'}
                    </span>
                  );
                },
              },
              {
                key: 'attempt',
                header: 'Attempt #',
                render: (d) => `Attempt ${d.attempt_number}`,
              },
              {
                key: 'duration',
                header: 'Duration',
                render: (d) => `${d.duration_ms} ms`,
              },
              {
                key: 'status',
                header: 'Delivery State',
                render: (d) => (
                  <StatusBadge
                    status={
                      d.status === 'success'
                        ? 'active'
                        : d.status === 'dlq'
                        ? 'error'
                        : 'pending'
                    }
                    labelOverride={d.status.toUpperCase()}
                  />
                ),
              },
              {
                key: 'created_at',
                header: 'Dispatched At',
                render: (d) => new Date(d.created_at).toLocaleTimeString(),
              },
              {
                key: 'actions',
                header: '',
                align: 'right',
                render: (d) => (
                  <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                    <button
                      type="button"
                      className="pm-secondary-btn small"
                      onClick={() => setInspectDelivery(d)}
                    >
                      Inspect
                    </button>
                    <button
                      type="button"
                      className="pm-secondary-btn small"
                      onClick={() => handleReplayDelivery(d.id)}
                      title="Audited manual replay"
                    >
                      <RotateCw size={12} />
                      <span>Replay</span>
                    </button>
                  </div>
                ),
              },
            ]}
            data={deliveries}
            emptyMessage="No webhook deliveries recorded yet. Outbound dispatches will appear here in real time."
          />
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 6: LIVE API LOGS */}
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
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '16px',
            }}
          >
            <div>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>
                Live Integration API Logs
              </h3>
              <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--pm-text-muted)' }}>
                Structured audit logs of incoming /api/v1/ requests. Authorization secrets and PII are redacted.
              </p>
            </div>
            <button
              type="button"
              className="pm-secondary-btn small"
              onClick={loadAllData}
              disabled={loading}
            >
              <RefreshCw size={13} className={loading ? 'pm-spin' : ''} />
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
                render: (l) => {
                  const colors: Record<string, string> = {
                    GET: '#3b82f6',
                    POST: '#10b981',
                    PUT: '#f59e0b',
                    PATCH: '#8b5cf6',
                    DELETE: '#ef4444',
                  };
                  return (
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        color: colors[l.method] || 'var(--pm-text)',
                        background: 'rgba(255,255,255,0.06)',
                        padding: '2px 6px',
                        borderRadius: '4px',
                      }}
                    >
                      {l.method}
                    </span>
                  );
                },
              },
              {
                key: 'path',
                header: 'Path',
                render: (l) => <code style={{ fontSize: '12px' }}>{l.path}</code>,
              },
              {
                key: 'status',
                header: 'Status',
                render: (l) => {
                  const isOk = l.status_code >= 200 && l.status_code < 300;
                  const isRateLimit = l.status_code === 429;
                  return (
                    <span
                      style={{
                        fontSize: '12px',
                        fontWeight: 600,
                        color: isOk ? 'var(--pm-success)' : isRateLimit ? 'var(--pm-warning)' : 'var(--pm-danger)',
                      }}
                    >
                      {l.status_code}
                    </span>
                  );
                },
              },
              {
                key: 'duration',
                header: 'Latency',
                render: (l) => `${l.duration_ms} ms`,
              },
              {
                key: 'principal',
                header: 'Principal',
                render: (l) => (
                  <span style={{ fontSize: '12px' }}>
                    {l.principal_type}: {l.principal_id?.slice(0, 10)}...
                  </span>
                ),
              },
              {
                key: 'ip_address',
                header: 'Client IP',
                render: (l) => <span style={{ fontSize: '12px' }}>{l.ip_address}</span>,
              },
              {
                key: 'request_id',
                header: 'Request ID',
                render: (l) => (
                  <span style={{ fontSize: '11px', color: 'var(--pm-text-dim)' }}>
                    {l.request_id?.slice(0, 14)}...
                  </span>
                ),
              },
            ]}
            data={apiLogs}
            emptyMessage="No API logs recorded yet. Inbound API requests to /api/v1/ will appear here."
          />
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 7: AUDIT TRAIL */}
      {/* ========================================================================= */}
      {activeTab === 'audit' && (
        <div
          style={{
            background: 'var(--pm-surface)',
            border: '1px solid var(--pm-border)',
            borderRadius: 'var(--pm-radius)',
            padding: '20px',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '16px',
            }}
          >
            <div>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>
                Tamper-Evident Forensic Audit Trail
              </h3>
              <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--pm-text-muted)' }}>
                Hash-chained immutable administrative actions for integrations, credentials, secrets, and manual replays.
              </p>
            </div>
            <button
              type="button"
              className="pm-secondary-btn small"
              onClick={loadAllData}
              disabled={loading}
            >
              <RefreshCw size={13} className={loading ? 'pm-spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>

          <DataTable<any>
            columns={[
              {
                key: 'timestamp',
                header: 'Timestamp',
                render: (a) => new Date(a.timestamp).toLocaleString(),
              },
              {
                key: 'action',
                header: 'Action',
                render: (a) => (
                  <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--pm-primary)' }}>
                    {a.action}
                  </span>
                ),
              },
              {
                key: 'actor',
                header: 'Actor',
                render: (a) => a.actor || 'System / Platform User',
              },
              {
                key: 'ip_address',
                header: 'IP Address',
                render: (a) => a.ip_address || '127.0.0.1',
              },
              {
                key: 'hash_chain',
                header: 'Integrity Seal',
                render: (a) => (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Shield size={12} color="var(--pm-success)" />
                    <code style={{ fontSize: '11px', color: 'var(--pm-text-dim)' }}>
                      {a.event_hash ? `${a.event_hash.slice(0, 16)}...` : 'VERIFIED'}
                    </code>
                  </div>
                ),
              },
            ]}
            data={auditLogs}
            emptyMessage="No audit records logged yet."
          />
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: CREATE SERVICE ACCOUNT */}
      {/* ========================================================================= */}
      {showCreateAccountModal && (
        <div className="pm-modal-overlay">
          <div className="pm-modal-content" style={{ maxWidth: '480px' }}>
            <div className="pm-modal-header">
              <h3>Create Service Account</h3>
              <button
                type="button"
                className="pm-modal-close"
                onClick={() => setShowCreateAccountModal(false)}
              >
                ×
              </button>
            </div>
            <div className="pm-modal-body">
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px' }}>
                  Account Name *
                </label>
                <input
                  type="text"
                  placeholder="e.g. ERP Pipeline Worker"
                  value={newAccountName}
                  onChange={(e) => setNewAccountName(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    background: 'var(--pm-surface-alt)',
                    border: '1px solid var(--pm-border)',
                    borderRadius: 'var(--pm-radius-sm)',
                  }}
                />
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px' }}>
                  Description (Optional)
                </label>
                <textarea
                  placeholder="Purpose of this automated integration account..."
                  value={newAccountDesc}
                  onChange={(e) => setNewAccountDesc(e.target.value)}
                  rows={3}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    background: 'var(--pm-surface-alt)',
                    border: '1px solid var(--pm-border)',
                    borderRadius: 'var(--pm-radius-sm)',
                  }}
                />
              </div>
            </div>
            <div className="pm-modal-footer">
              <button
                type="button"
                className="pm-secondary-btn"
                onClick={() => setShowCreateAccountModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="pm-primary-btn"
                onClick={handleCreateServiceAccount}
              >
                Create Account
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: CREATE API KEY */}
      {/* ========================================================================= */}
      {showCreateKeyModal && (
        <div className="pm-modal-overlay">
          <div className="pm-modal-content" style={{ maxWidth: '640px', maxHeight: '85vh', overflowY: 'auto' }}>
            <div className="pm-modal-header">
              <h3>Generate New API Key</h3>
              <button
                type="button"
                className="pm-modal-close"
                onClick={() => setShowCreateKeyModal(false)}
              >
                ×
              </button>
            </div>
            <div className="pm-modal-body">
              {/* Service Account selector */}
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px' }}>
                  Service Account Identity
                </label>
                <select
                  value={newKeyServiceAccountId}
                  onChange={(e) => setNewKeyServiceAccountId(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    background: 'var(--pm-surface-alt)',
                    border: '1px solid var(--pm-border)',
                    borderRadius: 'var(--pm-radius-sm)',
                  }}
                >
                  <option value="">Default Workspace Service Account</option>
                  {serviceAccounts.map((sa) => (
                    <option key={sa.id} value={sa.id}>
                      {sa.name} ({sa.status})
                    </option>
                  ))}
                </select>
              </div>

              {/* Environment */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px' }}>
                    Key Environment
                  </label>
                  <select
                    value={newKeyEnv}
                    onChange={(e) => setNewKeyEnv(e.target.value as any)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      background: 'var(--pm-surface-alt)',
                      border: '1px solid var(--pm-border)',
                      borderRadius: 'var(--pm-radius-sm)',
                    }}
                  >
                    <option value="live">Live (cvx_live_...)</option>
                    <option value="test">Test / Sandbox (cvx_test_...)</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px' }}>
                    Expiration Policy
                  </label>
                  <select
                    value={newKeyExpiresDays === null ? 'never' : String(newKeyExpiresDays)}
                    onChange={(e) =>
                      setNewKeyExpiresDays(e.target.value === 'never' ? null : Number(e.target.value))
                    }
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      background: 'var(--pm-surface-alt)',
                      border: '1px solid var(--pm-border)',
                      borderRadius: 'var(--pm-radius-sm)',
                    }}
                  >
                    <option value="30">30 Days</option>
                    <option value="90">90 Days (Recommended)</option>
                    <option value="180">180 Days</option>
                    <option value="365">1 Year</option>
                    <option value="never">Never Expire</option>
                  </select>
                </div>
              </div>

              {/* IP Allowlist */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px' }}>
                  IP Address Allowlist (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. 198.51.100.4, 203.0.113.0/24 (leave blank for any IP)"
                  value={newKeyIpAllowlist}
                  onChange={(e) => setNewKeyIpAllowlist(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    background: 'var(--pm-surface-alt)',
                    border: '1px solid var(--pm-border)',
                    borderRadius: 'var(--pm-radius-sm)',
                  }}
                />
                <span style={{ fontSize: '11px', color: 'var(--pm-text-dim)' }}>
                  Comma-separated list of IPv4/IPv6 addresses or CIDR subnets allowed to use this key.
                </span>
              </div>

              {/* Granular Scopes */}
              <div>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '8px',
                  }}
                >
                  <label style={{ fontSize: '13px', fontWeight: 600 }}>Granular API Scopes</label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      type="button"
                      style={{ fontSize: '11px', color: 'var(--pm-primary)' }}
                      onClick={() =>
                        setNewKeyScopes(scopeCategories.flatMap((c) => c.scopes.map((s) => s.code)))
                      }
                    >
                      Select All
                    </button>
                    <button
                      type="button"
                      style={{ fontSize: '11px', color: 'var(--pm-text-dim)' }}
                      onClick={() => setNewKeyScopes([])}
                    >
                      Clear
                    </button>
                  </div>
                </div>

                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                    maxHeight: '260px',
                    overflowY: 'auto',
                    padding: '8px',
                    background: 'var(--pm-surface-alt)',
                    borderRadius: 'var(--pm-radius-sm)',
                    border: '1px solid var(--pm-border)',
                  }}
                >
                  {scopeCategories.map((cat) => (
                    <div key={cat.category}>
                      <div
                        style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          color: 'var(--pm-text-muted)',
                          marginBottom: '4px',
                        }}
                      >
                        {cat.category}
                      </div>
                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                          gap: '6px',
                        }}
                      >
                        {cat.scopes.map((s) => {
                          const checked = newKeyScopes.includes(s.code);
                          return (
                            <label
                              key={s.code}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                fontSize: '12px',
                                cursor: 'pointer',
                                padding: '4px 6px',
                                borderRadius: '4px',
                                background: checked ? 'rgba(147, 132, 242, 0.1)' : 'transparent',
                              }}
                            >
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setNewKeyScopes((p) => [...p, s.code]);
                                  } else {
                                    setNewKeyScopes((p) => p.filter((x) => x !== s.code));
                                  }
                                }}
                              />
                              <div>
                                <div style={{ fontFamily: 'monospace' }}>{s.code}</div>
                                <div style={{ fontSize: '10px', color: 'var(--pm-text-dim)' }}>
                                  {s.desc}
                                </div>
                              </div>
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="pm-modal-footer">
              <button
                type="button"
                className="pm-secondary-btn"
                onClick={() => setShowCreateKeyModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="pm-primary-btn"
                onClick={handleCreateApiKey}
                disabled={newKeyScopes.length === 0}
              >
                Generate API Key
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: ONE-TIME SECRET REVEAL */}
      {/* ========================================================================= */}
      {showCreatedKeyRevealModal && revealedKeyResult && (
        <div className="pm-modal-overlay">
          <div className="pm-modal-content" style={{ maxWidth: '580px' }}>
            <div className="pm-modal-header">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--pm-success)' }}>
                <CheckCircle2 size={18} />
                <span>API Key Generated Successfully</span>
              </h3>
              <button
                type="button"
                className="pm-modal-close"
                onClick={() => {
                  setShowCreatedKeyRevealModal(false);
                  setRevealedKeyResult(null);
                }}
              >
                ×
              </button>
            </div>
            <div className="pm-modal-body">
              <div
                style={{
                  background: 'rgba(245, 158, 11, 0.12)',
                  border: '1px solid var(--pm-warning)',
                  borderRadius: 'var(--pm-radius-sm)',
                  padding: '12px 14px',
                  marginBottom: '16px',
                  fontSize: '13px',
                  color: 'var(--pm-warning)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px',
                }}
              >
                <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <strong>Important Security Notice:</strong>
                  <div>
                    This complete secret key will only be shown once. If you lose this key, you will have to rotate or generate a new one. Convernix only stores a salted SHA-256 cryptographic hash.
                  </div>
                </div>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px' }}>
                  Your Secret API Key
                </label>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    background: 'var(--pm-surface-alt)',
                    border: '1px solid var(--pm-border)',
                    borderRadius: 'var(--pm-radius-sm)',
                    padding: '8px 12px',
                    gap: '8px',
                  }}
                >
                  <code
                    style={{
                      fontFamily: 'monospace',
                      fontSize: '13px',
                      color: 'var(--pm-primary)',
                      wordBreak: 'break-all',
                      flex: 1,
                    }}
                  >
                    {revealedKeyResult.plaintext_key}
                  </code>
                  <button
                    type="button"
                    className="pm-secondary-btn small"
                    onClick={() => handleCopy(revealedKeyResult.plaintext_key)}
                    style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                  >
                    {keyCopied ? <Check size={13} color="var(--pm-success)" /> : <Copy size={13} />}
                    <span>{keyCopied ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
              </div>

              <div style={{ fontSize: '12px', color: 'var(--pm-text-muted)' }}>
                <strong>Example Usage Header:</strong>
                <pre
                  style={{
                    background: 'rgba(0,0,0,0.3)',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    marginTop: '4px',
                    overflowX: 'auto',
                  }}
                >
                  curl -H "X-API-Key: {revealedKeyResult.plaintext_key}" https://api.convernix.com/api/v1/leads/
                </pre>
              </div>
            </div>
            <div className="pm-modal-footer">
              <button
                type="button"
                className="pm-primary-btn"
                onClick={() => {
                  setShowCreatedKeyRevealModal(false);
                  setRevealedKeyResult(null);
                }}
              >
                I have safely stored this key
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: ADD WEBHOOK ENDPOINT */}
      {/* ========================================================================= */}
      {showCreateWebhookModal && (
        <div className="pm-modal-overlay">
          <div className="pm-modal-content" style={{ maxWidth: '580px', maxHeight: '85vh', overflowY: 'auto' }}>
            <div className="pm-modal-header">
              <h3>Register Webhook Endpoint</h3>
              <button
                type="button"
                className="pm-modal-close"
                onClick={() => setShowCreateWebhookModal(false)}
              >
                ×
              </button>
            </div>
            <div className="pm-modal-body">
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px' }}>
                  Endpoint Name *
                </label>
                <input
                  type="text"
                  placeholder="e.g. Production CRM Webhook Listener"
                  value={newWebhookName}
                  onChange={(e) => setNewWebhookName(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    background: 'var(--pm-surface-alt)',
                    border: '1px solid var(--pm-border)',
                    borderRadius: 'var(--pm-radius-sm)',
                  }}
                />
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px' }}>
                  Destination URL (HTTPS Recommended) *
                </label>
                <input
                  type="url"
                  placeholder="https://api.yourdomain.com/webhooks/convernix"
                  value={newWebhookUrl}
                  onChange={(e) => setNewWebhookUrl(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    background: 'var(--pm-surface-alt)',
                    border: '1px solid var(--pm-border)',
                    borderRadius: 'var(--pm-radius-sm)',
                  }}
                />
                <span style={{ fontSize: '11px', color: 'var(--pm-text-dim)' }}>
                  SSRF Protection: Localhost, private RFC 1918 ranges, and cloud metadata endpoints are strictly blocked.
                </span>
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px' }}>
                  Payload Version
                </label>
                <select
                  value={newWebhookVersion}
                  onChange={(e) => setNewWebhookVersion(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    background: 'var(--pm-surface-alt)',
                    border: '1px solid var(--pm-border)',
                    borderRadius: 'var(--pm-radius-sm)',
                  }}
                >
                  <option value="v1">v1 (Standard Domain Event Schema)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px' }}>
                  Subscribed Events
                </label>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                    gap: '6px',
                    maxHeight: '200px',
                    overflowY: 'auto',
                    padding: '8px',
                    background: 'var(--pm-surface-alt)',
                    borderRadius: 'var(--pm-radius-sm)',
                    border: '1px solid var(--pm-border)',
                  }}
                >
                  {allAvailableEvents.map((ev) => {
                    const checked = newWebhookEvents.includes(ev.code);
                    return (
                      <label
                        key={ev.code}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontSize: '12px',
                          cursor: 'pointer',
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setNewWebhookEvents((p) => [...p, ev.code]);
                            } else {
                              setNewWebhookEvents((p) => p.filter((x) => x !== ev.code));
                            }
                          }}
                        />
                        <span>{ev.label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            </div>
            <div className="pm-modal-footer">
              <button
                type="button"
                className="pm-secondary-btn"
                onClick={() => setShowCreateWebhookModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="pm-primary-btn"
                onClick={handleCreateWebhook}
                disabled={newWebhookEvents.length === 0}
              >
                Register Webhook
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: WEBHOOK SECRET REVEAL */}
      {/* ========================================================================= */}
      {showRevealedWebhookSecret && (
        <div className="pm-modal-overlay">
          <div className="pm-modal-content" style={{ maxWidth: '540px' }}>
            <div className="pm-modal-header">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Key size={18} color="var(--pm-primary)" />
                <span>Webhook Signing Secret</span>
              </h3>
              <button
                type="button"
                className="pm-modal-close"
                onClick={() => setShowRevealedWebhookSecret(null)}
              >
                ×
              </button>
            </div>
            <div className="pm-modal-body">
              <p style={{ fontSize: '13px', color: 'var(--pm-text-muted)' }}>
                Use this secret key to verify the <code>X-Convernix-Signature</code> header on incoming webhook deliveries using HMAC-SHA256.
              </p>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  background: 'var(--pm-surface-alt)',
                  border: '1px solid var(--pm-border)',
                  borderRadius: 'var(--pm-radius-sm)',
                  padding: '8px 12px',
                  gap: '8px',
                  margin: '14px 0',
                }}
              >
                <code
                  style={{
                    fontFamily: 'monospace',
                    fontSize: '13px',
                    color: 'var(--pm-primary)',
                    flex: 1,
                    wordBreak: 'break-all',
                  }}
                >
                  {showRevealedWebhookSecret.secret}
                </code>
                <button
                  type="button"
                  className="pm-secondary-btn small"
                  onClick={() => handleCopy(showRevealedWebhookSecret.secret)}
                >
                  Copy
                </button>
              </div>

              <div style={{ fontSize: '12px', color: 'var(--pm-text-dim)' }}>
                Canonical signature input is computed as <code>timestamp + "." + raw_payload</code>.
              </div>
            </div>
            <div className="pm-modal-footer">
              <button
                type="button"
                className="pm-primary-btn"
                onClick={() => setShowRevealedWebhookSecret(null)}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: INSPECT WEBHOOK DELIVERY */}
      {/* ========================================================================= */}
      {inspectDelivery && (
        <div className="pm-modal-overlay">
          <div className="pm-modal-content" style={{ maxWidth: '680px', maxHeight: '85vh', overflowY: 'auto' }}>
            <div className="pm-modal-header">
              <h3>Webhook Delivery Inspector</h3>
              <button
                type="button"
                className="pm-modal-close"
                onClick={() => setInspectDelivery(null)}
              >
                ×
              </button>
            </div>
            <div className="pm-modal-body">
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: '12px',
                  marginBottom: '16px',
                  background: 'var(--pm-surface-alt)',
                  padding: '12px',
                  borderRadius: 'var(--pm-radius-sm)',
                }}
              >
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--pm-text-muted)' }}>Status</div>
                  <div style={{ fontWeight: 600, fontSize: '14px' }}>
                    {inspectDelivery.http_status ? `HTTP ${inspectDelivery.http_status}` : 'Error'}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--pm-text-muted)' }}>Duration</div>
                  <div style={{ fontWeight: 600, fontSize: '14px' }}>{inspectDelivery.duration_ms} ms</div>
                </div>
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--pm-text-muted)' }}>Attempt</div>
                  <div style={{ fontWeight: 600, fontSize: '14px' }}>#{inspectDelivery.attempt_number}</div>
                </div>
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>
                  Request Headers
                </label>
                <pre
                  style={{
                    background: 'rgba(0,0,0,0.3)',
                    padding: '8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    maxHeight: '100px',
                    overflowY: 'auto',
                  }}
                >
                  {JSON.stringify(inspectDelivery.request_headers || {}, null, 2)}
                </pre>
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>
                  Dispatched Payload (JSON)
                </label>
                <pre
                  style={{
                    background: 'rgba(0,0,0,0.3)',
                    padding: '8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    maxHeight: '160px',
                    overflowY: 'auto',
                  }}
                >
                  {JSON.stringify(inspectDelivery.request_body || {}, null, 2)}
                </pre>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>
                  Response Body
                </label>
                <pre
                  style={{
                    background: 'rgba(0,0,0,0.3)',
                    padding: '8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    maxHeight: '120px',
                    overflowY: 'auto',
                  }}
                >
                  {inspectDelivery.response_body || '(Empty response body)'}
                </pre>
              </div>
            </div>
            <div className="pm-modal-footer">
              <button
                type="button"
                className="pm-secondary-btn"
                onClick={() => setInspectDelivery(null)}
              >
                Close
              </button>
              <button
                type="button"
                className="pm-primary-btn"
                onClick={() => {
                  handleReplayDelivery(inspectDelivery.id);
                  setInspectDelivery(null);
                }}
              >
                Replay Delivery Now
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: CONNECT CONNECTOR */}
      {/* ========================================================================= */}
      {showConnectModal && (
        <div className="pm-modal-overlay">
          <div className="pm-modal-content" style={{ maxWidth: '520px' }}>
            <div className="pm-modal-header">
              <h3>Connect {showConnectModal.name}</h3>
              <button
                type="button"
                className="pm-modal-close"
                onClick={() => setShowConnectModal(null)}
              >
                ×
              </button>
            </div>
            <div className="pm-modal-body">
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px' }}>
                  Integration Display Name
                </label>
                <input
                  type="text"
                  value={connectName}
                  onChange={(e) => setConnectName(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    background: 'var(--pm-surface-alt)',
                    border: '1px solid var(--pm-border)',
                    borderRadius: 'var(--pm-radius-sm)',
                  }}
                />
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px' }}>
                  Sync Direction
                </label>
                <select
                  value={connectSyncDir}
                  onChange={(e) => setConnectSyncDir(e.target.value as any)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    background: 'var(--pm-surface-alt)',
                    border: '1px solid var(--pm-border)',
                    borderRadius: 'var(--pm-radius-sm)',
                  }}
                >
                  <option value="bidirectional">Bidirectional (Two-Way Sync)</option>
                  <option value="inbound">Inbound Only (External CRM → Convernix)</option>
                  <option value="outbound">Outbound Only (Convernix → External CRM)</option>
                </select>
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px' }}>
                  Connection Settings / Credentials (JSON)
                </label>
                <textarea
                  value={connectConfigJson}
                  onChange={(e) => setConnectConfigJson(e.target.value)}
                  rows={4}
                  style={{
                    width: '100%',
                    fontFamily: 'monospace',
                    fontSize: '12px',
                    padding: '8px 12px',
                    background: 'var(--pm-surface-alt)',
                    border: '1px solid var(--pm-border)',
                    borderRadius: 'var(--pm-radius-sm)',
                  }}
                  placeholder='{"api_key": "...", "base_url": "..."}'
                />
                <span style={{ fontSize: '11px', color: 'var(--pm-text-dim)' }}>
                  All credentials and tokens are encrypted with envelope AES-256-GCM before persistence.
                </span>
              </div>
            </div>
            <div className="pm-modal-footer">
              <button
                type="button"
                className="pm-secondary-btn"
                onClick={() => setShowConnectModal(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="pm-primary-btn"
                onClick={handleConnectConnector}
              >
                Confirm & Connect
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: FIELD MAPPINGS DRAWER */}
      {/* ========================================================================= */}
      {showFieldMappingModal && (
        <div className="pm-modal-overlay">
          <div className="pm-modal-content" style={{ maxWidth: '680px', maxHeight: '85vh', overflowY: 'auto' }}>
            <div className="pm-modal-header">
              <h3>Field Mappings — {showFieldMappingModal.name}</h3>
              <button
                type="button"
                className="pm-modal-close"
                onClick={() => setShowFieldMappingModal(null)}
              >
                ×
              </button>
            </div>
            <div className="pm-modal-body">
              <p style={{ fontSize: '13px', color: 'var(--pm-text-muted)' }}>
                Configure schema field transformations between Convernix entities and external CRM objects.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', margin: '14px 0' }}>
                {fieldMappings.map((m, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr 1fr auto',
                      gap: '8px',
                      alignItems: 'center',
                      background: 'var(--pm-surface-alt)',
                      padding: '8px 12px',
                      borderRadius: 'var(--pm-radius-sm)',
                    }}
                  >
                    <div>
                      <span style={{ fontSize: '11px', color: 'var(--pm-text-dim)' }}>Local Field</span>
                      <div style={{ fontSize: '13px', fontWeight: 500 }}>{m.local_field}</div>
                    </div>
                    <div>
                      <span style={{ fontSize: '11px', color: 'var(--pm-text-dim)' }}>Remote Field</span>
                      <div style={{ fontSize: '13px', fontWeight: 500 }}>{m.remote_field}</div>
                    </div>
                    <div>
                      <span style={{ fontSize: '11px', color: 'var(--pm-text-dim)' }}>Transformation</span>
                      <div style={{ fontSize: '12px' }}>{m.transform_type}</div>
                    </div>
                    <button
                      type="button"
                      className="pm-secondary-btn small danger"
                      onClick={() => setFieldMappings((p) => p.filter((_, i) => i !== idx))}
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))}
              </div>

              {/* Add mapping line */}
              <button
                type="button"
                className="pm-secondary-btn small"
                onClick={() =>
                  setFieldMappings((p) => [
                    ...p,
                    {
                      local_object_type: 'lead',
                      remote_object_type: 'contact',
                      local_field: 'phone_number',
                      remote_field: 'mobilephone',
                      transform_type: 'direct',
                    },
                  ])
                }
                style={{ marginTop: '8px' }}
              >
                <Plus size={13} />
                <span>Add Field Mapping</span>
              </button>
            </div>
            <div className="pm-modal-footer">
              <button
                type="button"
                className="pm-secondary-btn"
                onClick={() => setShowFieldMappingModal(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="pm-primary-btn"
                onClick={handleSaveFieldMappings}
              >
                Save Mappings
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={confirmDialog.isOpen}
        title={confirmDialog.title}
        message={confirmDialog.message}
        danger={confirmDialog.danger}
        confirmText={confirmDialog.confirmText}
        onConfirm={confirmDialog.onConfirm}
        onCancel={() => setConfirmDialog((p) => ({ ...p, isOpen: false }))}
      />
    </div>
  );
}

export default IntegrationsView;
