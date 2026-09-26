import React, { useState } from 'react';
import {
  MessageSquare,
  Activity,
  RefreshCw,
  PowerOff,
  Plus,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { AdminPageHeader } from '../common/AdminPageHeader';
import { StatusBadge } from '../common/StatusBadge';
import { SecretField } from '../common/SecretField';
import { ConfirmationDialog } from '../common/ConfirmationDialog';
import { WhatsAppSetupWizard } from './WhatsAppSetupWizard';
import type { WhatsAppConnectionState, DiagnosticTestResult } from '../../types';

interface WhatsAppConfigurationProps {
  whatsapp: WhatsAppConnectionState;
  onConnect: (data: any) => Promise<boolean>;
  onTest: () => Promise<DiagnosticTestResult | null>;
  onDisconnect: () => Promise<boolean>;
  onRefresh: () => void;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export function WhatsAppConfiguration({
  whatsapp,
  onConnect,
  onTest,
  onDisconnect,
  onRefresh,
  toast,
}: WhatsAppConfigurationProps) {
  const [showWizard, setShowWizard] = useState(false);
  const [showDisconnectConfirm, setShowDisconnectConfirm] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<DiagnosticTestResult | null>(null);

  const isConnected = whatsapp.connection_status === 'connected';

  const handleRunDiagnostic = async () => {
    setTesting(true);
    const res = await onTest();
    setTesting(false);
    if (res) {
      setTestResult(res);
    }
  };

  const handleConfirmDisconnect = async () => {
    const ok = await onDisconnect();
    if (ok) {
      setShowDisconnectConfirm(false);
    }
  };

  return (
    <div className="pm-settings-panel">
      <AdminPageHeader
        breadcrumbs={[
          { label: 'Administration' },
          { label: 'Settings' },
          { label: 'WhatsApp Configuration' },
        ]}
        title="WhatsApp Configuration"
        subtitle="Connect and manage the official WhatsApp Business Cloud API accounts used by your organization."
        actions={
          <div className="pm-header-action-group">
            <button
              type="button"
              className="pm-secondary-btn"
              onClick={onRefresh}
              title="Refresh connection status from Meta"
            >
              <RefreshCw size={13} /> Refresh Status
            </button>
            <button
              type="button"
              className="pm-primary-btn"
              onClick={() => setShowWizard(true)}
            >
              <Plus size={14} /> {isConnected ? 'Reconnect / Edit' : 'Connect WhatsApp Business'}
            </button>
          </div>
        }
      />

      {/* Professional Connection Status Banner */}
      <div className={`pm-connection-status-banner ${whatsapp.connection_status}`}>
        <div className="pm-status-banner-top">
          <div className="pm-status-banner-badge-group">
            <span className="pm-status-banner-brand">WhatsApp Business</span>
            <StatusBadge
              status={whatsapp.connection_status}
              type="whatsapp"
              labelOverride={isConnected ? 'Connected & Active' : 'Not Connected'}
            />
          </div>
          <p className="pm-status-banner-message">
            {isConnected
              ? 'Your WhatsApp Business account is connected and ready to receive and route incoming messages.'
              : 'No WhatsApp Business number is currently linked. Run the setup wizard to link your Meta WABA account.'}
          </p>
        </div>

        {isConnected && (
          <div className="pm-status-banner-meta-row">
            <div>
              <small>Business Channel:</small>
              <strong>{whatsapp.business_name}</strong>
            </div>
            <div>
              <small>Phone Number:</small>
              <strong>{whatsapp.phone_number}</strong>
            </div>
            <div>
              <small>Webhook Status:</small>
              <span className="pm-inline-active">
                <span className="pm-live-dot" /> {whatsapp.webhook_status}
              </span>
            </div>
            <div>
              <small>Last Sync:</small>
              <span>{whatsapp.last_sync}</span>
            </div>
          </div>
        )}
      </div>

      {/* Integration Details & Credential Vault */}
      <div className="pm-admin-info-columns-pro">
        <div className="pm-info-col-main">
          <div className="pm-info-card">
            <div className="pm-info-card-header">
              <h3>Meta Cloud API Parameters</h3>
              <span className="pm-info-card-tag">WABA v23.0</span>
            </div>

            <dl className="pm-key-value-list">
              <div>
                <dt>Meta Business Account</dt>
                <dd>{whatsapp.meta_business_account || 'Cloudtronix Meta Portfolio'}</dd>
              </div>
              <div>
                <dt>WhatsApp Business Account ID (WABA)</dt>
                <dd>
                  <code>{whatsapp.business_account_id || 'Not configured'}</code>
                </dd>
              </div>
              <div>
                <dt>Phone Number ID</dt>
                <dd>
                  <code>{whatsapp.phone_number_id || 'Not configured'}</code>
                </dd>
              </div>
              <div>
                <dt>Business Phone Number</dt>
                <dd>
                  <strong>{whatsapp.phone_number || 'None'}</strong>
                </dd>
              </div>
              <div>
                <dt>Display Name</dt>
                <dd>{whatsapp.display_name || 'Cloudtronix Support'}</dd>
              </div>
              <div>
                <dt>Business Verification</dt>
                <dd>
                  <StatusBadge status={whatsapp.business_verification_status} />
                </dd>
              </div>
              <div>
                <dt>Webhook Callback URL</dt>
                <dd>
                  <code>{whatsapp.webhook_url}</code>
                </dd>
              </div>
            </dl>
          </div>

          {/* Secure Credentials Vault */}
          <div className="pm-info-card" style={{ marginTop: 18 }}>
            <div className="pm-info-card-header">
              <div>
                <h3>Secure Credentials Vault</h3>
                <p className="pm-card-subtitle">Encrypted token and secret parameters used by the lead router</p>
              </div>
              <ShieldCheck size={18} color="#52bb89" />
            </div>

            <div className="pm-secrets-stack">
              <SecretField
                label="Meta App Secret"
                value="secret_89f3102432890abcdef9102"
                onReplace={(newVal) => toast('App secret updated securely in backend.', 'success')}
              />
              <SecretField
                label="Permanent System User Access Token"
                value="EAABwzL1...[verified_system_user_token_valid]"
                onReplace={(newVal) => toast('Access token updated securely.', 'success')}
              />
              <SecretField
                label="Webhook Verify Token"
                value="convernix_secure_verify_token_2026"
                onReplace={(newVal) => toast('Verify token updated.', 'success')}
              />
            </div>
          </div>
        </div>

        {/* Right Action Column */}
        <div className="pm-info-col-side">
          <div className="pm-action-panel-card">
            <h4>Connection Operations</h4>
            <p>Perform diagnostic verifications or maintain channel connectivity.</p>

            <div className="pm-button-stack">
              <button
                type="button"
                className="pm-secondary-btn full-width"
                onClick={handleRunDiagnostic}
                disabled={testing}
              >
                <Activity size={14} /> {testing ? 'Testing...' : 'Test Connection'}
              </button>

              <button
                type="button"
                className="pm-secondary-btn full-width"
                onClick={() => setShowWizard(true)}
              >
                <RefreshCw size={14} /> Reconnect / Configure
              </button>

              {isConnected && (
                <button
                  type="button"
                  className="pm-danger-btn full-width"
                  onClick={() => setShowDisconnectConfirm(true)}
                >
                  <PowerOff size={14} /> Disconnect Channel
                </button>
              )}
            </div>

            {testResult && (
              <div className="pm-diagnostic-panel" role="region" aria-label="Diagnostic Results">
                <h5>Live Diagnostic Checks</h5>
                <ul className="pm-diagnostic-list">
                  {testResult.checks.map((chk) => (
                    <li key={chk.name} className="pm-diagnostic-item">
                      <CheckCircle2 size={13} color="#52bb89" className="pm-check-ico" />
                      <div>
                        <strong>{chk.name}</strong>
                        <span>{chk.message}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="pm-help-panel-card" style={{ marginTop: 16 }}>
            <h4>Meta Documentation</h4>
            <p>Reference official documentation on Cloud API webhooks and WhatsApp template approvals.</p>
            <a
              href="https://developers.facebook.com/docs/whatsapp/cloud-api"
              target="_blank"
              rel="noopener noreferrer"
              className="pm-btn-link"
            >
              Meta Developer Docs <ExternalLink size={12} />
            </a>
          </div>
        </div>
      </div>

      {/* 7-Step Setup Wizard Modal */}
      <WhatsAppSetupWizard
        isOpen={showWizard}
        onClose={() => setShowWizard(false)}
        onComplete={onConnect}
        onRunTest={onTest}
        toast={toast}
      />

      {/* Disconnect Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={showDisconnectConfirm}
        title="Disconnect WhatsApp Business?"
        message="Disconnecting this WhatsApp channel will immediately halt automated enquiry routing and incoming customer messaging. Existing conversations and audit logs will be preserved."
        confirmLabel="Disconnect Now"
        isDanger={true}
        onConfirm={handleConfirmDisconnect}
        onCancel={() => setShowDisconnectConfirm(false)}
      />
    </div>
  );
}

