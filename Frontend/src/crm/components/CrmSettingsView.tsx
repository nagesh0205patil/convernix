import React, { useState } from 'react'
import {
  Settings,
  Shield,
  Bot,
  GitMerge,
  Save,
  CheckCircle,
  AlertCircle
} from 'lucide-react'

interface CrmSettingsViewProps {
  token: string
}

export const CrmSettingsView: React.FC<CrmSettingsViewProps> = ({ token: _token }) => {
  const [inboundStrategy, setInboundStrategy] = useState('ATTACH_TO_ACTIVE')
  const [duplicateStrictness, setDuplicateStrictness] = useState('EXACT_MATCH_HMAC')
  const [defaultCurrency, setDefaultCurrency] = useState('USD')
  const [assignmentMode, setAssignmentMode] = useState('MANUAL')
  const [saved, setSaved] = useState(false)

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="crm-container">
      <div className="crm-header">
        <div className="crm-header-title-group">
          <div className="crm-header-icon">
            <Settings size={20} />
          </div>
          <div>
            <h1 className="crm-header-title">CRM Settings & Policies</h1>
            <p className="crm-header-subtitle">
              Configure tenant CRM inbound lead rules, duplicate resolution, and assignment automation
            </p>
          </div>
        </div>

        <div className="crm-header-actions">
          {saved && (
            <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem' }}>
              <CheckCircle size={14} /> Saved successfully
            </span>
          )}
          <button className="crm-btn crm-btn-primary" onClick={handleSave}>
            <Save size={14} />
            <span>Save Settings</span>
          </button>
        </div>
      </div>

      <div className="crm-content">
        <form onSubmit={handleSave} style={{ maxWidth: '800px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Section 1: Inbound Lead Creation */}
          <div
            style={{
              background: '#141722',
              border: '1px solid #232738',
              borderRadius: '10px',
              padding: '20px',
            }}
          >
            <h3 style={{ margin: '0 0 12px 0', fontSize: '0.95rem', color: '#f8fafc', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Bot size={16} color="#818cf8" />
              <span>Inbound WhatsApp Lead Strategy</span>
            </h3>
            <p style={{ margin: '0 0 16px 0', fontSize: '0.8rem', color: '#94a3b8' }}>
              Determine how incoming messages from Meta WhatsApp webhooks interact with existing lead opportunities.
            </p>

            <div className="crm-form-group">
              <label>Resolution Rule</label>
              <select
                className="crm-form-control"
                value={inboundStrategy}
                onChange={(e) => setInboundStrategy(e.target.value)}
              >
                <option value="ATTACH_TO_ACTIVE">
                  Attach to Active Open Lead (Do not create duplicate leads for same conversation)
                </option>
                <option value="REOPEN_LAST">
                  Reopen Last Closed Lead if within 30 days
                </option>
                <option value="AUTO_CREATE_NEW">
                  Always create a new Lead per new WhatsApp thread
                </option>
              </select>
            </div>
          </div>

          {/* Section 2: Duplicate Detection */}
          <div
            style={{
              background: '#141722',
              border: '1px solid #232738',
              borderRadius: '10px',
              padding: '20px',
            }}
          >
            <h3 style={{ margin: '0 0 12px 0', fontSize: '0.95rem', color: '#f8fafc', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <GitMerge size={16} color="#10b981" />
              <span>Identity Resolution & Blind Indexing</span>
            </h3>
            <p style={{ margin: '0 0 16px 0', fontSize: '0.8rem', color: '#94a3b8' }}>
              HMAC-SHA256 blind indexing ensures duplicate detection without decrypting customer records or storing raw contact numbers in index columns.
            </p>

            <div className="crm-form-group">
              <label>Match Criteria</label>
              <select
                className="crm-form-control"
                value={duplicateStrictness}
                onChange={(e) => setDuplicateStrictness(e.target.value)}
              >
                <option value="EXACT_MATCH_HMAC">
                  Strict HMAC Match (E.164 phone hash, normalized email hash, WhatsApp ID)
                </option>
                <option value="PHONE_AND_EMAIL">
                  Separate Phone or Email Match
                </option>
              </select>
            </div>
          </div>

          {/* Section 3: Lead Assignment Architecture */}
          <div
            style={{
              background: '#141722',
              border: '1px solid #232738',
              borderRadius: '10px',
              padding: '20px',
            }}
          >
            <h3 style={{ margin: '0 0 12px 0', fontSize: '0.95rem', color: '#f8fafc', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Shield size={16} color="#fbbf24" />
              <span>Routing & Ownership Architecture</span>
            </h3>
            <p style={{ margin: '0 0 16px 0', fontSize: '0.8rem', color: '#94a3b8' }}>
              Configure ownership assignment model for newly qualified leads.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div className="crm-form-group">
                <label>Assignment Engine</label>
                <select
                  className="crm-form-control"
                  value={assignmentMode}
                  onChange={(e) => setAssignmentMode(e.target.value)}
                >
                  <option value="MANUAL">Manual Triage & Assignment</option>
                  <option value="ROUND_ROBIN">Round Robin (Team Members)</option>
                  <option value="LEAST_LOADED">Least Loaded (Active Lead Count)</option>
                </select>
              </div>

              <div className="crm-form-group">
                <label>Default Currency</label>
                <select
                  className="crm-form-control"
                  value={defaultCurrency}
                  onChange={(e) => setDefaultCurrency(e.target.value)}
                >
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="INR">INR (₹)</option>
                  <option value="GBP">GBP (£)</option>
                </select>
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
