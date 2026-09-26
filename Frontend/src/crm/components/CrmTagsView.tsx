import React, { useState, useEffect, useCallback } from 'react'
import {
  Tag as TagIcon,
  Plus,
  Trash2,
  RefreshCw,
  AlertTriangle
} from 'lucide-react'
import { crmApi } from '../services/crmApi'

interface CrmTagsViewProps {
  token: string
}

export const CrmTagsView: React.FC<CrmTagsViewProps> = ({ token }) => {
  const [tags, setTags] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Create Tag state
  const [showModal, setShowModal] = useState(false)
  const [name, setName] = useState('')
  const [color, setColor] = useState('#6366f1')
  const [description, setDescription] = useState('')
  const [saving, setSaving] = useState(false)
  const [modalError, setModalError] = useState<string | null>(null)

  const loadTags = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await crmApi.getTags(token)
      const list = Array.isArray(data) ? data : data?.results || []
      setTags(list)
    } catch (err: any) {
      setError(err.message || 'Failed to load tags')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    loadTags()
  }, [loadTags])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    setSaving(true)
    setModalError(null)
    try {
      await crmApi.createTag(token, {
        name: name.trim(),
        color,
        description: description.trim() || undefined,
      })
      setShowModal(false)
      setName('')
      setDescription('')
      loadTags()
    } catch (err: any) {
      setModalError(err.message || 'Failed to create tag')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (tagId: string) => {
    if (!confirm('Are you sure you want to delete this tag?')) return
    try {
      await crmApi.deleteTag(token, tagId)
      loadTags()
    } catch (err: any) {
      setError(`Failed to delete tag: ${err.message}`)
    }
  }

  return (
    <div className="crm-container">
      <div className="crm-header">
        <div className="crm-header-title-group">
          <div className="crm-header-icon">
            <TagIcon size={20} />
          </div>
          <div>
            <h1 className="crm-header-title">CRM Tags</h1>
            <p className="crm-header-subtitle">
              Manage tenant-scoped classification tags for customers and leads
            </p>
          </div>
        </div>

        <div className="crm-header-actions">
          <button className="crm-btn crm-btn-secondary" onClick={loadTags} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
          <button className="crm-btn crm-btn-primary" onClick={() => setShowModal(true)}>
            <Plus size={14} />
            <span>New Tag</span>
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
                <th>Tag Preview</th>
                <th>Name</th>
                <th>Description</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && tags.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '32px', color: '#94a3b8' }}>
                    Loading tags...
                  </td>
                </tr>
              ) : tags.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '32px', color: '#64748b' }}>
                    No tags defined yet. Click "New Tag" to create one.
                  </td>
                </tr>
              ) : (
                tags.map((t) => (
                  <tr key={t.tag_id}>
                    <td>
                      <span
                        className="crm-tag-pill"
                        style={{
                          borderColor: t.color || '#6366f1',
                          color: t.color || '#6366f1',
                          fontSize: '0.82rem',
                          padding: '4px 10px',
                        }}
                      >
                        <TagIcon size={12} />
                        <span>{t.name}</span>
                      </span>
                    </td>
                    <td style={{ fontWeight: 600, color: '#f8fafc' }}>{t.name}</td>
                    <td style={{ color: '#94a3b8' }}>{t.description || '—'}</td>
                    <td style={{ color: '#64748b', fontSize: '0.8rem' }}>
                      {t.created_at ? new Date(t.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td>
                      <button
                        className="crm-btn crm-btn-danger"
                        style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                        onClick={() => handleDelete(t.tag_id)}
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
              <h2 className="crm-modal-title">Create New Tag</h2>
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
                  <label>Tag Name *</label>
                  <input
                    type="text"
                    className="crm-form-control"
                    placeholder="e.g. VIP Client"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                </div>

                <div className="crm-form-group">
                  <label>Color</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <input
                      type="color"
                      value={color}
                      onChange={(e) => setColor(e.target.value)}
                      style={{ width: '40px', height: '36px', background: 'none', border: 'none', cursor: 'pointer' }}
                    />
                    <input
                      type="text"
                      className="crm-form-control"
                      value={color}
                      onChange={(e) => setColor(e.target.value)}
                    />
                  </div>
                </div>

                <div className="crm-form-group">
                  <label>Description</label>
                  <textarea
                    className="crm-form-control"
                    rows={3}
                    placeholder="Optional description of when to use this tag..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
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
                  {saving ? 'Creating...' : 'Create Tag'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
