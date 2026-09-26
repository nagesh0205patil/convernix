import React, { useEffect, useState } from 'react';
import {
  Lock,
  KeyRound,
  Shield,
  Smartphone,
  Mail,
  Monitor,
  LogOut,
  CheckCircle2,
  AlertCircle,
  Plus,
  Trash2,
  Copy,
  Check,
  RefreshCw,
  Eye,
  Sliders,
  ShieldAlert,
  X,
} from 'lucide-react';
import { AdminPageHeader } from '../common/AdminPageHeader';
import { StatusBadge } from '../common/StatusBadge';
import { ConfirmationDialog } from '../common/ConfirmationDialog';
import { adminApi } from '../../services/adminApi';
import type { ApiKeyInfo, SecurityPolicyInfo, UserSessionInfo } from '../../types';

interface SecuritySettingsProps {
  sessions: UserSessionInfo[];
  onUpdatePassword: (data: any) => Promise<boolean>;
  onRevokeSession: (id: number) => Promise<boolean>;
  onRevokeAllOther: () => Promise<boolean>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export function SecuritySettings({
  sessions,
  onUpdatePassword,
  onRevokeSession,
  onRevokeAllOther,
  toast,
}: SecuritySettingsProps) {
  const [activeSubView, setActiveSubView] = useState<'auth' | 'api-keys' | 'policies' | 'sessions'>('auth');

  // Password & MFA State
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [updating, setUpdating] = useState(false);
  const [mfaEnabled, setMfaEnabled] = useState(true);
  const [showRevokeAllConfirm, setShowRevokeAllConfirm] = useState(false);

  // API Keys State
  const [apiKeys, setApiKeys] = useState<ApiKeyInfo[]>([]);
  const [loadingKeys, setLoadingKeys] = useState(false);
  const [showCreateKeyModal, setShowCreateKeyModal] = useState(false);
  const [keyFormData, setKeyFormData] = useState({
    name: '',
    scopes: ['*'],
    expires_in_days: 90,
  });
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);

  // Security Policy State
  const [policy, setPolicy] = useState<SecurityPolicyInfo>({
    mfa_required: false,
    password_min_length: 8,
    password_require_special: true,
    session_duration_minutes: 480,
    ip_allowlist: [],
  });
  const [ipInput, setIpInput] = useState('');
  const [savingPolicy, setSavingPolicy] = useState(false);

  // Fetch API Keys & Policies
  const fetchApiKeys = async () => {
    setLoadingKeys(true);
    try {
      const res = await adminApi.getApiKeys();
      setApiKeys(res.api_keys || []);
    } catch (err: any) {
      toast(err.message || 'Failed to load API keys', 'error');
    } finally {
      setLoadingKeys(false);
    }
  };

  const fetchPolicy = async () => {
    try {
      const res = await adminApi.getSecurityPolicy();
      if (res) {
        setPolicy(res);
        setMfaEnabled(res.mfa_required);
      }
    } catch (err: any) {
      // non-fatal
    }
  };

  useEffect(() => {
    fetchPolicy();
  }, []);

  useEffect(() => {
    if (activeSubView === 'api-keys') {
      fetchApiKeys();
    }
  }, [activeSubView]);

  // Compute password strength
  const calculateStrength = (pwd: string) => {
    if (!pwd) return 0;
    let score = 0;
    if (pwd.length >= 8) score += 25;
    if (/[A-Z]/.test(pwd)) score += 25;
    if (/[a-z]/.test(pwd) && /[0-9]/.test(pwd)) score += 25;
    if (/[^A-Za-z0-9]/.test(pwd)) score += 25;
    return score;
  };

