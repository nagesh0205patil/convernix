import React, { useState, useEffect, useCallback } from 'react'
import {
  Workflow,
  Plus,
  RefreshCw,
  AlertTriangle,
  Layers,
  CheckCircle,
  XCircle,
  Flag
} from 'lucide-react'
import { crmApi } from '../services/crmApi'

interface CrmPipelinesViewProps {
  token: string
}

export const CrmPipelinesView: React.FC<CrmPipelinesViewProps> = ({ token }) => {
  const [pipelines, setPipelines] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Pipeline modal
  const [showPipeModal, setShowPipeModal] = useState(false)
  const [pipeName, setPipeName] = useState('')
  const [pipeDesc, setPipeDesc] = useState('')
  const [savingPipe, setSavingPipe] = useState(false)

  // Stage modal
  const [showStageModal, setShowStageModal] = useState(false)
  const [stagePipelineId, setStagePipelineId] = useState('')
  const [stageName, setStageName] = useState('')
  const [stageClassification, setStageClassification] = useState('OPEN')
  const [isTerminal, setIsTerminal] = useState(false)
  const [stageSaving, setStageSaving] = useState(false)

  const loadPipelines = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await crmApi.getPipelines(token)
      const list = Array.isArray(data) ? data : data?.results || []
      setPipelines(list)
    } catch (err: any) {
      setError(err.message || 'Failed to load pipelines')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    loadPipelines()
  }, [loadPipelines])

  const handleCreatePipeline = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!pipeName.trim()) return
    setSavingPipe(true)
    try {
      await crmApi.createPipeline(token, {
        name: pipeName.trim(),
        description: pipeDesc.trim() || undefined,
      })
      setShowPipeModal(false)
      setPipeName('')
      setPipeDesc('')
      loadPipelines()
    } catch (err: any) {
      setError(`Failed to create pipeline: ${err.message}`)
    } finally {
      setSavingPipe(false)
    }
  }

  const handleCreateStage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!stageName.trim() || !stagePipelineId) return
    setStageSaving(true)
    try {
      const pipe = pipelines.find((p) => p.pipeline_id === stagePipelineId)
      const nextOrder = (pipe?.stages?.length || 0) + 1
      await crmApi.createPipelineStage(token, stagePipelineId, {
        name: stageName.trim(),
        display_order: nextOrder,
        classification: stageClassification,
        is_terminal: isTerminal,
      })
      setShowStageModal(false)
      setStageName('')
      setStageClassification('OPEN')
      setIsTerminal(false)
      loadPipelines()
    } catch (err: any) {
      setError(`Failed to add stage: ${err.message}`)
    } finally {
      setStageSaving(false)
    }
  }

  return (
    <div className="crm-container">
      <div className="crm-header">
        <div className="crm-header-title-group">
          <div className="crm-header-icon">
            <Workflow size={20} />
          </div>
          <div>
            <h1 className="crm-header-title">Pipelines & Stages</h1>
            <p className="crm-header-subtitle">
              Configure tenant sales workflows, stage progression sequences, and win/loss rules
            </p>
          </div>
        </div>

        <div className="crm-header-actions">
          <button className="crm-btn crm-btn-secondary" onClick={loadPipelines} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
          <button className="crm-btn crm-btn-primary" onClick={() => setShowPipeModal(true)}>
            <Plus size={14} />
            <span>New Pipeline</span>
          </button>
        </div>
      </div>

      <div className="crm-content">
        {error && (
          <div className="crm-alert-warning" style={{ marginBottom: '16px' }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {pipelines.map((pipe) => (
            <div
              key={pipe.pipeline_id}
              style={{
                background: '#141722',
                border: '1px solid #232738',
                borderRadius: '10px',
                padding: '20px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.05rem', color: '#f8fafc', fontWeight: 600 }}>
                    {pipe.name} {pipe.is_default && <span className="crm-badge crm-badge-stage" style={{ marginLeft: '8px' }}>Default</span>}
                  </h3>
                  {pipe.description && (
                    <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: '#94a3b8' }}>
                      {pipe.description}
                    </p>
                  )}
                </div>

                <button
                  className="crm-btn crm-btn-secondary"
                  onClick={() => {
                    setStagePipelineId(pipe.pipeline_id)
                    setShowStageModal(true)
                  }}
                >
                  <Plus size={13} />
                  <span>Add Stage</span>
                </button>
              </div>

              {/* Stages List */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
                {(pipe.stages || []).map((stage: any, sIdx: number) => (
                  <div
                    key={stage.stage_id}
                    style={{
                      background: '#0d0f17',
                      border: '1px solid #232738',
                      borderRadius: '8px',
                      padding: '12px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>
                        STEP {sIdx + 1}
                      </span>
                      <span
                        className="crm-badge"
                        style={{
                          background:
                            stage.classification === 'WON'
                              ? 'rgba(16, 185, 129, 0.2)'
                              : stage.classification === 'LOST'
                              ? 'rgba(239, 68, 68, 0.2)'
                              : '#1e2438',
                          color:
                            stage.classification === 'WON'
                              ? '#34d399'
                              : stage.classification === 'LOST'
                              ? '#f87171'
                              : '#94a3b8',
                        }}
                      >
                        {stage.classification}
                      </span>
                    </div>

                    <div style={{ fontWeight: 600, color: '#f1f5f9', fontSize: '0.9rem' }}>
                      {stage.name}
                    </div>

                    {stage.is_terminal && (
                      <div style={{ fontSize: '0.72rem', color: '#fbbf24', marginTop: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Flag size={11} />
                        <span>Terminal State</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* New Pipeline Modal */}
      {showPipeModal && (
        <div className="crm-modal-backdrop" onClick={() => setShowPipeModal(false)}>
          <div className="crm-modal" onClick={(e) => e.stopPropagation()}>
            <div className="crm-modal-header">
              <h2 className="crm-modal-title">Create Sales Pipeline</h2>
              <button
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
                onClick={() => setShowPipeModal(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreatePipeline}>
              <div className="crm-modal-body">
                <div className="crm-form-group">
                  <label>Pipeline Name *</label>
                  <input
                    type="text"
                    className="crm-form-control"
                    placeholder="e.g. Enterprise Sales Pipeline"
                    value={pipeName}
                    onChange={(e) => setPipeName(e.target.value)}
                    required
                  />
                </div>

                <div className="crm-form-group">
                  <label>Description</label>
                  <textarea
                    className="crm-form-control"
                    rows={3}
                    placeholder="Workflow details..."
                    value={pipeDesc}
                    onChange={(e) => setPipeDesc(e.target.value)}
                  />
                </div>
              </div>

              <div className="crm-modal-footer">
                <button
                  type="button"
                  className="crm-btn crm-btn-secondary"
                  onClick={() => setShowPipeModal(false)}
                  disabled={savingPipe}
                >
                  Cancel
                </button>
                <button type="submit" className="crm-btn crm-btn-primary" disabled={savingPipe}>
                  {savingPipe ? 'Creating...' : 'Create Pipeline'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* New Stage Modal */}
      {showStageModal && (
        <div className="crm-modal-backdrop" onClick={() => setShowStageModal(false)}>
          <div className="crm-modal" onClick={(e) => e.stopPropagation()}>
            <div className="crm-modal-header">
              <h2 className="crm-modal-title">Add Stage to Pipeline</h2>
              <button
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
                onClick={() => setShowStageModal(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateStage}>
              <div className="crm-modal-body">
                <div className="crm-form-group">
                  <label>Stage Name *</label>
                  <input
                    type="text"
                    className="crm-form-control"
                    placeholder="e.g. Contract Review"
                    value={stageName}
                    onChange={(e) => setStageName(e.target.value)}
                    required
                  />
                </div>

                <div className="crm-form-group">
                  <label>Stage Classification</label>
                  <select
                    className="crm-form-control"
                    value={stageClassification}
                    onChange={(e) => setStageClassification(e.target.value)}
                  >
                    <option value="OPEN">Open (In Progress)</option>
                    <option value="WON">Won (Success Closure)</option>
                    <option value="LOST">Lost (Opportunity Lost)</option>
                  </select>
                </div>

                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', cursor: 'pointer', color: '#cbd5e1' }}>
                  <input
                    type="checkbox"
                    checked={isTerminal}
                    onChange={(e) => setIsTerminal(e.target.checked)}
                  />
                  <span>Terminal State (Cannot move further once reached)</span>
                </label>
              </div>

              <div className="crm-modal-footer">
                <button
                  type="button"
                  className="crm-btn crm-btn-secondary"
                  onClick={() => setShowStageModal(false)}
                  disabled={stageSaving}
                >
                  Cancel
                </button>
                <button type="submit" className="crm-btn crm-btn-primary" disabled={stageSaving}>
                  {stageSaving ? 'Adding...' : 'Add Stage'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
