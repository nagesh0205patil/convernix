import React, { useState } from 'react';
import {
  Check,
  ChevronRight,
  ChevronLeft,
  X,
  MessageSquare,
  Key,
  Webhook,
  Activity,
  CheckCircle2,
  AlertCircle,
  Copy,
} from 'lucide-react';
import type { DiagnosticTestResult } from '../../types';

interface WhatsAppSetupWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: (data: any) => Promise<boolean>;
  onRunTest: () => Promise<DiagnosticTestResult | null>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export function WhatsAppSetupWizard({
  isOpen,
  onClose,
  onComplete,
  onRunTest,
  toast,
}: WhatsAppSetupWizardProps) {
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [testResult, setTestResult] = useState<DiagnosticTestResult | null>(null);

  const [wizardData, setWizardData] = useState({
    meta_business_id: 'MBID_89102432890',
    display_name: 'Cloudtronix Support',
    business_portfolio: 'Cloudtronix Meta Portfolio',
    business_account_id: 'WABA_20489102',
    account_name: 'Cloudtronix Official WABA',
    timezone: 'Asia/Kolkata',
    phone_number_id: 'PNID_987654321',
    phone_number: '+91 98765 43210',
    meta_app_id: '89102432890',
    meta_app_secret: '••••••••••••••••••••••••',
    meta_access_token: '••••••••••••••••••••••••••••••••',
    verify_token: 'convernix_secure_verify_token_2026',
    webhook_url: 'https://convernix.example/api/whatsapp/webhook/',
  });

  if (!isOpen) return null;

  const updateField = (field: string, val: string) => {
    setWizardData((prev) => ({ ...prev, [field]: val }));
  };

  const runTest = async () => {
    setBusy(true);
    const res = await onRunTest();
    setBusy(false);
    if (res) {
      setTestResult(res);
    }
  };

  const handleFinish = async () => {
    setBusy(true);
    const ok = await onComplete(wizardData);
    setBusy(false);
    if (ok) {
      toast('WhatsApp Business setup completed successfully!', 'success');
      onClose();
    }
  };

  const stepsMeta = [
    { num: 1, title: 'Meta Business' },
    { num: 2, title: 'WhatsApp Account' },
    { num: 3, title: 'Phone Number' },
    { num: 4, title: 'Credentials' },
    { num: 5, title: 'Webhook' },
    { num: 6, title: 'Connection Test' },
    { num: 7, title: 'Complete' },
  ];

  return (
    <div className="pm-modal-overlay" role="presentation">
      <div
        className="pm-wizard-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="wizard-title"
      >
        <header className="pm-wizard-header">
          <div className="pm-wizard-header-title">
            <span className="pm-wizard-pill">Guided Setup</span>
            <h2 id="wizard-title">Connect WhatsApp Business</h2>
          </div>
          <button type="button" className="pm-modal-close" onClick={onClose} aria-label="Close setup wizard">
            <X size={16} />
          </button>
        </header>

        {/* Wizard Stepper Bar */}
        <div className="pm-wizard-stepper">
          {stepsMeta.map((s) => {
            const isCompleted = step > s.num;
            const isCurrent = step === s.num;

            return (
              <div
                key={s.num}
                className={`pm-wizard-step-node ${isCompleted ? 'completed' : ''} ${isCurrent ? 'current' : ''}`}
              >
                <div className="pm-wizard-node-circle">
                  {isCompleted ? <Check size={12} strokeWidth={3} /> : s.num}
                </div>
                <span className="pm-wizard-node-label">{s.title}</span>
              </div>
            );
          })}
        </div>

        {/* Wizard Body */}
        <div className="pm-wizard-body">
          {step === 1 && (
            <div className="pm-wizard-step-content">
              <h3>Step 1: Meta Business Details</h3>
              <p>Identify your Meta Business Portfolio or Business Manager account.</p>

              <div className="pm-form-field">
                <label>Meta Business ID</label>
                <input
                  type="text"
                  value={wizardData.meta_business_id}
                  onChange={(e) => updateField('meta_business_id', e.target.value)}
                  placeholder="e.g. 102938475601928"
                  required
                />
                <small className="field-help">Found in Meta Business Suite under Business Settings → Business Info</small>
              </div>

              <div className="pm-form-field">
                <label>Meta Business Portfolio Name</label>
                <input
                  type="text"
                  value={wizardData.business_portfolio}
                  onChange={(e) => updateField('business_portfolio', e.target.value)}
                />
              </div>

              <div className="pm-form-field">
                <label>Business Display Name</label>
                <input
                  type="text"
                  value={wizardData.display_name}
                  onChange={(e) => updateField('display_name', e.target.value)}
                />
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="pm-wizard-step-content">
              <h3>Step 2: WhatsApp Business Account (WABA)</h3>
              <p>Link your registered WABA container ID managing phone numbers and message templates.</p>

              <div className="pm-form-field">
                <label>WhatsApp Business Account ID (WABA ID)</label>
                <input
                  type="text"
                  value={wizardData.business_account_id}
                  onChange={(e) => updateField('business_account_id', e.target.value)}
                  placeholder="e.g. 204891029384"
                  required
                />
              </div>

              <div className="pm-form-field">
                <label>Account Label / Internal Name</label>
                <input
                  type="text"
                  value={wizardData.account_name}
                  onChange={(e) => updateField('account_name', e.target.value)}
                />
              </div>

              <div className="pm-form-field">
                <label>Operational Timezone</label>
                <select
                  value={wizardData.timezone}
                  onChange={(e) => updateField('timezone', e.target.value)}
                >
                  <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">America/New_York</option>
                  <option value="Europe/London">Europe/London</option>
                </select>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="pm-wizard-step-content">
              <h3>Step 3: Phone Number Registration</h3>
              <p>Enter the verified WhatsApp Phone Number ID and E.164 number format.</p>

              <div className="pm-form-field">
                <label>Meta Phone Number ID</label>
                <input
                  type="text"
                  value={wizardData.phone_number_id}
                  onChange={(e) => updateField('phone_number_id', e.target.value)}
                  placeholder="e.g. PNID_987654321"
                  required
                />
                <small className="field-help">Located in Meta WhatsApp Manager → Phone Numbers</small>
              </div>

              <div className="pm-form-field">
                <label>Business WhatsApp Phone Number</label>
                <input
                  type="tel"
                  value={wizardData.phone_number}
                  onChange={(e) => updateField('phone_number', e.target.value)}
                  placeholder="+91 98765 43210"
                  required
                />
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="pm-wizard-step-content">
              <h3>Step 4: API Credentials Vault</h3>
              <p>Store your Meta System User Access Token and App Secret securely. Credentials are encrypted at rest.</p>

              <div className="pm-form-field">
                <label>Meta App ID</label>
                <input
                  type="text"
                  value={wizardData.meta_app_id}
                  onChange={(e) => updateField('meta_app_id', e.target.value)}
                />
              </div>

              <div className="pm-form-field">
                <label>Meta App Secret</label>
                <input
                  type="password"
                  value={wizardData.meta_app_secret}
                  onChange={(e) => updateField('meta_app_secret', e.target.value)}
                  placeholder="Enter Meta App Secret..."
                />
              </div>

              <div className="pm-form-field">
                <label>Permanent System User Access Token</label>
                <textarea
                  rows={2}
                  value={wizardData.meta_access_token}
                  onChange={(e) => updateField('meta_access_token', e.target.value)}
                  placeholder="EAAB..."
                />
                <small className="field-help">Requires whatsapp_business_messaging and whatsapp_business_management scopes</small>
              </div>
            </div>
          )}

          {step === 5 && (
            <div className="pm-wizard-step-content">
              <h3>Step 5: Webhook Verification</h3>
              <p>Paste the Convernix webhook callback URL into your Meta App dashboard.</p>

              <div className="pm-webhook-box">
                <div className="pm-form-field">
                  <label>Callback URL</label>
                  <div className="pm-copy-input-row">
                    <input type="text" value={wizardData.webhook_url} readOnly />
                    <button
                      type="button"
                      className="pm-secondary-btn small"
                      onClick={() => {
                        navigator.clipboard.writeText(wizardData.webhook_url);
                        toast('Webhook URL copied to clipboard.', 'success');
                      }}
                    >
                      <Copy size={13} /> Copy
                    </button>
                  </div>
                </div>

                <div className="pm-form-field">
                  <label>Verify Token</label>
                  <div className="pm-copy-input-row">
                    <input type="text" value={wizardData.verify_token} readOnly />
                    <button
                      type="button"
                      className="pm-secondary-btn small"
                      onClick={() => {
                        navigator.clipboard.writeText(wizardData.verify_token);
                        toast('Verify token copied to clipboard.', 'success');
                      }}
                    >
                      <Copy size={13} /> Copy
                    </button>
                  </div>
                </div>

                <div className="pm-webhook-notes">
                  <strong>Required Webhook Subscription Fields:</strong>
                  <code>messages, message_template_status_update, phone_number_quality_update</code>
                </div>
              </div>
            </div>
          )}

          {step === 6 && (
            <div className="pm-wizard-step-content">
              <h3>Step 6: Live Connection Test</h3>
              <p>Convernix will run live synthetic diagnostic checks across all Meta API endpoints.</p>

              <div className="pm-test-controls">
                <button
                  type="button"
                  className="pm-primary-btn"
                  onClick={runTest}
                  disabled={busy}
                >
                  <Activity size={14} /> {busy ? 'Testing Connection...' : 'Run Diagnostics'}
                </button>
              </div>

              {testResult && (
                <div className="pm-test-results-list">
                  {testResult.checks.map((chk) => (
                    <div key={chk.name} className="pm-test-check-row">
                      <div className="pm-check-icon success">
                        <CheckCircle2 size={16} />
                      </div>
                      <div className="pm-check-info">
                        <strong>{chk.name}</strong>
                        <span>{chk.message}</span>
                      </div>
                      <span className="pm-check-status-tag">Success</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {step === 7 && (
            <div className="pm-wizard-step-content centered">
              <div className="pm-wizard-complete-icon">
                <CheckCircle2 size={48} color="#25d366" />
              </div>
              <h3>Configuration Ready</h3>
              <p>
                Your WhatsApp Business number <strong>{wizardData.phone_number}</strong> is linked to Convernix
                under <strong>{wizardData.display_name}</strong>. Webhook listeners and automated lead router are ready to activate.
              </p>
            </div>
          )}
        </div>

        {/* Wizard Footer Navigation */}
        <footer className="pm-wizard-footer">
          <button
            type="button"
            className="pm-secondary-btn"
            onClick={() => setStep(step - 1)}
            disabled={step === 1 || busy}
          >
            <ChevronLeft size={14} /> Previous
          </button>

          <div style={{ marginLeft: 'auto', display: 'flex', gap: 10 }}>
            {step < 7 && (
              <button
                type="button"
                className="pm-secondary-btn"
                onClick={() => setStep(step + 1)}
              >
                Skip Step
              </button>
            )}

            {step < 7 ? (
              <button
                type="button"
                className="pm-primary-btn"
                onClick={() => setStep(step + 1)}
              >
                Next <ChevronRight size={14} />
              </button>
            ) : (
              <button
                type="button"
                className="pm-primary-btn"
                onClick={handleFinish}
                disabled={busy}
              >
                {busy ? 'Activating...' : 'Activate Integration'}
              </button>
            )}
          </div>
        </footer>
      </div>
    </div>
  );
}

