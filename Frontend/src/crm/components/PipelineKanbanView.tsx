import React, { useState, useEffect, useCallback } from 'react'
import {
  Kanban,
  RefreshCw,
  Plus,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  User,
  DollarSign,
  Filter,
  Tag as TagIcon
} from 'lucide-react'
import { crmApi } from '../services/crmApi'

interface PipelineKanbanViewProps {
  token: string
  onSelectLead: (leadId: string) => void
  onSelectCustomer: (customerId: string) => void
}

export const PipelineKanbanView: React.FC<PipelineKanbanViewProps> = ({
  token,
  onSelectLead,
  onSelectCustomer,
}) => {
  const [pipelines, setPipelines] = useState<any[]>([])
  const [selectedPipelineId, setSelectedPipelineId] = useState<string>('')
  const [stages, setStages] = useState<any[]>([])
  const [leads, setLeads] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [transitioningLeadId, setTransitioningLeadId] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const pipeData = await crmApi.getPipelines(token)
      const pList = Array.isArray(pipeData) ? pipeData : pipeData?.results || []
      setPipelines(pList)

      let currentPipelineId = selectedPipelineId
      if (!currentPipelineId && pList.length > 0) {
        currentPipelineId = pList[0].pipeline_id
        setSelectedPipelineId(currentPipelineId)
      }

      const activePipe = pList.find((p: any) => p.pipeline_id === currentPipelineId) || pList[0]
      if (activePipe && activePipe.stages) {
        setStages(activePipe.stages)
      }

      // Load leads for this pipeline
      const leadData = await crmApi.getLeads(token, {
        pipeline_id: currentPipelineId || undefined,
        page_size: 100,
      })
      const lList = Array.isArray(leadData) ? leadData : leadData?.results || []
      setLeads(lList)
    } catch (err: any) {
      setError(err.message || 'Failed to load pipeline data')
    } finally {
      setLoading(false)
    }
  }, [token, selectedPipelineId])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleStageMove = async (lead: any, targetStageId: string) => {
    if (lead.stage_id === targetStageId || transitioningLeadId) return

    const previousStageId = lead.stage_id
    const previousVersion = lead.version || 1

    // Optimistic UI state update
    setLeads((prev) =>
      prev.map((l) =>
        l.lead_id === lead.lead_id
          ? { ...l, stage_id: targetStageId, version: previousVersion + 1 }
          : l
      )
    )
    setTransitioningLeadId(lead.lead_id)
    setError(null)

    try {
      const updated = await crmApi.transitionLeadStage(token, lead.lead_id, {
        stage_id: targetStageId,
        expected_version: previousVersion,
        reason: 'Moved via Kanban stage transition',
      })
      // Sync with server result
      setLeads((prev) =>
        prev.map((l) => (l.lead_id === lead.lead_id ? updated : l))
      )
    } catch (err: any) {
      // Rollback on rejection
      setLeads((prev) =>
        prev.map((l) =>
          l.lead_id === lead.lead_id
            ? { ...l, stage_id: previousStageId, version: previousVersion }
            : l
        )
      )
      setError(`Stage transition rejected: ${err.message || 'Optimistic lock error'}`)
    } finally {
      setTransitioningLeadId(null)
    }
  }

  // Calculate summary metrics
  const totalValue = leads.reduce((acc, l) => acc + (Number(l.expected_value) || 0), 0)

  return (
    <div className="crm-container">
      {/* Header */}
      <div className="crm-header">
        <div className="crm-header-title-group">
          <div className="crm-header-icon">
            <Kanban size={20} />
          </div>
          <div>
            <h1 className="crm-header-title">Pipeline Kanban</h1>
            <p className="crm-header-subtitle">
              Visual deal flow, opportunity stages, and optimistic stage transitions
            </p>
          </div>
        </div>

        <div className="crm-header-actions">
          {pipelines.length > 1 && (
            <select
              className="crm-filter-select"
              value={selectedPipelineId}
              onChange={(e) => setSelectedPipelineId(e.target.value)}
            >
              {pipelines.map((p) => (
                <option key={p.pipeline_id} value={p.pipeline_id}>
                  {p.name}
                </option>
              ))}
            </select>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', color: '#10b981', fontWeight: 600 }}>
            <span>Total Value: ${totalValue.toLocaleString()}</span>
          </div>

          <button className="crm-btn crm-btn-secondary" onClick={loadData} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
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

        {/* Kanban Columns */}
        <div className="crm-kanban-board">
          {stages.map((stage, sIdx) => {
            const stageLeads = leads.filter((l) => l.stage_id === stage.stage_id)
            const stageVal = stageLeads.reduce((acc, l) => acc + (Number(l.expected_value) || 0), 0)
            const prevStage = sIdx > 0 ? stages[sIdx - 1] : null
            const nextStage = sIdx < stages.length - 1 ? stages[sIdx + 1] : null

            return (
              <div key={stage.stage_id} className="crm-kanban-column">
                <div className="crm-kanban-column-header">
                  <div className="crm-kanban-column-title">
                    <span>{stage.name}</span>
                    <span className="crm-kanban-count">{stageLeads.length}</span>
                  </div>
                  {stageVal > 0 && (
                    <span style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600 }}>
                      ${stageVal.toLocaleString()}
                    </span>
                  )}
                </div>

                <div className="crm-kanban-column-body">
                  {stageLeads.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '24px 12px', color: '#475569', fontSize: '0.8rem' }}>
                      No deals in this stage
                    </div>
                  ) : (
                    stageLeads.map((lead) => (
                      <div key={lead.lead_id} className="crm-kanban-card">
                        <div
                          className="crm-kanban-card-title"
                          onClick={() => onSelectLead(lead.lead_id)}
                        >
                          {lead.title}
                        </div>

                        <div className="crm-kanban-card-customer">
                          <button
                            style={{
                              background: 'none',
                              border: 'none',
                              color: '#818cf8',
                              cursor: 'pointer',
                              padding: 0,
                              fontSize: '0.8rem',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px'
                            }}
                            onClick={() => onSelectCustomer(lead.customer_id)}
                          >
                            <User size={12} />
                            <span>{lead.customer_name || 'Customer'}</span>
                          </button>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px' }}>
                          <span className={`crm-badge crm-badge-priority-${lead.priority.toLowerCase()}`}>
                            {lead.priority}
                          </span>
                          {lead.expected_value ? (
                            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#10b981' }}>
                              ${Number(lead.expected_value).toLocaleString()}
                            </span>
                          ) : (
                            <span style={{ color: '#475569', fontSize: '0.75rem' }}>—</span>
                          )}
                        </div>

                        {/* Card Footer with Quick Move Buttons */}
                        <div className="crm-kanban-card-footer">
                          <div>
                            {lead.owner_name ? (
                              <span>{lead.owner_name}</span>
                            ) : (
                              <span>Unassigned</span>
                            )}
                          </div>
                          <div style={{ display: 'flex', gap: '4px' }}>
                            {prevStage && (
                              <button
                                className="crm-btn crm-btn-secondary"
                                style={{ padding: '2px 6px', fontSize: '0.7rem' }}
                                title={`Move to ${prevStage.name}`}
                                onClick={() => handleStageMove(lead, prevStage.stage_id)}
                                disabled={transitioningLeadId === lead.lead_id}
                              >
                                <ChevronLeft size={12} />
                              </button>
                            )}
                            {nextStage && (
                              <button
                                className="crm-btn crm-btn-secondary"
                                style={{ padding: '2px 6px', fontSize: '0.7rem' }}
                                title={`Move to ${nextStage.name}`}
                                onClick={() => handleStageMove(lead, nextStage.stage_id)}
                                disabled={transitioningLeadId === lead.lead_id}
                              >
                                <ChevronRight size={12} />
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
