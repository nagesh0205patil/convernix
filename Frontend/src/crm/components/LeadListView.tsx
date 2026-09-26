import React, { useState, useEffect, useCallback } from 'react'
import {
  Search,
  Filter,
  Plus,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  User,
  Building,
  Tag as TagIcon,
  AlertCircle,
  ExternalLink,
  DollarSign
} from 'lucide-react'
import { crmApi } from '../services/crmApi'

interface LeadListViewProps {
  token: string
  onSelectLead: (leadId: string) => void
  onSelectCustomer: (customerId: string) => void
}

export const LeadListView: React.FC<LeadListViewProps> = ({
  token,
  onSelectLead,
  onSelectCustomer,
}) => {
  const [leads, setLeads] = useState<any[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(15)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [search, setSearch] = useState('')
  const [stageFilter, setStageFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sortField, setSortField] = useState('-created_at')

  // Metadata for dropdowns
  const [pipelines, setPipelines] = useState<any[]>([])
  const [stages, setStages] = useState<any[]>([])

  // Create Modal
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [customers, setCustomers] = useState<any[]>([])
  const [createForm, setCreateForm] = useState({
    customer_id: '',
    title: '',
    pipeline_id: '',
    stage_id: '',
    priority: 'MEDIUM',
    expected_value: '',
    currency: 'USD',
  })
  const [createError, setCreateError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  const loadPipelines = useCallback(async () => {
    try {
      const data = await crmApi.getPipelines(token)
      const list = Array.isArray(data) ? data : data?.results || []
      setPipelines(list)
      if (list.length > 0) {
        const allStages = list.flatMap((p: any) => p.stages || [])
        setStages(allStages)
        if (!createForm.pipeline_id && list[0]) {
          setCreateForm(prev => ({
            ...prev,
            pipeline_id: list[0].pipeline_id,
            stage_id: list[0].stages?.[0]?.stage_id || ''
          }))
        }
      }
    } catch (err: any) {
      console.error('Failed to load pipelines', err)
    }
  }, [token, createForm.pipeline_id])

  const loadLeads = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, any> = {
        page,
        page_size: pageSize,
        search: search.trim() || undefined,
        stage_id: stageFilter || undefined,
        priority: priorityFilter || undefined,
        status: statusFilter || undefined,
        ordering: sortField,
      }
      const data = await crmApi.getLeads(token, params)
      const items = Array.isArray(data) ? data : data?.results || []
      setLeads(items)
      setTotalCount(data?.count || items.length)
    } catch (err: any) {
      setError(err.message || 'Failed to load leads')
    } finally {
      setLoading(false)
    }
  }, [token, page, pageSize, search, stageFilter, priorityFilter, statusFilter, sortField])

  useEffect(() => {
    loadPipelines()
  }, [loadPipelines])

  useEffect(() => {
    loadLeads()
  }, [loadLeads])

  const openCreateDialog = async () => {
    setCreateError(null)
    try {
      const custData = await crmApi.getCustomers(token, { page_size: 50 })
      const custList = Array.isArray(custData) ? custData : custData?.results || []
      setCustomers(custList)
      if (custList.length > 0 && !createForm.customer_id) {
        setCreateForm(prev => ({ ...prev, customer_id: custList[0].customer_id }))
      }
    } catch (err) {
      console.error('Failed to load customers for modal', err)
    }
    setShowCreateModal(true)
  }

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!createForm.title.trim() || !createForm.customer_id) {
      setCreateError('Please enter a title and select a customer.')
      return
    }
    setCreating(true)
    setCreateError(null)
    try {
      const payload: any = {
        customer_id: createForm.customer_id,
        title: createForm.title.trim(),
        pipeline_id: createForm.pipeline_id || undefined,
        stage_id: createForm.stage_id || undefined,
        priority: createForm.priority,
        currency: createForm.currency,
      }
      if (createForm.expected_value) {
        payload.expected_value = parseFloat(createForm.expected_value)
      }
      await crmApi.createLead(token, payload)
      setShowCreateModal(false)
      setCreateForm({
        customer_id: '',
        title: '',
        pipeline_id: pipelines[0]?.pipeline_id || '',
        stage_id: pipelines[0]?.stages?.[0]?.stage_id || '',
        priority: 'MEDIUM',
        expected_value: '',
        currency: 'USD',
      })
      loadLeads()
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create lead')
    } finally {
      setCreating(false)
    }
  }

  const totalPages = Math.ceil(totalCount / pageSize) || 1

  return (
    <div className="crm-container">
      {/* Header */}
      <div className="crm-header">
        <div className="crm-header-title-group">
          <div className="crm-header-icon">
            <TrendingUp size={20} />
          </div>
          <div>
            <h1 className="crm-header-title">Leads Management</h1>
            <p className="crm-header-subtitle">
              Manage opportunities, pipeline tracking, customer association & ownership
            </p>
          </div>
        </div>

        <div className="crm-header-actions">
          <button
            className="crm-btn crm-btn-secondary"
            onClick={loadLeads}
            disabled={loading}
            title="Refresh Leads"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
          <button
            className="crm-btn crm-btn-primary"
            onClick={openCreateDialog}
          >
            <Plus size={15} />
            <span>Create Lead</span>
          </button>
        </div>
      </div>

      <div className="crm-content">
        {/* Filter Bar */}
        <div className="crm-filter-bar">
          <div className="crm-search-box">
            <Search size={15} color="#64748b" />
            <input
              type="text"
              placeholder="Search leads by title..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Filter size={14} color="#64748b" />
            <select
              className="crm-filter-select"
              value={stageFilter}
              onChange={(e) => {
                setStageFilter(e.target.value)
                setPage(1)
              }}
            >
              <option value="">All Stages</option>
              {stages.map((st: any) => (
                <option key={st.stage_id} value={st.stage_id}>
                  {st.name}
                </option>
              ))}
            </select>

            <select
              className="crm-filter-select"
              value={priorityFilter}
              onChange={(e) => {
                setPriorityFilter(e.target.value)
                setPage(1)
              }}
            >
              <option value="">All Priorities</option>
              <option value="LOW">Low</option>
              <option value="MEDIUM">Medium</option>
              <option value="HIGH">High</option>
              <option value="URGENT">Urgent</option>
            </select>

            <select
              className="crm-filter-select"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setPage(1)
              }}
            >
              <option value="">All Statuses</option>
              <option value="OPEN">Open</option>
              <option value="WON">Won</option>
              <option value="LOST">Lost</option>
              <option value="ARCHIVED">Archived</option>
            </select>

            <select
              className="crm-filter-select"
              value={sortField}
              onChange={(e) => setSortField(e.target.value)}
            >
              <option value="-created_at">Newest First</option>
              <option value="created_at">Oldest First</option>
              <option value="-expected_value">Highest Value</option>
              <option value="expected_value">Lowest Value</option>
              <option value="-priority">Priority</option>
            </select>
          </div>
        </div>

        {error && (
          <div className="crm-alert-warning" style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Lead Table */}
        <div className="crm-table-container">
          <table className="crm-table">
            <thead>
              <tr>
                <th>Opportunity / Title</th>
                <th>Customer</th>
                <th>Stage</th>
                <th>Priority</th>
                <th>Value</th>
                <th>Owner / Dept</th>
                <th>Tags</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && leads.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '32px', color: '#94a3b8' }}>
                    Loading leads...
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '32px', color: '#64748b' }}>
                    No leads found matching your criteria. Click "Create Lead" to add one.
                  </td>
                </tr>
              ) : (
                leads.map((lead: any) => (
                  <tr key={lead.lead_id}>
                    <td>
                      <button
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#f8fafc',
                          fontWeight: 600,
                          cursor: 'pointer',
                          padding: 0,
                          textAlign: 'left',
                          fontSize: '0.85rem'
                        }}
                        onClick={() => onSelectLead(lead.lead_id)}
                      >
                        {lead.title}
                      </button>
                      <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}>
                        Source: {lead.source || 'MANUAL'}
                      </div>
                    </td>
                    <td>
                      <button
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#818cf8',
                          cursor: 'pointer',
                          padding: 0,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          fontSize: '0.85rem'
                        }}
                        onClick={() => onSelectCustomer(lead.customer_id)}
                        title="Open Customer 360"
                      >
                        <User size={13} />
                        <span>{lead.customer_name || 'Customer'}</span>
                        <ExternalLink size={11} />
                      </button>
                    </td>
                    <td>
                      <span className="crm-badge crm-badge-stage">
                        {lead.stage_name || lead.status}
                      </span>
                    </td>
                    <td>
                      <span className={`crm-badge crm-badge-priority-${lead.priority.toLowerCase()}`}>
                        {lead.priority}
                      </span>
                    </td>
                    <td>
                      {lead.expected_value ? (
                        <span style={{ fontWeight: 600, color: '#10b981' }}>
                          ${Number(lead.expected_value).toLocaleString()} {lead.currency}
                        </span>
                      ) : (
                        <span style={{ color: '#64748b' }}>—</span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '0.78rem' }}>
                        {lead.owner_name && (
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <User size={12} color="#94a3b8" />
                            {lead.owner_name}
                          </span>
                        )}
                        {lead.department_name && (
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#94a3b8' }}>
                            <Building size={12} />
                            {lead.department_name}
                          </span>
                        )}
                        {!lead.owner_name && !lead.department_name && (
                          <span style={{ color: '#64748b' }}>Unassigned</span>
                        )}
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {lead.tags && lead.tags.length > 0 ? (
                          lead.tags.map((tg: any, idx: number) => (
                            <span key={idx} className="crm-tag-pill" style={tg.color ? { borderColor: tg.color, color: tg.color } : {}}>
                              <TagIcon size={10} />
                              {tg.name || tg}
                            </span>
                          ))
                        ) : (
                          <span style={{ color: '#475569', fontSize: '0.75rem' }}>—</span>
                        )}
                      </div>
                    </td>
                    <td style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                      {lead.created_at ? new Date(lead.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td>
                      <button
                        className="crm-btn crm-btn-secondary"
                        style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                        onClick={() => onSelectLead(lead.lead_id)}
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {/* Pagination */}
          <div className="crm-pagination">
            <div>
              Showing {leads.length > 0 ? (page - 1) * pageSize + 1 : 0} to{' '}
              {Math.min(page * pageSize, totalCount)} of {totalCount} leads
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <select
                className="crm-filter-select"
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value))
                  setPage(1)
                }}
              >
                <option value={10}>10 / page</option>
                <option value={15}>15 / page</option>
                <option value={25}>25 / page</option>
                <option value={50}>50 / page</option>
              </select>

              <button
                className="crm-btn crm-btn-secondary"
                style={{ padding: '6px 10px' }}
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft size={14} />
              </button>
              <span>
                Page {page} of {totalPages}
              </span>
              <button
                className="crm-btn crm-btn-secondary"
                style={{ padding: '6px 10px' }}
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Create Lead Modal */}
      {showCreateModal && (
        <div className="crm-modal-backdrop" onClick={() => setShowCreateModal(false)}>
          <div className="crm-modal" onClick={(e) => e.stopPropagation()}>
            <div className="crm-modal-header">
              <h2 className="crm-modal-title">Create New Lead</h2>
              <button
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
                onClick={() => setShowCreateModal(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSubmit}>
              <div className="crm-modal-body">
                {createError && (
                  <div className="crm-alert-warning">
                    {createError}
                  </div>
                )}

                <div className="crm-form-group">
                  <label>Customer *</label>
                  <select
                    className="crm-form-control"
                    value={createForm.customer_id}
                    onChange={(e) => setCreateForm({ ...createForm, customer_id: e.target.value })}
                    required
                  >
                    <option value="">Select Customer</option>
                    {customers.map((c: any) => (
                      <option key={c.customer_id} value={c.customer_id}>
                        {c.display_name} {c.phone_masked ? `(${c.phone_masked})` : ''}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="crm-form-group">
                  <label>Lead Title / Opportunity *</label>
                  <input
                    type="text"
                    className="crm-form-control"
                    placeholder="e.g. Enterprise License Upgrade 2026"
                    value={createForm.title}
                    onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                    required
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="crm-form-group">
                    <label>Pipeline</label>
                    <select
                      className="crm-form-control"
                      value={createForm.pipeline_id}
                      onChange={(e) => {
                        const pid = e.target.value
                        const p = pipelines.find((x: any) => x.pipeline_id === pid)
                        setCreateForm({
                          ...createForm,
                          pipeline_id: pid,
                          stage_id: p?.stages?.[0]?.stage_id || ''
                        })
                      }}
                    >
                      {pipelines.map((p: any) => (
                        <option key={p.pipeline_id} value={p.pipeline_id}>
                          {p.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="crm-form-group">
                    <label>Stage</label>
                    <select
                      className="crm-form-control"
                      value={createForm.stage_id}
                      onChange={(e) => setCreateForm({ ...createForm, stage_id: e.target.value })}
                    >
                      {pipelines
                        .find((p: any) => p.pipeline_id === createForm.pipeline_id)
                        ?.stages?.map((st: any) => (
                          <option key={st.stage_id} value={st.stage_id}>
                            {st.name}
                          </option>
                        )) || <option value="">No stages</option>}
                    </select>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="crm-form-group">
                    <label>Priority</label>
                    <select
                      className="crm-form-control"
                      value={createForm.priority}
                      onChange={(e) => setCreateForm({ ...createForm, priority: e.target.value })}
                    >
                      <option value="LOW">Low</option>
                      <option value="MEDIUM">Medium</option>
                      <option value="HIGH">High</option>
                      <option value="URGENT">Urgent</option>
                    </select>
                  </div>

                  <div className="crm-form-group">
                    <label>Expected Value</label>
                    <input
                      type="number"
                      step="0.01"
                      className="crm-form-control"
                      placeholder="e.g. 5000"
                      value={createForm.expected_value}
                      onChange={(e) => setCreateForm({ ...createForm, expected_value: e.target.value })}
                    />
                  </div>
                </div>
              </div>

              <div className="crm-modal-footer">
                <button
                  type="button"
                  className="crm-btn crm-btn-secondary"
                  onClick={() => setShowCreateModal(false)}
                  disabled={creating}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="crm-btn crm-btn-primary"
                  disabled={creating}
                >
                  {creating ? 'Creating...' : 'Create Lead'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
