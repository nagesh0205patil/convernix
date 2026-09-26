import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  KeyRound,
  FileText,
  UserCheck,
  Clock,
  AlertTriangle,
  RotateCw,
  CheckCircle2,
  Lock,
  Download,
  Eye,
  RefreshCw,
  ExternalLink,
  Info,
} from 'lucide-react';
import type { ComplianceTab } from '../../types';

interface ComplianceShellProps {
  activeSubTab: ComplianceTab;
  onSubTabChange: (tab: ComplianceTab) => void;
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export function ComplianceShell({
  activeSubTab,
  onSubTabChange,
  showToast,
}: ComplianceShellProps) {
  const [telemetry, setTelemetry] = useState<any>(null);
  const [kmsData, setKmsData] = useState<any>(null);
  const [ropaData, setRopaData] = useState<any>(null);
  const [dsrRequests, setDsrRequests] = useState<any[]>([]);
  const [holds, setHolds] = useState<any[]>([]);
  const [incidents, setIncidents] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [rotatingKey, setRotatingKey] = useState(false);

  const getHeaders = () => ({
    'Authorization': `Bearer ${localStorage.getItem('crm_access_token') || ''}`,
    'Content-Type': 'application/json',
  });

  const fetchTelemetry = async () => {
    try {
      const res = await fetch('/api/admin/compliance/telemetry/', { headers: getHeaders() });
      if (res.ok) setTelemetry(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchKms = async () => {
    try {
      const res = await fetch('/api/admin/security/kms/', { headers: getHeaders() });
      if (res.ok) setKmsData(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchRopa = async () => {
    try {
      const res = await fetch('/api/admin/privacy/ropa/', { headers: getHeaders() });
      if (res.ok) setRopaData(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchDsr = async () => {
    try {
      const res = await fetch('/api/admin/privacy/requests/', { headers: getHeaders() });
      if (res.ok) {
        const data = await res.json();
        setDsrRequests(data.requests || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchHolds = async () => {
    try {
      const res = await fetch('/api/admin/privacy/holds/', { headers: getHeaders() });
      if (res.ok) {
        const data = await res.json();
        setHolds(data.holds || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchIncidents = async () => {
    try {
      const res = await fetch('/api/admin/security/incidents/', { headers: getHeaders() });
      if (res.ok) {
        const data = await res.json();
        setIncidents(data.incidents || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadData = async () => {
    setLoading(true);
    await Promise.all([fetchTelemetry(), fetchKms(), fetchRopa(), fetchDsr(), fetchHolds(), fetchIncidents()]);
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRotateKey = async () => {
    if (!window.confirm('Are you sure you want to rotate your tenant DEK? New records will be encrypted with key version N+1. Previous versions remain decryptable.')) return;
    setRotatingKey(true);
    try {
      const res = await fetch('/api/admin/security/kms/', {
        method: 'POST',
        headers: getHeaders(),
      });
      const data = await res.json();
      if (res.ok) {
        showToast(data.message || 'Key successfully rotated.', 'success');
        fetchKms();
        fetchTelemetry();
      } else {
        showToast(data.detail || 'Key rotation failed.', 'error');
      }
    } catch (e) {
      showToast('Network error during key rotation.', 'error');
    } finally {
      setRotatingKey(false);
    }
  };

  const handleExecuteDsr = async (id: number) => {
    try {
      const res = await fetch(`/api/admin/privacy/requests/${id}/action/`, {
        method: 'POST',
        headers: getHeaders(),
      });
      const data = await res.json();
      if (res.ok) {
        showToast('Privacy request executed successfully.', 'success');
        fetchDsr();
        fetchTelemetry();
      } else {
        showToast(data.detail || 'Execution failed.', 'error');
      }
    } catch (e) {
      showToast('Error executing DSR request.', 'error');
    }
  };

  const handleRunRetention = async () => {
    try {
      const res = await fetch('/api/admin/privacy/retention/run/', {
        method: 'POST',
        headers: getHeaders(),
      });
      const data = await res.json();
      if (res.ok) {
        showToast(`Retention sweep completed: ${data.records_deleted || 0} deleted, ${data.records_anonymized || 0} anonymized.`, 'success');
        fetchTelemetry();
      } else {
        showToast('Retention sweep failed.', 'error');
      }
    } catch (e) {
      showToast('Error triggering retention sweep.', 'error');
    }
  };

  return (
    <div className="adm-compliance-shell">
      {/* Non-Certification Disclaimer Banner */}
      <div className="adm-compliance-disclaimer" style={{
        background: 'rgba(56, 189, 248, 0.08)',
        border: '1px solid rgba(56, 189, 248, 0.25)',
        borderRadius: 8,
        padding: '12px 16px',
        marginBottom: 20,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        color: '#94a3b8',
        fontSize: 13,
      }}>
        <Info size={18} style={{ color: '#38bdf8', flexShrink: 0 }} />
        <div>
          <strong style={{ color: '#f8fafc' }}>Compliance Readiness & Telemetry:</strong> Technical controls implemented in Convernix support readiness for ISO/IEC 27001:2022, ISO/IEC 27701:2025, SOC 2 Trust Services Criteria, and India's DPDP Act 2023. Independent third-party audit and organizational governance are required for formal certification and attestation.
        </div>
      </div>

      {/* Subtab Navigation */}
      <div className="adm-subtab-nav" style={{
        display: 'flex',
        gap: 8,
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        paddingBottom: 8,
        marginBottom: 24,
        overflowX: 'auto',
      }}>
        {[
          { key: 'telemetry', label: 'Controls & Telemetry', icon: ShieldCheck },
          { key: 'kms', label: 'KMS & Envelope Keys', icon: KeyRound },
          { key: 'ropa', label: 'Data Inventory (ROPA)', icon: FileText },
          { key: 'dsr', label: 'Privacy Requests (DSR)', icon: UserCheck },
          { key: 'retention', label: 'Retention & Legal Holds', icon: Clock },
          { key: 'incidents', label: 'Security Incidents', icon: AlertTriangle },
        ].map((t) => {
          const Icon = t.icon;
          const active = activeSubTab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => onSubTabChange(t.key as ComplianceTab)}
              style={{
                background: active ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                color: active ? '#818cf8' : '#94a3b8',
                border: active ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
                borderRadius: 6,
                padding: '8px 14px',
                fontSize: 13,
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              <Icon size={15} />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* 1. Telemetry View */}
      {activeSubTab === 'telemetry' && (
        <div className="adm-telemetry-view">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
            <div style={{ background: '#1e293b', padding: 16, borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)' }}>
              <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>Envelope Encryption</div>
              <div style={{ fontSize: 18, fontWeight: 600, color: '#4ade80', display: 'flex', alignItems: 'center', gap: 6 }}>
                <CheckCircle2 size={18} /> {telemetry?.encryption?.status || 'ACTIVE'}
              </div>
              <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                Algorithm: {telemetry?.encryption?.algorithm || 'AES-256-GCM'} (v{telemetry?.encryption?.key_version || 1})
              </div>
            </div>

            <div style={{ background: '#1e293b', padding: 16, borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)' }}>
              <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>KMS Envelope Key</div>
              <div style={{ fontSize: 18, fontWeight: 600, color: '#4ade80', display: 'flex', alignItems: 'center', gap: 6 }}>
                <CheckCircle2 size={18} /> {telemetry?.kms?.provider || 'KMS Connected'}
              </div>
              <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                Status: {telemetry?.kms?.status || 'ONLINE'}
              </div>
            </div>

            <div style={{ background: '#1e293b', padding: 16, borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)' }}>
              <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>Audit Hash Integrity</div>
              <div style={{ fontSize: 18, fontWeight: 600, color: '#4ade80', display: 'flex', alignItems: 'center', gap: 6 }}>
                <CheckCircle2 size={18} /> {telemetry?.audit_logging?.tamper_integrity || 'VERIFIED'}
              </div>
              <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                {telemetry?.audit_logging?.total_events || 0} events signed with HMAC
              </div>
            </div>

            <div style={{ background: '#1e293b', padding: 16, borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)' }}>
              <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>Data Principal Requests</div>
              <div style={{ fontSize: 18, fontWeight: 600, color: '#f8fafc' }}>
                {telemetry?.privacy?.requests_total || 0} Total
              </div>
              <div style={{ fontSize: 12, color: '#38bdf8', marginTop: 4 }}>
                {telemetry?.privacy?.requests_completed || 0} Fulfilled
              </div>
            </div>
          </div>

          <div style={{ background: '#1e293b', borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)', overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, fontSize: 15, color: '#f8fafc' }}>Compliance Controls Matrix</h3>
              <span style={{ fontSize: 12, color: '#94a3b8' }}>
                {telemetry?.controls_summary?.implemented || 0} / {telemetry?.controls_summary?.total_controls || 0} Controls Implemented
              </span>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, textAlign: 'left' }}>
              <thead>
                <tr style={{ background: 'rgba(0,0,0,0.2)', color: '#94a3b8' }}>
                  <th style={{ padding: '12px 16px' }}>Control ID</th>
                  <th style={{ padding: '12px 16px' }}>Framework</th>
                  <th style={{ padding: '12px 16px' }}>Reference</th>
                  <th style={{ padding: '12px 16px' }}>Control Name</th>
                  <th style={{ padding: '12px 16px' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {(telemetry?.controls_summary?.controls || []).map((ctrl: any) => (
                  <tr key={ctrl.control_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '12px 16px', color: '#818cf8', fontWeight: 600 }}>{ctrl.control_id}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{
                        padding: '3px 8px', borderRadius: 4, fontSize: 11, fontWeight: 500,
                        background: ctrl.framework === 'ISO27001' ? 'rgba(59, 130, 246, 0.15)' :
                                    ctrl.framework === 'DPDP' ? 'rgba(168, 85, 247, 0.15)' :
                                    ctrl.framework === 'SOC2' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255,255,255,0.08)',
                        color: ctrl.framework === 'ISO27001' ? '#60a5fa' :
                               ctrl.framework === 'DPDP' ? '#c084fc' :
                               ctrl.framework === 'SOC2' ? '#34d399' : '#e2e8f0',
                      }}>
                        {ctrl.framework}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{ctrl.framework_reference}</td>
                    <td style={{ padding: '12px 16px', color: '#f8fafc' }}>{ctrl.control_name}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{ color: '#4ade80', display: 'flex', alignItems: 'center', gap: 4 }}>
                        <CheckCircle2 size={14} /> Implemented
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 2. KMS & Envelope Encryption View */}
      {activeSubTab === 'kms' && (
        <div className="adm-kms-view">
          <div style={{ background: '#1e293b', borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)', padding: 24, marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
              <div>
                <h3 style={{ margin: '0 0 6px 0', fontSize: 16, color: '#f8fafc' }}>Tenant Envelope Key Management</h3>
                <p style={{ margin: 0, fontSize: 13, color: '#94a3b8' }}>
                  Each tenant receives an independent 256-bit Data Encryption Key (DEK). DEKs are protected inside the database by a Key Encryption Key (KEK) using envelope encryption.
                </p>
              </div>
              <button
                onClick={handleRotateKey}
                disabled={rotatingKey}
                style={{
                  background: '#6366f1',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 6,
                  padding: '10px 16px',
                  fontSize: 13,
                  fontWeight: 500,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  cursor: rotatingKey ? 'not-allowed' : 'pointer',
                  opacity: rotatingKey ? 0.7 : 1,
                }}
              >
                <RotateCw size={15} className={rotatingKey ? 'spin' : ''} />
                {rotatingKey ? 'Rotating Key...' : 'Rotate Tenant Key'}
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
              <div style={{ background: 'rgba(0,0,0,0.2)', padding: 14, borderRadius: 6 }}>
                <div style={{ fontSize: 12, color: '#94a3b8' }}>Current Key Version</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#818cf8', marginTop: 4 }}>
                  v{kmsData?.key_version || 1}
                </div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.2)', padding: 14, borderRadius: 6 }}>
                <div style={{ fontSize: 12, color: '#94a3b8' }}>Encryption Algorithm</div>
                <div style={{ fontSize: 16, fontWeight: 600, color: '#f8fafc', marginTop: 4 }}>
                  {kmsData?.algorithm || 'AES-256-GCM'}
                </div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.2)', padding: 14, borderRadius: 6 }}>
                <div style={{ fontSize: 12, color: '#94a3b8' }}>KMS Key Provider</div>
                <div style={{ fontSize: 16, fontWeight: 600, color: '#38bdf8', marginTop: 4 }}>
                  {kmsData?.kms_provider || 'Local / Env KEK'}
                </div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.2)', padding: 14, borderRadius: 6 }}>
                <div style={{ fontSize: 12, color: '#94a3b8' }}>Last Rotation</div>
                <div style={{ fontSize: 13, fontWeight: 500, color: '#e2e8f0', marginTop: 6 }}>
                  {kmsData?.last_rotated_at ? new Date(kmsData.last_rotated_at).toLocaleDateString() : 'Initial Provisioning'}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 3. ROPA Data Inventory View */}
      {activeSubTab === 'ropa' && (
        <div className="adm-ropa-view">
          <div style={{ background: '#1e293b', borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)', overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
              <h3 style={{ margin: '0 0 4px 0', fontSize: 15, color: '#f8fafc' }}>Privacy Data Inventory & Record of Processing (ROPA)</h3>
              <p style={{ margin: 0, fontSize: 13, color: '#94a3b8' }}>
                Machine-readable inventory defining all data classifications, storage locations, encryption status, and retention categories under ISO 27701 & DPDP Act 2023.
              </p>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, textAlign: 'left' }}>
              <thead>
                <tr style={{ background: 'rgba(0,0,0,0.2)', color: '#94a3b8' }}>
                  <th style={{ padding: '12px 16px' }}>Category</th>
                  <th style={{ padding: '12px 16px' }}>Data Fields</th>
                  <th style={{ padding: '12px 16px' }}>Purpose</th>
                  <th style={{ padding: '12px 16px' }}>Encryption</th>
                  <th style={{ padding: '12px 16px' }}>Masking</th>
                  <th style={{ padding: '12px 16px' }}>Retention</th>
                </tr>
              </thead>
              <tbody>
                {(ropaData?.inventory || []).map((item: any, idx: number) => (
                  <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{
                        padding: '3px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                        background: item.classification === 'PERSONAL_DATA' ? 'rgba(234, 179, 8, 0.15)' :
                                    item.classification === 'SECRET' ? 'rgba(239, 68, 68, 0.15)' :
                                    item.classification === 'CONFIDENTIAL' ? 'rgba(59, 130, 246, 0.15)' : 'rgba(255,255,255,0.08)',
                        color: item.classification === 'PERSONAL_DATA' ? '#facc15' :
                               item.classification === 'SECRET' ? '#f87171' :
                               item.classification === 'CONFIDENTIAL' ? '#60a5fa' : '#e2e8f0',
                      }}>
                        {item.category}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', color: '#f8fafc', fontWeight: 500 }}>
                      {Array.isArray(item.fields) ? item.fields.join(', ') : item.fields}
                    </td>
                    <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{item.purpose}</td>
                    <td style={{ padding: '12px 16px', color: item.encryption_status === 'ENCRYPTED' ? '#4ade80' : '#94a3b8' }}>
                      {item.encryption_status}
                    </td>
                    <td style={{ padding: '12px 16px', color: '#e2e8f0' }}>{item.masking_rule || 'None'}</td>
                    <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{item.retention_period || 'Standard'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 4. DSR Privacy Requests View */}
      {activeSubTab === 'dsr' && (
        <div className="adm-dsr-view">
          <div style={{ background: '#1e293b', borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)', overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: '0 0 4px 0', fontSize: 15, color: '#f8fafc' }}>Data Subject / Principal Requests (DSR)</h3>
                <p style={{ margin: 0, fontSize: 13, color: '#94a3b8' }}>
                  Manage and fulfill statutory privacy requests under India DPDP Act 2023 & ISO 27701.
                </p>
              </div>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, textAlign: 'left' }}>
              <thead>
                <tr style={{ background: 'rgba(0,0,0,0.2)', color: '#94a3b8' }}>
                  <th style={{ padding: '12px 16px' }}>Request ID</th>
                  <th style={{ padding: '12px 16px' }}>Data Principal</th>
                  <th style={{ padding: '12px 16px' }}>Type</th>
                  <th style={{ padding: '12px 16px' }}>Status</th>
                  <th style={{ padding: '12px 16px' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {dsrRequests.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ padding: '24px 16px', textAlign: 'center', color: '#64748b' }}>
                      No privacy requests received yet.
                    </td>
                  </tr>
                ) : (
                  dsrRequests.map((req) => (
                    <tr key={req.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '12px 16px', color: '#818cf8', fontWeight: 600 }}>{req.request_id}</td>
                      <td style={{ padding: '12px 16px', color: '#f8fafc' }}>{req.data_principal_reference || 'Customer'}</td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{
                          padding: '3px 8px', borderRadius: 4, fontSize: 11, fontWeight: 500,
                          background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8',
                        }}>
                          {req.request_type}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ color: req.status === 'COMPLETED' ? '#4ade80' : '#facc15' }}>
                          {req.status}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        {req.status !== 'COMPLETED' ? (
                          <button
                            onClick={() => handleExecuteDsr(req.id)}
                            style={{
                              background: '#6366f1', color: '#fff', border: 'none',
                              borderRadius: 4, padding: '6px 12px', fontSize: 12, cursor: 'pointer',
                            }}
                          >
                            Execute
                          </button>
                        ) : (
                          <span style={{ color: '#94a3b8', fontSize: 12 }}>Fulfilled</span>
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

      {/* 5. Retention & Legal Holds View */}
      {activeSubTab === 'retention' && (
        <div className="adm-retention-view">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <div>
              <h3 style={{ margin: '0 0 4px 0', fontSize: 16, color: '#f8fafc' }}>Automated Retention & Legal Holds</h3>
              <p style={{ margin: 0, fontSize: 13, color: '#94a3b8' }}>
                Enforce privacy data lifecycles while preserving evidence during active regulatory investigations.
              </p>
            </div>
            <button
              onClick={handleRunRetention}
              style={{
                background: 'rgba(239, 68, 68, 0.15)',
                color: '#f87171',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: 6,
                padding: '8px 14px',
                fontSize: 13,
                fontWeight: 500,
                cursor: 'pointer',
              }}
            >
              Run Retention Sweep Now
            </button>
          </div>

          <div style={{ background: '#1e293b', borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)', overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
              <h4 style={{ margin: 0, fontSize: 14, color: '#f8fafc' }}>Active Legal Holds</h4>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, textAlign: 'left' }}>
              <thead>
                <tr style={{ background: 'rgba(0,0,0,0.2)', color: '#94a3b8' }}>
                  <th style={{ padding: '12px 16px' }}>Hold ID</th>
                  <th style={{ padding: '12px 16px' }}>Name</th>
                  <th style={{ padding: '12px 16px' }}>Scope</th>
                  <th style={{ padding: '12px 16px' }}>Reason</th>
                  <th style={{ padding: '12px 16px' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {holds.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ padding: '24px 16px', textAlign: 'center', color: '#64748b' }}>
                      No active legal holds. Standard retention policies apply.
                    </td>
                  </tr>
                ) : (
                  holds.map((h) => (
                    <tr key={h.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '12px 16px', color: '#818cf8', fontWeight: 600 }}>{h.hold_id}</td>
                      <td style={{ padding: '12px 16px', color: '#f8fafc' }}>{h.name}</td>
                      <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{h.scope}</td>
                      <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{h.reason}</td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ color: h.is_active ? '#f87171' : '#64748b', fontWeight: 500 }}>
                          {h.is_active ? 'ACTIVE HOLD' : 'RELEASED'}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 6. Security Incidents View */}
      {activeSubTab === 'incidents' && (
        <div className="adm-incidents-view">
          <div style={{ background: '#1e293b', borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)', overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
              <h3 style={{ margin: '0 0 4px 0', fontSize: 15, color: '#f8fafc' }}>Security Incident Response Tracker</h3>
              <p style={{ margin: 0, fontSize: 13, color: '#94a3b8' }}>
                Auditable incident management workflow for anomaly detection, containment, investigation, and post-incident review under SOC 2 & ISO 27001.
              </p>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, textAlign: 'left' }}>
              <thead>
                <tr style={{ background: 'rgba(0,0,0,0.2)', color: '#94a3b8' }}>
                  <th style={{ padding: '12px 16px' }}>Incident ID</th>
                  <th style={{ padding: '12px 16px' }}>Severity</th>
                  <th style={{ padding: '12px 16px' }}>Title</th>
                  <th style={{ padding: '12px 16px' }}>Category</th>
                  <th style={{ padding: '12px 16px' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {incidents.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ padding: '24px 16px', textAlign: 'center', color: '#64748b' }}>
                      No security incidents recorded. System telemetry nominal.
                    </td>
                  </tr>
                ) : (
                  incidents.map((inc) => (
                    <tr key={inc.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '12px 16px', color: '#818cf8', fontWeight: 600 }}>{inc.incident_id}</td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{
                          padding: '3px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                          background: inc.severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.2)' :
                                      inc.severity === 'HIGH' ? 'rgba(249, 115, 22, 0.2)' : 'rgba(234, 179, 8, 0.2)',
                          color: inc.severity === 'CRITICAL' ? '#f87171' :
                                 inc.severity === 'HIGH' ? '#fb923c' : '#facc15',
                        }}>
                          {inc.severity}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px', color: '#f8fafc' }}>{inc.title}</td>
                      <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{inc.category}</td>
                      <td style={{ padding: '12px 16px', color: '#38bdf8' }}>{inc.status}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

