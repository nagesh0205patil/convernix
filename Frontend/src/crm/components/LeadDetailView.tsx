import React, { useState, useEffect, useCallback } from 'react'
import {
  ArrowLeft,
  User,
  Building,
  Tag as TagIcon,
  Calendar,
  DollarSign,
  CheckCircle2,
  Clock,
  AlertTriangle,
  History,
  Shield,
  Send,
  Plus,
  Trash2,
  ExternalLink,
  Edit2
} from 'lucide-react'
import { crmApi } from '../services/crmApi'

interface LeadDetailViewProps {
  token: string
  leadId: string
  onBack: () => void
  onSelectCustomer: (customerId: string) => void
}

export const LeadDetailView: React.FC<LeadDetailViewProps> = ({
  token,
  leadId,
  onBack,
  onSelectCustomer,
}) => {
  const [lead, setLead] = useState<any>(null)
  const [pipeline, setPipeline] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [transitioning, setTransitioning] = useState(false)

  // Modals
  const [showAssignModal, setShowAssignModal] = useState(false)
  const [assignForm, setAssignForm] = useState({
    owner_user_id: '',
    department_id: '',
    reason: '',
  })
  const [assigning, setAssigning] = useState(false)

  const [newTagInput, setNewTagInput] = useState('')
  const [tagSaving, setTagSaving] = useState(false)

  const loadLead = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await crmApi.getLead(token, leadId)
      setLead(data)
      if (data.pipeline_id) {
        const pipeData = await crmApi.getPipelines(token)
        const list = Array.isArray(pipeData) ? pipeData : pipeData?.results || []
        const found = list.find((p: any) => p.pipeline_id === data.pipeline_id)
        if (found) setPipeline(found)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load lead details')
    } finally {
      setLoading(false)
    }
  }, [token, leadId])

  useEffect(() => {
    loadLead()
  }, [loadLead])

  const handleStageChange = async (targetStageId: string) => {
    if (!lead || transitioning || lead.stage_id === targetStageId) return

    // Save previous state for rollback
    const previousStageId = lead.stage_id
    const previousVersion = lead.version

    // Optimistic UI update
    setLead((prev: any) => ({
      ...prev,
      stage_id: targetStageId,
      version: (prev.version || 1) + 1,
    }))
    setTransitioning(true)
    setError(null)

    try {
      const updated = await crmApi.transitionLeadStage(token, leadId, {
        stage_id: targetStageId,
        expected_version: previousVersion,
        reason: 'Moved via CRM Lead Detail board',
      })
      setLead(updated)
    } catch (err: any) {
      // Rollback on rejection
      setLead((prev: any) => ({
        ...prev,
        stage_id: previousStageId,
        version: previousVersion,
      }))
      setError(`Stage update rejected: ${err.message || 'Optimistic lock conflict'}`)
    } finally {
      setTransitioning(false)
    }
  }

  const handleAssign = async (e: React.FormEvent) => {
    e.preventDefault()
    setAssigning(true)
    try {
      const updated = await crmApi.assignLead(token, leadId, {
        owner_user_id: assignForm.owner_user_id || undefined,
        department_id: assignForm.department_id || undefined,
        reason: assignForm.reason || 'Manual reassignment',
      })
      setLead(updated)
      setShowAssignModal(false)
      setAssignForm({ owner_user_id: '', department_id: '', reason: '' })
    } catch (err: any) {
      setError(`Failed to assign: ${err.message}`)
    } finally {
      setAssigning(false)
    }
  }

  const handleAddTag = async (e: React.FormEvent) => {
    e.preventDefault()
    const tag = newTagInput.trim()
    if (!tag || !lead) return
    const currentTags = (lead.tags || []).map((t: any) => (typeof t === 'string' ? t : t.name))
    if (currentTags.includes(tag)) {
      setNewTagInput('')
      return
    }
    const updatedTags = [...currentTags, tag]
    setTagSaving(true)
    try {
      const res = await crmApi.updateLeadTags(token, leadId, updatedTags)
      setLead((prev: any) => ({ ...prev, tags: res.tags }))
      setNewTagInput('')
    } catch (err: any) {
      setError(`Failed to add tag: ${err.message}`)
    } finally {
      setTagSaving(false)
    }
  }

  const handleRemoveTag = async (tagName: string) => {
    if (!lead) return
    const currentTags = (lead.tags || []).map((t: any) => (typeof t === 'string' ? t : t.name))
    const updatedTags = currentTags.filter((t: string) => t !== tagName)
    setTagSaving(true)
    try {
      const res = await crmApi.updateLeadTags(token, leadId, updatedTags)
      setLead((prev: any) => ({ ...prev, tags: res.tags }))
    } catch (err: any) {
      setError(`Failed to remove tag: ${err.message}`)
    } finally {
      setTagSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="crm-container" style={{ padding: '32px', textAlign: 'center', color: '#94a3b8' }}>
        Loading lead details...
      </div>
    )
  }

  if (!lead) {
    return (
      <div className="crm-container" style={{ padding: '32px' }}>
        <button className="crm-btn crm-btn-secondary" onClick={onBack}>
          <ArrowLeft size={14} /> Back to Leads
        </button>
        <div className="crm-alert-warning" style={{ marginTop: '16px' }}>
          Lead not found or inaccessible.
        </div>
      </div>
    )
  }

  const orderedStages = pipeline?.stages || []

  return (
    <div className="crm-container">
      {/* Top Header */}
      <div className="crm-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button className="crm-btn crm-btn-secondary" onClick={onBack} title="Back">
            <ArrowLeft size={14} />
          </button>
          <div>
            <h1 className="crm-header-title">{lead.title}</h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
              <span className="crm-badge crm-badge-stage">{lead.status}</span>
              <span className={`crm-badge crm-badge-priority-${lead.priority.toLowerCase()}`}>
                {lead.priority}
              </span>
              <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
                ID: {lead.lead_id?.substring(0, 8)}... (v{lead.version || 1})
              </span>
            </div>
          </div>
        </div>

        <div className="crm-header-actions">
          <button
            className="crm-btn crm-btn-secondary"
            onClick={() => setShowAssignModal(true)}
          >
            <User size={14} />
            <span>Assign Owner</span>
          </button>
          <button
            className="crm-btn crm-btn-primary"
            onClick={() => onSelectCustomer(lead.customer_id)}
          >
            <ExternalLink size={14} />
            <span>Open Customer 360</span>
          </button>
        </div>
      </div>

      <div className="crm-content">
        {error && (
          <div className="crm-alert-warning" style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Pipeline Stage Progression Bar */}
        {orderedStages.length > 0 && (
          <div
            style={{
              background: '#141722',
              border: '1px solid #232738',
              borderRadius: '10px',
              padding: '16px',
              marginBottom: '20px',
            }}
          >
            <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '12px', fontWeight: 600 }}>
              PIPELINE STAGE: {pipeline.name}
            </div>
            <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
              {orderedStages.map((st: any) => {
                const isActive = lead.stage_id === st.stage_id
                return (
                  <button
                    key={st.stage_id}
                    className="crm-btn"
                    style={{
                      flex: 1,
                      minWidth: '130px',
                      justifyContent: 'center',
                      background: isActive ? '#4f46e5' : '#1a1e2d',
                      borderColor: isActive ? '#6366f1' : '#282f45',
                      color: isActive ? '#fff' : '#94a3b8',
                      cursor: transitioning ? 'not-allowed' : 'pointer',
                    }}
                    onClick={() => handleStageChange(st.stage_id)}
                    disabled={transitioning}
                  >
                    {isActive ? <CheckCircle2 size={14} /> : <Clock size={14} />}
                    <span>{st.name}</span>
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Main Grid: Details + Timeline */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '20px' }}>
          {/* Left Column: Lead Info & Custom Fields */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Lead Properties Card */}
            <div
              style={{
                background: '#141722',
                border: '1px solid #232738',
                borderRadius: '10px',
                padding: '20px',
              }}
            >
              <h2 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc', marginBottom: '16px' }}>
                Lead Details
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', fontSize: '0.85rem' }}>
                <div>
                  <div style={{ color: '#64748b', marginBottom: '4px' }}>Associated Customer</div>
                  <button
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#818cf8',
                      fontWeight: 600,
                      cursor: 'pointer',
                      padding: 0,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                    onClick={() => onSelectCustomer(lead.customer_id)}
                  >
                    <User size={14} />
                    <span>{lead.customer_name || 'Customer'}</span>
                    <ExternalLink size={12} />
                  </button>
                </div>

                <div>
                  <div style={{ color: '#64748b', marginBottom: '4px' }}>Expected Value</div>
                  <div style={{ fontWeight: 600, color: '#10b981', fontSize: '1rem' }}>
                    {lead.expected_value
                      ? `$${Number(lead.expected_value).toLocaleString()} ${lead.currency || 'USD'}`
                      : '—'}
                  </div>
                </div>

                <div>
                  <div style={{ color: '#64748b', marginBottom: '4px' }}>Primary Owner</div>
                  <div style={{ color: '#f1f5f9', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <User size={14} color="#94a3b8" />
                    <span>{lead.owner_name || 'Unassigned'}</span>
                  </div>
                </div>

                <div>
                  <div style={{ color: '#64748b', marginBottom: '4px' }}>Department</div>
                  <div style={{ color: '#f1f5f9', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Building size={14} color="#94a3b8" />
                    <span>{lead.department_name || 'No Department'}</span>
                  </div>
                </div>

                <div>
                  <div style={{ color: '#64748b', marginBottom: '4px' }}>Source</div>
                  <div style={{ color: '#cbd5e1' }}>{lead.source || 'MANUAL'}</div>
                </div>

                <div>
                  <div style={{ color: '#64748b', marginBottom: '4px' }}>Created Date</div>
                  <div style={{ color: '#cbd5e1' }}>
                    {lead.created_at ? new Date(lead.created_at).toLocaleString() : '—'}
                  </div>
                </div>
              </div>
            </div>

            {/* Tags Card */}
            <div
              style={{
                background: '#141722',
                border: '1px solid #232738',
                borderRadius: '10px',
                padding: '20px',
              }}
            >
              <h2 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc', marginBottom: '12px' }}>
                Tags
              </h2>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                {lead.tags && lead.tags.length > 0 ? (
                  lead.tags.map((tg: any, idx: number) => {
                    const tagName = typeof tg === 'string' ? tg : tg.name
                    return (
                      <span key={idx} className="crm-tag-pill" style={{ padding: '4px 10px', fontSize: '0.8rem' }}>
                        <TagIcon size={12} />
                        <span>{tagName}</span>
                        <button
                          style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: 0 }}
                          onClick={() => handleRemoveTag(tagName)}
                          title="Remove tag"
                        >
                          ✕
                        </button>
                      </span>
                    )
                  })
                ) : (
                  <div style={{ color: '#64748b', fontSize: '0.85rem' }}>No tags assigned</div>
                )}
              </div>

              <form onSubmit={handleAddTag} style={{ display: 'flex', gap: '8px', maxWidth: '300px' }}>
                <input
                  type="text"
                  className="crm-form-control"
                  placeholder="Add tag..."
                  value={newTagInput}
                  onChange={(e) => setNewTagInput(e.target.value)}
                  disabled={tagSaving}
                />
                <button type="submit" className="crm-btn crm-btn-secondary" disabled={tagSaving || !newTagInput.trim()}>
                  <Plus size={14} /> Add
                </button>
              </form>
            </div>

            {/* Custom Fields Card */}
            <div
              style={{
                background: '#141722',
                border: '1px solid #232738',
                borderRadius: '10px',
                padding: '20px',
              }}
            >
              <h2 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc', marginBottom: '12px' }}>
                Custom Fields
              </h2>
              {lead.custom_fields && Object.keys(lead.custom_fields).length > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  {Object.entries(lead.custom_fields).map(([k, v]: any) => (
                    <div key={k} style={{ background: '#0d0f17', padding: '10px 14px', borderRadius: '6px', border: '1px solid #232738' }}>
                      <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase' }}>{k}</div>
                      <div style={{ fontSize: '0.85rem', color: '#cbd5e1', marginTop: '2px', fontWeight: 500 }}>
                        {String(v)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: '#64748b', fontSize: '0.85rem' }}>
                  No custom fields configured for this lead.
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Stage & Assignment History */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div
              style={{
                background: '#141722',
                border: '1px solid #232738',
                borderRadius: '10px',
                padding: '20px',
              }}
            >
              <h2 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <History size={16} />
                <span>Stage History</span>
              </h2>

              <div className="crm-timeline">
                {lead.stage_history && lead.stage_history.length > 0 ? (
                  lead.stage_history.map((hist: any, idx: number) => (
                    <div key={idx} className="crm-timeline-item">
                      <div className="crm-timeline-dot" />
                      <div className="crm-timeline-content">
                        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#a5b4fc' }}>
                          {hist.from_stage_name || 'Start'} → {hist.to_stage_name}
                        </div>
                        <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '2px' }}>
                          by {hist.changed_by_name || 'System'} · {new Date(hist.created_at).toLocaleDateString()}
                        </div>
                        {hist.reason && (
                          <div style={{ fontSize: '0.75rem', color: '#cbd5e1', marginTop: '4px' }}>
                            "{hist.reason}"
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <div style={{ color: '#64748b', fontSize: '0.8rem' }}>No stage transitions recorded.</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Reassign Modal */}
      {showAssignModal && (
        <div className="crm-modal-backdrop" onClick={() => setShowAssignModal(false)}>
          <div className="crm-modal" onClick={(e) => e.stopPropagation()}>
            <div className="crm-modal-header">
              <h2 className="crm-modal-title">Assign Lead Owner & Department</h2>
              <button
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
                onClick={() => setShowAssignModal(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAssign}>
              <div className="crm-modal-body">
                <div className="crm-form-group">
                  <label>Owner User ID (UUID)</label>
                  <input
                    type="text"
                    className="crm-form-control"
                    placeholder="Enter user UUID or leave blank"
                    value={assignForm.owner_user_id}
                    onChange={(e) => setAssignForm({ ...assignForm, owner_user_id: e.target.value })}
                  />
                </div>

                <div className="crm-form-group">
                  <label>Department ID (UUID)</label>
                  <input
                    type="text"
                    className="crm-form-control"
                    placeholder="Enter department UUID or leave blank"
                    value={assignForm.department_id}
                    onChange={(e) => setAssignForm({ ...assignForm, department_id: e.target.value })}
                  />
                </div>

                <div className="crm-form-group">
                  <label>Reason for Assignment</label>
                  <input
                    type="text"
                    className="crm-form-control"
                    placeholder="e.g. Inbound tier 2 assignment"
                    value={assignForm.reason}
                    onChange={(e) => setAssignForm({ ...assignForm, reason: e.target.value })}
                  />
                </div>
              </div>

              <div className="crm-modal-footer">
                <button
                  type="button"
                  className="crm-btn crm-btn-secondary"
                  onClick={() => setShowAssignModal(false)}
                  disabled={assigning}
                >
                  Cancel
                </button>
                <button type="submit" className="crm-btn crm-btn-primary" disabled={assigning}>
                  {assigning ? 'Saving...' : 'Save Assignment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
