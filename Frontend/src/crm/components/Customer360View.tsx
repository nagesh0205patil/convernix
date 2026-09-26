import React, { useState, useEffect, useCallback } from 'react'
import {
  ArrowLeft,
  User,
  Phone,
  Mail,
  Calendar,
  MessageSquare,
  Activity as ActivityIcon,
  FileText,
  TrendingUp,
  Paperclip,
  GitMerge,
  Eye,
  EyeOff,
  AlertTriangle,
  Plus,
  Send,
  ExternalLink,
  ShieldCheck,
  Tag as TagIcon
} from 'lucide-react'
import { crmApi } from '../services/crmApi'

interface Customer360ViewProps {
  token: string
  customerId: string
  onBack: () => void
  onSelectLead: (leadId: string) => void
}

type TabType = 'overview' | 'conversations' | 'activities' | 'notes' | 'leads' | 'files'

export const Customer360View: React.FC<Customer360ViewProps> = ({
  token,
  customerId,
  onBack,
  onSelectLead,
}) => {
  const [data360, setData360] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<TabType>('overview')

  // PII reveal state
  const [revealPii, setRevealPii] = useState(false)
  const [unmaskedCustomer, setUnmaskedCustomer] = useState<any>(null)
  const [revealing, setRevealing] = useState(false)

  // Notes state
  const [notes, setNotes] = useState<any[]>([])
  const [newNote, setNewNote] = useState('')
  const [addingNote, setAddingNote] = useState(false)

  // Merge Modal state
  const [showMergeModal, setShowMergeModal] = useState(false)
  const [duplicateCustomerId, setDuplicateCustomerId] = useState('')
  const [mergeReason, setMergeReason] = useState('')
  const [merging, setMerging] = useState(false)
  const [mergeError, setMergeError] = useState<string | null>(null)

  const load360 = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await crmApi.getCustomer360(token, customerId)
      setData360(res)
      setNotes(res.notes || [])
    } catch (err: any) {
      setError(err.message || 'Failed to load Customer 360 data')
    } finally {
      setLoading(false)
    }
  }, [token, customerId])

  useEffect(() => {
    load360()
  }, [load360])

  const togglePiiReveal = async () => {
    if (revealPii) {
      setRevealPii(false)
      return
    }
    setRevealing(true)
    try {
      const full = await crmApi.getCustomer(token, customerId)
      setUnmaskedCustomer(full)
      setRevealPii(true)
    } catch (err: any) {
      setError(`Cannot reveal PII: ${err.message || 'Permission denied'}`)
    } finally {
      setRevealing(false)
    }
  }

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newNote.trim()) return
    setAddingNote(true)
    try {
      const created = await crmApi.addCustomerNote(token, customerId, newNote.trim())
      setNotes(prev => [created, ...prev])
      setNewNote('')
    } catch (err: any) {
      setError(`Failed to save note: ${err.message}`)
    } finally {
      setAddingNote(false)
    }
  }

  const handleMergeSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!duplicateCustomerId.trim()) return
    setMerging(true)
    setMergeError(null)
    try {
      await crmApi.mergeCustomers(token, {
        primary_customer_id: customerId,
        duplicate_customer_id: duplicateCustomerId.trim(),
        reason: mergeReason || 'Consolidated via Customer 360 interface',
      })
      setShowMergeModal(false)
      setDuplicateCustomerId('')
      setMergeReason('')
      load360()
    } catch (err: any) {
      setMergeError(err.message || 'Merge failed')
    } finally {
      setMerging(false)
    }
  }

  if (loading) {
    return (
      <div className="crm-container" style={{ padding: '32px', textAlign: 'center', color: '#94a3b8' }}>
        Loading Customer 360 profile...
      </div>
    )
  }

  if (!data360) {
    return (
      <div className="crm-container" style={{ padding: '32px' }}>
        <button className="crm-btn crm-btn-secondary" onClick={onBack}>
          <ArrowLeft size={14} /> Back
        </button>
        <div className="crm-alert-warning" style={{ marginTop: '16px' }}>
          Customer profile not found.
        </div>
      </div>
    )
  }

  const customer = data360.customer || {}
  const conversations = data360.conversations || []
  const activities = data360.activities || []
  const leads = data360.leads || []
  const files = data360.files || []
  const identities = customer.identities || []

  const displayPhone = revealPii && unmaskedCustomer?.phone
    ? unmaskedCustomer.phone
    : customer.phone_masked || '—'

  const displayEmail = revealPii && unmaskedCustomer?.email
    ? unmaskedCustomer.email
    : customer.email_masked || '—'

  return (
    <div className="crm-container">
      {/* Header */}
      <div className="crm-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button className="crm-btn crm-btn-secondary" onClick={onBack} title="Back">
            <ArrowLeft size={14} />
          </button>
          <div>
            <h1 className="crm-header-title">{customer.display_name}</h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
              <span className="crm-badge crm-badge-stage">{customer.status}</span>
              <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
                Customer ID: {customerId.substring(0, 8)}...
              </span>
            </div>
          </div>
        </div>

        <div className="crm-header-actions">
          <button
            className="crm-btn crm-btn-secondary"
            onClick={() => setShowMergeModal(true)}
            title="Merge with duplicate record"
          >
            <GitMerge size={14} />
            <span>Merge Customer</span>
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

        <div className="crm-c360-grid">
          {/* Left Column: Profile Card */}
          <div className="crm-c360-profile-card">
            <div className="crm-c360-avatar-header">
              <div className="crm-c360-avatar">
                {customer.display_name?.[0]?.toUpperCase() || 'C'}
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.05rem', color: '#fff', fontWeight: 600 }}>
                  {customer.display_name}
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                  Source: {customer.source || 'WHATSAPP'}
                </span>
              </div>
            </div>

            {/* Contact Details with Secure Reveal Toggle */}
            <div style={{ background: '#0d0f17', border: '1px solid #232738', borderRadius: '8px', padding: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600, letterSpacing: '0.05em' }}>
                  CONTACT INFO
                </span>
                <button
                  style={{
                    background: 'none',
                    border: 'none',
                    color: revealPii ? '#f87171' : '#818cf8',
                    cursor: 'pointer',
                    fontSize: '0.75rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: 0
                  }}
                  onClick={togglePiiReveal}
                  disabled={revealing}
                >
                  {revealPii ? <EyeOff size={12} /> : <Eye size={12} />}
                  <span>{revealPii ? 'Mask PII' : 'Reveal PII'}</span>
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.85rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#cbd5e1' }}>
                  <Phone size={14} color="#94a3b8" />
                  <span style={{ fontFamily: 'monospace' }}>{displayPhone}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#cbd5e1' }}>
                  <Mail size={14} color="#94a3b8" />
                  <span style={{ fontFamily: 'monospace' }}>{displayEmail}</span>
                </div>
              </div>
            </div>

            {/* Identities */}
            <div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600, marginBottom: '8px' }}>
                CONNECTED IDENTITIES
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {identities.length > 0 ? (
                  identities.map((id: any, idx: number) => (
                    <div
                      key={idx}
                      style={{
                        background: '#0d0f17',
                        border: '1px solid #1e2230',
                        borderRadius: '6px',
                        padding: '6px 10px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontSize: '0.8rem',
                      }}
                    >
                      <span style={{ color: '#818cf8', fontWeight: 500 }}>{id.provider}</span>
                      <span style={{ color: '#94a3b8', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                        {id.provider_key?.substring(0, 14)}...
                      </span>
                    </div>
                  ))
                ) : (
                  <div style={{ color: '#64748b', fontSize: '0.8rem' }}>None registered</div>
                )}
              </div>
            </div>

            {/* Tags */}
            <div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600, marginBottom: '8px' }}>
                TAGS
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {customer.tags && customer.tags.length > 0 ? (
                  customer.tags.map((tg: any, idx: number) => (
                    <span key={idx} className="crm-tag-pill">
                      <TagIcon size={11} />
                      {tg.name || tg}
                    </span>
                  ))
                ) : (
                  <span style={{ color: '#64748b', fontSize: '0.8rem' }}>No tags</span>
                )}
              </div>
            </div>

            {/* Important Timestamps */}
            <div style={{ fontSize: '0.75rem', color: '#64748b', borderTop: '1px solid #1e2436', paddingTop: '12px' }}>
              <div>First Contact: {customer.created_at ? new Date(customer.created_at).toLocaleDateString() : '—'}</div>
              <div>Last Activity: {customer.updated_at ? new Date(customer.updated_at).toLocaleString() : '—'}</div>
            </div>
          </div>

          {/* Right Column: Tabbed Sections */}
          <div className="crm-c360-tab-container">
            <div className="crm-c360-tabs">
              <button
                className={`crm-c360-tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
                onClick={() => setActiveTab('overview')}
              >
                Overview
              </button>
              <button
                className={`crm-c360-tab-btn ${activeTab === 'conversations' ? 'active' : ''}`}
                onClick={() => setActiveTab('conversations')}
              >
                <MessageSquare size={13} style={{ display: 'inline', marginRight: '4px' }} />
                Conversations ({conversations.length})
              </button>
              <button
                className={`crm-c360-tab-btn ${activeTab === 'activities' ? 'active' : ''}`}
                onClick={() => setActiveTab('activities')}
              >
                <ActivityIcon size={13} style={{ display: 'inline', marginRight: '4px' }} />
                Activities ({activities.length})
              </button>
              <button
                className={`crm-c360-tab-btn ${activeTab === 'notes' ? 'active' : ''}`}
                onClick={() => setActiveTab('notes')}
              >
                <FileText size={13} style={{ display: 'inline', marginRight: '4px' }} />
                Notes ({notes.length})
              </button>
              <button
                className={`crm-c360-tab-btn ${activeTab === 'leads' ? 'active' : ''}`}
                onClick={() => setActiveTab('leads')}
              >
                <TrendingUp size={13} style={{ display: 'inline', marginRight: '4px' }} />
                Leads ({leads.length})
              </button>
              <button
                className={`crm-c360-tab-btn ${activeTab === 'files' ? 'active' : ''}`}
                onClick={() => setActiveTab('files')}
              >
                <Paperclip size={13} style={{ display: 'inline', marginRight: '4px' }} />
                Files ({files.length})
              </button>
            </div>

            <div className="crm-c360-panel">
              {/* TAB 1: OVERVIEW */}
              {activeTab === 'overview' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px' }}>
                    <div style={{ background: '#0d0f17', border: '1px solid #232738', padding: '14px', borderRadius: '8px' }}>
                      <div style={{ fontSize: '0.75rem', color: '#64748b' }}>TOTAL LEADS</div>
                      <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc', marginTop: '4px' }}>
                        {leads.length}
                      </div>
                    </div>
                    <div style={{ background: '#0d0f17', border: '1px solid #232738', padding: '14px', borderRadius: '8px' }}>
                      <div style={{ fontSize: '0.75rem', color: '#64748b' }}>WON LEADS</div>
                      <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#10b981', marginTop: '4px' }}>
                        {leads.filter((l: any) => l.status === 'WON').length}
                      </div>
                    </div>
                    <div style={{ background: '#0d0f17', border: '1px solid #232738', padding: '14px', borderRadius: '8px' }}>
                      <div style={{ fontSize: '0.75rem', color: '#64748b' }}>CONVERSATIONS</div>
                      <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#818cf8', marginTop: '4px' }}>
                        {conversations.length}
                      </div>
                    </div>
                  </div>

                  {/* Active Lead Summary */}
                  <div>
                    <h4 style={{ fontSize: '0.9rem', color: '#f8fafc', marginBottom: '10px', fontWeight: 600 }}>
                      Current Opportunities
                    </h4>
                    {leads.filter((l: any) => l.status === 'OPEN').length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {leads
                          .filter((l: any) => l.status === 'OPEN')
                          .map((lead: any) => (
                            <div
                              key={lead.lead_id}
                              style={{
                                background: '#181c2b',
                                border: '1px solid #252b3e',
                                borderRadius: '8px',
                                padding: '12px 16px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                              }}
                            >
                              <div>
                                <button
                                  style={{ background: 'none', border: 'none', color: '#fff', fontWeight: 600, cursor: 'pointer', padding: 0 }}
                                  onClick={() => onSelectLead(lead.lead_id)}
                                >
                                  {lead.title}
                                </button>
                                <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px' }}>
                                  Stage: {lead.stage_name || lead.status} · Priority: {lead.priority}
                                </div>
                              </div>
                              <button
                                className="crm-btn crm-btn-secondary"
                                style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                                onClick={() => onSelectLead(lead.lead_id)}
                              >
                                View Lead
                              </button>
                            </div>
                          ))}
                      </div>
                    ) : (
                      <div style={{ color: '#64748b', fontSize: '0.85rem' }}>No open leads currently.</div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 2: CONVERSATIONS */}
              {activeTab === 'conversations' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                    Real-time WhatsApp conversations linked to this customer (Convernix Inbox Source of Truth):
                  </div>
                  {conversations.length > 0 ? (
                    conversations.map((conv: any) => (
                      <div
                        key={conv.conversation_id}
                        style={{
                          background: '#0d0f17',
                          border: '1px solid #232738',
                          borderRadius: '8px',
                          padding: '14px',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                          <span style={{ fontWeight: 600, color: '#cbd5e1', fontSize: '0.85rem' }}>
                            Conversation #{conv.conversation_id?.substring(0, 8)}
                          </span>
                          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                            Status: {conv.status || 'OPEN'}
                          </span>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {(conv.messages || []).map((msg: any, mIdx: number) => {
                            const isInbound = msg.direction === 'INBOUND'
                            return (
                              <div
                                key={mIdx}
                                style={{
                                  alignSelf: isInbound ? 'flex-start' : 'flex-end',
                                  maxWidth: '75%',
                                  background: isInbound ? '#1e2438' : '#312e81',
                                  padding: '8px 12px',
                                  borderRadius: '8px',
                                  fontSize: '0.82rem',
                                  color: '#f8fafc',
                                }}
                              >
                                <div>{msg.content || msg.text || '(Attachment)'}</div>
                                <div style={{ fontSize: '0.68rem', color: '#94a3b8', textAlign: 'right', marginTop: '2px' }}>
                                  {msg.created_at ? new Date(msg.created_at).toLocaleTimeString() : ''}
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div style={{ color: '#64748b', fontSize: '0.85rem' }}>No conversations recorded.</div>
                  )}
                </div>
              )}

              {/* TAB 3: ACTIVITIES */}
              {activeTab === 'activities' && (
                <div className="crm-timeline">
                  {activities.length > 0 ? (
                    activities.map((act: any, idx: number) => (
                      <div key={idx} className="crm-timeline-item">
                        <div className="crm-timeline-dot" />
                        <div className="crm-timeline-content">
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontWeight: 600, color: '#a5b4fc', fontSize: '0.85rem' }}>
                              {act.activity_type}
                            </span>
                            <span style={{ fontSize: '0.72rem', color: '#64748b' }}>
                              {act.created_at ? new Date(act.created_at).toLocaleString() : ''}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '4px' }}>
                            {act.description}
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div style={{ color: '#64748b', fontSize: '0.85rem' }}>No activities logged yet.</div>
                  )}
                </div>
              )}

              {/* TAB 4: NOTES */}
              {activeTab === 'notes' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {/* Add note form */}
                  <form onSubmit={handleAddNote} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <textarea
                      className="crm-form-control"
                      rows={3}
                      placeholder="Write an internal encrypted note..."
                      value={newNote}
                      onChange={(e) => setNewNote(e.target.value)}
                      disabled={addingNote}
                    />
                    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                      <button
                        type="submit"
                        className="crm-btn crm-btn-primary"
                        disabled={addingNote || !newNote.trim()}
                      >
                        <Send size={13} />
                        <span>{addingNote ? 'Saving...' : 'Add Encrypted Note'}</span>
                      </button>
                    </div>
                  </form>

                  {/* Notes list */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {notes.length > 0 ? (
                      notes.map((n: any, idx: number) => (
                        <div
                          key={idx}
                          style={{
                            background: '#0d0f17',
                            border: '1px solid #232738',
                            borderRadius: '8px',
                            padding: '12px',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                            <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 500 }}>
                              {n.created_by_name || 'Staff User'}
                            </span>
                            <span style={{ fontSize: '0.72rem', color: '#64748b' }}>
                              {n.created_at ? new Date(n.created_at).toLocaleString() : ''}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.85rem', color: '#f1f5f9', whiteSpace: 'pre-wrap' }}>
                            {n.content || n.note}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div style={{ color: '#64748b', fontSize: '0.85rem' }}>No notes yet.</div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 5: LEADS */}
              {activeTab === 'leads' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {leads.length > 0 ? (
                    leads.map((lead: any) => (
                      <div
                        key={lead.lead_id}
                        style={{
                          background: '#0d0f17',
                          border: '1px solid #232738',
                          borderRadius: '8px',
                          padding: '12px 16px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                        }}
                      >
                        <div>
                          <button
                            style={{ background: 'none', border: 'none', color: '#fff', fontWeight: 600, cursor: 'pointer', padding: 0 }}
                            onClick={() => onSelectLead(lead.lead_id)}
                          >
                            {lead.title}
                          </button>
                          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px' }}>
                            Status: {lead.status} · Value:{' '}
                            {lead.expected_value ? `$${Number(lead.expected_value).toLocaleString()}` : '—'}
                          </div>
                        </div>
                        <button
                          className="crm-btn crm-btn-secondary"
                          style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                          onClick={() => onSelectLead(lead.lead_id)}
                        >
                          View Lead
                        </button>
                      </div>
                    ))
                  ) : (
                    <div style={{ color: '#64748b', fontSize: '0.85rem' }}>No leads on file.</div>
                  )}
                </div>
              )}

              {/* TAB 6: FILES */}
              {activeTab === 'files' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {files.length > 0 ? (
                    files.map((file: any, idx: number) => (
                      <div
                        key={idx}
                        style={{
                          background: '#0d0f17',
                          border: '1px solid #232738',
                          borderRadius: '8px',
                          padding: '10px 14px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <Paperclip size={14} color="#818cf8" />
                          <span style={{ fontSize: '0.85rem', color: '#f1f5f9' }}>
                            {file.file_name || file.name || 'Attachment'}
                          </span>
                        </div>
                        <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                          {file.content_type || 'document'}
                        </span>
                      </div>
                    ))
                  ) : (
                    <div style={{ color: '#64748b', fontSize: '0.85rem' }}>No files or attachments.</div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Customer Merge Modal */}
      {showMergeModal && (
        <div className="crm-modal-backdrop" onClick={() => setShowMergeModal(false)}>
          <div className="crm-modal" onClick={(e) => e.stopPropagation()}>
            <div className="crm-modal-header">
              <h2 className="crm-modal-title">Merge Duplicate Customer</h2>
              <button
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
                onClick={() => setShowMergeModal(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleMergeSubmit}>
              <div className="crm-modal-body">
                {mergeError && (
                  <div className="crm-alert-warning">
                    {mergeError}
                  </div>
                )}

                <div className="crm-alert-warning" style={{ fontSize: '0.8rem' }}>
                  <strong>Caution:</strong> This operation consolidates all leads, conversations,
                  activities, notes, tags, and identities from the duplicate customer into this primary record
                  (<strong>{customer.display_name}</strong>). The duplicate customer status will be set to
                  MERGED.
                </div>

                <div className="crm-form-group">
                  <label>Duplicate Customer ID to Merge *</label>
                  <input
                    type="text"
                    className="crm-form-control"
                    placeholder="Enter duplicate customer UUID"
                    value={duplicateCustomerId}
                    onChange={(e) => setDuplicateCustomerId(e.target.value)}
                    required
                  />
                </div>

                <div className="crm-form-group">
                  <label>Reason for Merge</label>
                  <input
                    type="text"
                    className="crm-form-control"
                    placeholder="e.g. Verified duplicate phone identity"
                    value={mergeReason}
                    onChange={(e) => setMergeReason(e.target.value)}
                  />
                </div>
              </div>

              <div className="crm-modal-footer">
                <button
                  type="button"
                  className="crm-btn crm-btn-secondary"
                  onClick={() => setShowMergeModal(false)}
                  disabled={merging}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="crm-btn crm-btn-danger"
                  disabled={merging || !duplicateCustomerId.trim()}
                >
                  {merging ? 'Merging...' : 'Confirm Customer Merge'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
