import React, { useState, useEffect, useCallback } from 'react'
import {
  Sliders,
  Plus,
  Trash2,
  RefreshCw,
  Lock,
  CheckCircle,
  XCircle,
  AlertTriangle
} from 'lucide-react'
import { crmApi } from '../services/crmApi'

interface CrmCustomFieldsViewProps {
  token: string
}

const FIELD_TYPES = [
  'TEXT',
  'TEXTAREA',
  'NUMBER',
  'DECIMAL',
  'BOOLEAN',
  'DATE',
  'DATETIME',
  'EMAIL',
  'PHONE',
  'URL',
  'SELECT',
  'MULTI_SELECT',
]

export const CrmCustomFieldsView: React.FC<CrmCustomFieldsViewProps> = ({ token }) => {
  const [fields, setFields] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Create Modal
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({
    entity_type: 'LEAD',
    name: '',
    label: '',
    field_type: 'TEXT',
    is_required: false,
    is_sensitive: false,
    options_text: '',
  })
  const [saving, setSaving] = useState(false)
  const [modalError, setModalError] = useState<string | null>(null)

  const loadFields = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await crmApi.getCustomFields(token)
      const list = Array.isArray(data) ? data : data?.results || []
      setFields(list)
    } catch (err: any) {
      setError(err.message || 'Failed to load custom fields')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    loadFields()
  }, [loadFields])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim() || !form.label.trim()) return
    setSaving(true)
    setModalError(null)
    try {
      const payload: any = {
        entity_type: form.entity_type,
        name: form.name.trim().toLowerCase().replace(/\s+/g, '_'),
        label: form.label.trim(),
        field_type: form.field_type,
        is_required: form.is_required,
        is_sensitive: form.is_sensitive,
      }
      if (['SELECT', 'MULTI_SELECT'].includes(form.field_type) && form.options_text) {
        payload.options = form.options_text.split(',').map((o) => o.trim()).filter(Boolean)
      }
      await crmApi.createCustomField(token, payload)
      setShowModal(false)
      setForm({
        entity_type: 'LEAD',
        name: '',
        label: '',
        field_type: 'TEXT',
        is_required: false,
        is_sensitive: false,
        options_text: '',
      })
      loadFields()
    } catch (err: any) {
      setModalError(err.message || 'Failed to create field')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (fieldId: string) => {
    if (!confirm('Are you sure you want to delete this custom field definition?')) return
    try {
      await crmApi.deleteCustomField(token, fieldId)
      loadFields()
    } catch (err: any) {
      setError(`Failed to delete field: ${err.message}`)
    }
  }

  return (
    <div className="crm-container">
      <div className="crm-header">
        <div className="crm-header-title-group">
          <div className="crm-header-icon">
            <Sliders size={20} />
          </div>
          <div>
            <h1 className="crm-header-title">Custom Fields</h1>
            <p className="crm-header-subtitle">
              Extend Customer & Lead models with dynamic tenant-isolated schema attributes
            </p>
          </div>
        </div>

        <div className="crm-header-actions">
          <button className="crm-btn crm-btn-secondary" onClick={loadFields} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
          <button className="crm-btn crm-btn-primary" onClick={() => setShowModal(true)}>
            <Plus size={14} />
            <span>New Custom Field</span>
          </button>
        </div>
      </div>

      <div className="crm-content">
        {error && (
          <div className="crm-alert-warning" style={{ marginBottom: '16px' }}>
            {error}
          </div>
        )}

        <div className="crm-table-container">
          <table className="crm-table">
            <thead>
              <tr>
                <th>Entity</th>
                <th>Label</th>
                <th>Field Key</th>
                <th>Data Type</th>
                <th>Required</th>
                <th>Encrypted (PII)</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && fields.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '32px', color: '#94a3b8' }}>
                    Loading custom fields...
                  </td>
                </tr>
              ) : fields.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '32px', color: '#64748b' }}>
                    No custom fields configured. Click "New Custom Field" to define one.
                  </td>
                </tr>
              ) : (
                fields.map((f) => (
                  <tr key={f.field_id}>
                    <td>
                      <span className="crm-badge crm-badge-stage">{f.entity_type}</span>
                    </td>
                    <td style={{ fontWeight: 600, color: '#f8fafc' }}>{f.label}</td>
                    <td style={{ fontFamily: 'monospace', color: '#818cf8', fontSize: '0.8rem' }}>
                      {f.name}
                    </td>
                    <td>
                      <span className="crm-tag-pill">{f.field_type}</span>
                    </td>
                    <td>
                      {f.is_required ? (
                        <CheckCircle size={15} color="#10b981" />
                      ) : (
                        <XCircle size={15} color="#475569" />
                      )}
                    </td>
                    <td>
                      {f.is_sensitive ? (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#fbbf24', fontSize: '0.8rem' }}>
                          <Lock size={12} />
                          <span>AES-256</span>
                        </span>
                      ) : (
                        <span style={{ color: '#475569', fontSize: '0.8rem' }}>Standard</span>
                      )}
                    </td>
                    <td>
                      <button
                        className="crm-btn crm-btn-danger"
                        style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                        onClick={() => handleDelete(f.field_id)}
                      >
                        <Trash2 size={12} />
                        <span>Delete</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="crm-modal-backdrop" onClick={() => setShowModal(false)}>
          <div className="crm-modal" onClick={(e) => e.stopPropagation()}>
            <div className="crm-modal-header">
              <h2 className="crm-modal-title">Create Custom Field Definition</h2>
              <button
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
                onClick={() => setShowModal(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreate}>
              <div className="crm-modal-body">
                {modalError && (
                  <div className="crm-alert-warning">
                    {modalError}
                  </div>
                )}

                <div className="crm-form-group">
                  <label>Applies To *</label>
                  <select
                    className="crm-form-control"
                    value={form.entity_type}
                    onChange={(e) => setForm({ ...form, entity_type: e.target.value })}
                  >
                    <option value="LEAD">Lead Entity</option>
                    <option value="CUSTOMER">Customer Entity</option>
                  </select>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="crm-form-group">
                    <label>Display Label *</label>
                    <input
                      type="text"
                      className="crm-form-control"
                      placeholder="e.g. Budget Approval Code"
                      value={form.label}
                      onChange={(e) => {
                        const lbl = e.target.value
                        setForm({
                          ...form,
                          label: lbl,
                          name: form.name || lbl.toLowerCase().replace(/[^a-z0-9]/g, '_')
                        })
                      }}
                      required
                    />
                  </div>

                  <div className="crm-form-group">
                    <label>System Key *</label>
                    <input
                      type="text"
                      className="crm-form-control"
                      placeholder="e.g. budget_approval_code"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <div className="crm-form-group">
                  <label>Field Data Type *</label>
                  <select
                    className="crm-form-control"
                    value={form.field_type}
                    onChange={(e) => setForm({ ...form, field_type: e.target.value })}
                  >
                    {FIELD_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </div>

                {['SELECT', 'MULTI_SELECT'].includes(form.field_type) && (
                  <div className="crm-form-group">
                    <label>Dropdown Options (comma separated) *</label>
                    <input
                      type="text"
                      className="crm-form-control"
                      placeholder="Option A, Option B, Option C"
                      value={form.options_text}
                      onChange={(e) => setForm({ ...form, options_text: e.target.value })}
                    />
                  </div>
                )}

                <div style={{ display: 'flex', gap: '20px', marginTop: '6px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', cursor: 'pointer', color: '#cbd5e1' }}>
                    <input
                      type="checkbox"
                      checked={form.is_required}
                      onChange={(e) => setForm({ ...form, is_required: e.target.checked })}
                    />
                    <span>Required Field</span>
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', cursor: 'pointer', color: '#fbbf24' }}>
                    <input
                      type="checkbox"
                      checked={form.is_sensitive}
                      onChange={(e) => setForm({ ...form, is_sensitive: e.target.checked })}
                    />
                    <span>Sensitive PII (Encrypt with AES-256)</span>
                  </label>
                </div>
              </div>

              <div className="crm-modal-footer">
                <button
                  type="button"
                  className="crm-btn crm-btn-secondary"
                  onClick={() => setShowModal(false)}
                  disabled={saving}
                >
                  Cancel
                </button>
                <button type="submit" className="crm-btn crm-btn-primary" disabled={saving}>
                  {saving ? 'Saving...' : 'Create Field Definition'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