  const strength = calculateStrength(newPassword);
  const getStrengthLabel = (s: number) => {
    if (s <= 25) return { label: 'Weak', color: '#ef4444' };
    if (s <= 50) return { label: 'Fair', color: '#f59e0b' };
    if (s <= 75) return { label: 'Good', color: '#38bdf8' };
    return { label: 'Strong & Compliant', color: '#52bb89' };
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentPassword) {
      toast('Please enter your current password.', 'error');
      return;
    }
    if (newPassword.length < policy.password_min_length) {
      toast(`New password must be at least ${policy.password_min_length} characters per security policy.`, 'error');
      return;
    }
    if (policy.password_require_special && !/[^A-Za-z0-9]/.test(newPassword)) {
      toast('Security policy requires at least one special character.', 'error');
      return;
    }
    if (newPassword !== confirmPassword) {
      toast('Password confirmation does not match.', 'error');
      return;
    }

    setUpdating(true);
    const ok = await onUpdatePassword({
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
    });
    setUpdating(false);
    if (ok) {
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      toast('Password updated successfully.', 'success');
    }
  };

  const handleCreateApiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyFormData.name.trim()) {
      toast('API key name is required.', 'error');
      return;
    }

    try {
      const res = await adminApi.createApiKey({
        name: keyFormData.name.trim(),
        scopes: keyFormData.scopes,
        expires_in_days: Number(keyFormData.expires_in_days) || undefined,
      });
      setShowCreateKeyModal(false);
      setNewlyCreatedKey(res.plaintext_key);
      fetchApiKeys();
      toast('API key created successfully.', 'success');
    } catch (err: any) {
      toast(err.message || 'Failed to create API key.', 'error');
    }
  };

  const handleRevokeKey = async (key: ApiKeyInfo) => {
    if (!confirm(`Are you sure you want to revoke API key "${key.name}"? Any systems using this key will immediately lose access.`)) {
      return;
    }
    try {
      await adminApi.revokeApiKey(key.id);
      toast(`API key "${key.name}" revoked.`, 'success');
      fetchApiKeys();
    } catch (err: any) {
      toast(err.message || 'Failed to revoke API key.', 'error');
    }
  };

  const handleSavePolicy = async () => {
    setSavingPolicy(true);
    try {
      const updated = await adminApi.updateSecurityPolicy(policy);
      setPolicy(updated);
      toast('Organization security policy updated successfully.', 'success');
    } catch (err: any) {
      toast(err.message || 'Failed to update security policy.', 'error');
    } finally {
      setSavingPolicy(false);
    }
  };

  const addIpToAllowlist = () => {
    const ip = ipInput.trim();
    if (!ip) return;
    if (policy.ip_allowlist.includes(ip)) {
      toast('IP already in allowlist.', 'info');
      return;
    }
    setPolicy({
      ...policy,
      ip_allowlist: [...policy.ip_allowlist, ip],
    });
    setIpInput('');
  };

  const removeIpFromAllowlist = (ip: string) => {
    setPolicy({
      ...policy,
      ip_allowlist: policy.ip_allowlist.filter((x) => x !== ip),
    });
  };

  return (
    <div className="pm-settings-panel">
      <AdminPageHeader
        breadcrumbs={[
          { label: 'Administration' },
          { label: 'Settings' },
          { label: 'Security' },
        ]}
        title="Security & API Keys"
        subtitle="Manage administrator authentication, organizational security policies, API credentials, and active sessions."
      />

      {/* Subview Selector */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: 10 }}>
        <button
          type="button"
          className={`pm-btn pm-btn-sm ${activeSubView === 'auth' ? 'pm-btn-primary' : 'pm-btn-outline'}`}
          onClick={() => setActiveSubView('auth')}
        >
          <Lock size={13} />
          <span>Authentication & MFA</span>
        </button>
        <button
          type="button"
          className={`pm-btn pm-btn-sm ${activeSubView === 'api-keys' ? 'pm-btn-primary' : 'pm-btn-outline'}`}
          onClick={() => setActiveSubView('api-keys')}
        >
          <KeyRound size={13} />
          <span>API Keys & Secrets</span>
        </button>
        <button
          type="button"
          className={`pm-btn pm-btn-sm ${activeSubView === 'policies' ? 'pm-btn-primary' : 'pm-btn-outline'}`}
          onClick={() => setActiveSubView('policies')}
        >
          <ShieldAlert size={13} />
          <span>Security Policies</span>
        </button>
        <button
          type="button"
          className={`pm-btn pm-btn-sm ${activeSubView === 'sessions' ? 'pm-btn-primary' : 'pm-btn-outline'}`}
          onClick={() => setActiveSubView('sessions')}
        >
          <Monitor size={13} />
          <span>Active Sessions</span>
        </button>
      </div>

      {/* VIEW: AUTHENTICATION & MFA */}
      {activeSubView === 'auth' && (
        <div className="pm-security-grid">
          {/* Password Section */}
          <div className="pm-info-card">
            <div className="pm-info-card-header">
              <div>
                <h3>Account Password</h3>
                <p className="pm-card-subtitle">Keep your Convernix administrator account secure</p>
              </div>
              <KeyRound size={18} color="#aaa4ff" />
            </div>

            <form onSubmit={handlePasswordSubmit} className="pm-form-stack" noValidate>
              <div className="pm-form-field">
                <label htmlFor="current_password">Current Password</label>
                <input
                  id="current_password"
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Enter current account password"
                  required
                />
              </div>

              <div className="pm-form-field">
                <label htmlFor="new_password">New Password</label>
                <input
                  id="new_password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Create a strong new password"
                  required
                />
                {newPassword && (
                  <div className="pm-password-strength-bar">
                    <div
                      className="pm-strength-fill"
                      style={{
                        width: `${strength}%`,
                        backgroundColor: getStrengthLabel(strength).color,
                      }}
                    />
                    <small style={{ color: getStrengthLabel(strength).color }}>
                      Strength: {getStrengthLabel(strength).label}
                    </small>
                  </div>
                )}
              </div>

              <div className="pm-form-field">
                <label htmlFor="confirm_password">Confirm New Password</label>
                <input
                  id="confirm_password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter new password"
                  required
                />
              </div>

              <button
                type="submit"
                className="pm-btn pm-btn-primary"
                disabled={updating}
                style={{ marginTop: 8 }}
              >
                {updating ? 'Updating...' : 'Update Password'}
              </button>
            </form>
          </div>

          {/* MFA Section */}
          <div className="pm-info-card">
            <div className="pm-info-card-header">
              <div>
                <h3>Two-Factor Authentication (2FA)</h3>
                <p className="pm-card-subtitle">Enforce multi-factor verification for administrative actions</p>
              </div>
              <Shield size={18} color="#52bb89" />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 14px', borderRadius: 8, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Smartphone size={20} style={{ color: '#38bdf8' }} />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#fff' }}>Authenticator App (TOTP)</div>
                    <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Google Authenticator, 1Password, or Authy</div>
                  </div>
                </div>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '2px 8px', borderRadius: 10, background: 'rgba(82, 187, 137, 0.15)', color: '#52bb89' }}>
                  CONFIGURED
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 14px', borderRadius: 8, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Mail size={20} style={{ color: '#aaa4ff' }} />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#fff' }}>Email Security Codes</div>
                    <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Backup fallback delivery to primary admin address</div>
                  </div>
                </div>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '2px 8px', borderRadius: 10, background: 'rgba(82, 187, 137, 0.15)', color: '#52bb89' }}>
                  ACTIVE
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* VIEW: API KEYS & SECRETS */}
      {activeSubView === 'api-keys' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: '#fff' }}>Tenant API Keys</h3>
              <p style={{ margin: '4px 0 0', fontSize: '0.82rem', color: '#94a3b8' }}>
                Cryptographically secure bearer keys prefixed with <code>cvx_live_</code>. Stored as SHA-256 hashes at rest.
              </p>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" className="pm-btn pm-btn-outline" onClick={fetchApiKeys}>
                <RefreshCw size={13} className={loadingKeys ? 'animate-spin' : ''} />
                <span>Refresh</span>
              </button>
              <button type="button" className="pm-btn pm-btn-primary" onClick={() => setShowCreateKeyModal(true)}>
                <Plus size={14} />
                <span>Generate Key</span>
              </button>
            </div>
          </div>

          <div className="pm-table-container">
            <table className="pm-table">
              <thead>
                <tr>
                  <th>Key Name</th>
                  <th>Prefix Identifier</th>
                  <th>Scopes</th>
                  <th>Created By</th>
                  <th>Expires</th>
                  <th>Last Used</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {loadingKeys ? (
                  <tr>
                    <td colSpan={8} style={{ textAlign: 'center', padding: '30px 0', color: '#94a3b8' }}>
                      Loading API keys...
                    </td>
                  </tr>
                ) : apiKeys.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ textAlign: 'center', padding: '30px 0', color: '#94a3b8' }}>
                      No active API keys found. Generate a key to integrate external automation or CRM webhooks.
                    </td>
                  </tr>
                ) : (
                  apiKeys.map((k) => (
                    <tr key={k.id} style={{ opacity: k.is_active ? 1 : 0.6 }}>
                      <td>
                        <span style={{ fontWeight: 600, color: '#fff' }}>{k.name}</span>
                      </td>
                      <td>
                        <code style={{ fontSize: '0.8rem', background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: 4 }}>
                          {k.key_prefix}...
                        </code>
                      </td>
                      <td>
                        <span style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>{k.scopes.join(', ')}</span>
                      </td>
                      <td style={{ fontSize: '0.82rem', color: '#94a3b8' }}>{k.creator_name || 'Admin'}</td>
                      <td style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
                        {k.expires_at ? new Date(k.expires_at).toLocaleDateString() : 'Never'}
                      </td>
                      <td style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
                        {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : 'Never'}
                      </td>
                      <td>
                        <span
                          style={{
                            fontSize: '0.72rem',
                            fontWeight: 600,
                            padding: '2px 8px',
                            borderRadius: 10,
                            background: k.is_active ? 'rgba(82, 187, 137, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                            color: k.is_active ? '#52bb89' : '#f87171',
                          }}
                        >
                          {k.is_active ? 'ACTIVE' : 'REVOKED'}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {k.is_active && (
                          <button
                            type="button"
                            className="pm-btn pm-btn-sm pm-btn-outline"
                            onClick={() => handleRevokeKey(k)}
                            style={{ color: '#f87171' }}
                            title="Revoke key immediately"
                          >
                            <Trash2 size={12} />
                            <span>Revoke</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* VIEW: SECURITY POLICIES */}
      {activeSubView === 'policies' && (
        <div style={{ maxWidth: 720 }}>
          <div className="pm-info-card">
            <h3 style={{ margin: '0 0 4px', fontSize: '1.1rem', fontWeight: 600 }}>Organization Security Policies</h3>
            <p className="pm-card-subtitle" style={{ marginBottom: 20 }}>
              Apply mandatory zero-trust authentication policies across all members of this tenant workspace.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={policy.mfa_required}
                  onChange={(e) => setPolicy({ ...policy, mfa_required: e.target.checked })}
                />
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#fff' }}>Mandatory Multi-Factor Authentication (MFA)</div>
                  <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Require all staff and operators to verify via TOTP before accessing workspace</div>
                </div>
              </label>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div className="pm-form-group">
                  <label className="pm-form-label">Minimum Password Length</label>
                  <input
                    type="number"
                    min={8}
                    max={64}
                    className="pm-input"
                    value={policy.password_min_length}
                    onChange={(e) => setPolicy({ ...policy, password_min_length: Number(e.target.value) })}
                  />
                </div>

                <div className="pm-form-group">
                  <label className="pm-form-label">Session Idle Timeout (minutes)</label>
                  <input
                    type="number"
                    min={15}
                    max={1440}
                    className="pm-input"
                    value={policy.session_duration_minutes}
                    onChange={(e) => setPolicy({ ...policy, session_duration_minutes: Number(e.target.value) })}
                  />
                </div>
              </div>

              <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={policy.password_require_special}
                  onChange={(e) => setPolicy({ ...policy, password_require_special: e.target.checked })}
                />
                <span style={{ fontSize: '0.88rem', color: '#cbd5e1' }}>Enforce special character requirements (!@#$%^&*) in passwords</span>
              </label>

              {/* IP Allowlist */}
              <div>
                <label className="pm-form-label">IP Address Allowlist (Optional CIDR / IPs)</label>
                <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                  <input
                    type="text"
                    className="pm-input"
                    placeholder="e.g. 203.0.113.42 or 10.0.0.0/24"
                    value={ipInput}
                    onChange={(e) => setIpInput(e.target.value)}
                  />
                  <button type="button" className="pm-btn pm-btn-outline" onClick={addIpToAllowlist}>
                    Add IP
                  </button>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {policy.ip_allowlist.map((ip) => (
                    <span
                      key={ip}
                      style={{
                        background: 'rgba(255,255,255,0.06)',
                        padding: '3px 8px',
                        borderRadius: 14,
                        fontSize: '0.78rem',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                      }}
                    >
                      <span>{ip}</span>
                      <X size={12} style={{ cursor: 'pointer' }} onClick={() => removeIpFromAllowlist(ip)} />
                    </span>
                  ))}
                  {policy.ip_allowlist.length === 0 && (
                    <span style={{ fontSize: '0.8rem', color: '#64748b' }}>No IP restrictions applied. Access open to all verified networks.</span>
                  )}
                </div>
              </div>

              <div style={{ marginTop: 10 }}>
                <button
                  type="button"
                  className="pm-btn pm-btn-primary"
                  onClick={handleSavePolicy}
                  disabled={savingPolicy}
                >
                  {savingPolicy ? 'Saving Policies...' : 'Save Security Policy'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* VIEW: SESSIONS */}
      {activeSubView === 'sessions' && (
        <div className="pm-info-card">
          <div className="pm-info-card-header">
            <div>
              <h3>Active Sessions</h3>
              <p className="pm-card-subtitle">Devices and locations currently signed into this tenant workspace</p>
            </div>
            {sessions.length > 1 && (
              <button
                type="button"
                className="pm-btn pm-btn-outline"
                style={{ color: '#f87171' }}
                onClick={() => setShowRevokeAllConfirm(true)}
              >
                <LogOut size={14} />
                <span>Revoke All Other Sessions</span>
              </button>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {sessions.map((sess) => (
              <div
                key={sess.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '12px 14px',
                  borderRadius: 8,
                  background: sess.is_current ? 'rgba(56, 189, 248, 0.06)' : 'rgba(255,255,255,0.02)',
                  border: sess.is_current ? '1px solid rgba(56, 189, 248, 0.3)' : '1px solid rgba(255,255,255,0.06)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Monitor size={20} style={{ color: sess.is_current ? '#38bdf8' : '#94a3b8' }} />
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontWeight: 600, fontSize: '0.9rem', color: '#fff' }}>{sess.device}</span>
                      {sess.is_current && (
                        <span style={{ fontSize: '0.68rem', background: '#38bdf8', color: '#0f172a', fontWeight: 700, padding: '1px 6px', borderRadius: 4 }}>
                          THIS DEVICE
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                      {sess.browser} · {sess.location} · {sess.ip_address}
                    </div>
                  </div>
                </div>

                {!sess.is_current && (
                  <button
                    type="button"
                    className="pm-btn pm-btn-sm pm-btn-outline"
                    onClick={async () => {
                      await onRevokeSession(sess.id);
                    }}
                  >
                    Terminate
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Generate API Key Modal */}
      {showCreateKeyModal && (
        <div className="pm-modal-overlay" onClick={() => setShowCreateKeyModal(false)}>
          <div className="pm-modal" style={{ maxWidth: 480 }} onClick={(e) => e.stopPropagation()}>
            <form onSubmit={handleCreateApiKey}>
              <div className="pm-modal-header">
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>Generate API Key</h3>
                <button type="button" className="pm-modal-close" onClick={() => setShowCreateKeyModal(false)}>
                  <X size={18} />
                </button>
              </div>
              <div className="pm-modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div className="pm-form-group">
                  <label className="pm-form-label">Key Description / Name *</label>
                  <input
                    type="text"
                    className="pm-input"
                    placeholder="e.g. Zapier Ingestion, Salesforce Webhook"
                    value={keyFormData.name}
                    onChange={(e) => setKeyFormData({ ...keyFormData, name: e.target.value })}
                    required
                  />
                </div>

                <div className="pm-form-group">
                  <label className="pm-form-label">Key Expiration</label>
                  <select
                    className="pm-input"
                    value={keyFormData.expires_in_days}
                    onChange={(e) => setKeyFormData({ ...keyFormData, expires_in_days: Number(e.target.value) })}
                  >
                    <option value={30}>30 Days</option>
                    <option value={90}>90 Days (Recommended)</option>
                    <option value={365}>1 Year</option>
                    <option value={0}>No Expiration</option>
                  </select>
                </div>
              </div>
              <div className="pm-modal-footer">
                <button type="button" className="pm-btn pm-btn-outline" onClick={() => setShowCreateKeyModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="pm-btn pm-btn-primary">
                  Generate Key
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reveal Plaintext Key Once Modal */}
      {newlyCreatedKey && (
        <div className="pm-modal-overlay">
          <div className="pm-modal" style={{ maxWidth: 540 }} onClick={(e) => e.stopPropagation()}>
            <div className="pm-modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <AlertCircle size={20} style={{ color: '#f59e0b' }} />
                <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 600 }}>Save Your Secret API Key</h3>
              </div>
            </div>
            <div className="pm-modal-body">
              <div style={{ background: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: 8, padding: 12, marginBottom: 14 }}>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#fcd34d', lineHeight: 1.4 }}>
                  <strong>Important:</strong> Please copy this key and save it securely. For security reasons, you will never be able to view this key again once this dialog is dismissed.
                </p>
              </div>

              <div className="pm-form-group">
                <label className="pm-form-label">Plaintext Bearer Secret</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    type="text"
                    readOnly
                    className="pm-input"
                    style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}
                    value={newlyCreatedKey}
                  />
                  <button
                    type="button"
                    className="pm-btn pm-btn-primary"
                    onClick={() => {
                      navigator.clipboard.writeText(newlyCreatedKey);
                      setCopiedKey(true);
                      setTimeout(() => setCopiedKey(false), 3000);
                    }}
                  >
                    {copiedKey ? <Check size={14} /> : <Copy size={14} />}
                    <span>{copiedKey ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
              </div>
            </div>
            <div className="pm-modal-footer">
              <button
                type="button"
                className="pm-btn pm-btn-primary"
                onClick={() => setNewlyCreatedKey(null)}
              >
                I have safely stored this key
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Dialog for Revoke All */}
      <ConfirmationDialog
        isOpen={showRevokeAllConfirm}
        title="Revoke All Other Sessions?"
        message="This will immediately sign out all active sessions on other devices. You will remain logged into this current browser."
        confirmText="Revoke Sessions"
        confirmVariant="danger"
        onConfirm={async () => {
          setShowRevokeAllConfirm(false);
          await onRevokeAllOther();
        }}
        onCancel={() => setShowRevokeAllConfirm(false)}
      />
    </div>
  );
}
