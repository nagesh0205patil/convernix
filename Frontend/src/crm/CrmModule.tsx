import React, { useState, useEffect } from 'react'
import {
  TrendingUp,
  Kanban,
  UserCheck,
  Search,
  Tag,
  Sliders,
  Workflow,
  Settings
} from 'lucide-react'
import './crm.css'

import { LeadListView } from './components/LeadListView'
import { LeadDetailView } from './components/LeadDetailView'
import { Customer360View } from './components/Customer360View'
import { PipelineKanbanView } from './components/PipelineKanbanView'
import { CrmSearchView } from './components/CrmSearchView'
import { CrmTagsView } from './components/CrmTagsView'
import { CrmCustomFieldsView } from './components/CrmCustomFieldsView'
import { CrmPipelinesView } from './components/CrmPipelinesView'
import { CrmSettingsView } from './components/CrmSettingsView'

export type CrmSubView =
  | 'leads'
  | 'lead-detail'
  | 'customer-360'
  | 'pipeline'
  | 'search'
  | 'tags'
  | 'custom-fields'
  | 'pipelines'
  | 'settings'

interface CrmModuleProps {
  token: string
  initialSubView?: CrmSubView
  initialLeadId?: string
  initialCustomerId?: string
  onBackToInbox?: () => void
}

export const CrmModule: React.FC<CrmModuleProps> = ({
  token,
  initialSubView = 'leads',
  initialLeadId,
  initialCustomerId,
}) => {
  const [currentView, setCurrentView] = useState<CrmSubView>(initialSubView)
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(initialLeadId || null)
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(initialCustomerId || null)

  // Listen to hash changes if present
  useEffect(() => {
    const handleHash = () => {
      const hash = window.location.hash.replace(/^#\/?/, '')
      if (hash.startsWith('leads/')) {
        const id = hash.replace('leads/', '')
        setSelectedLeadId(id)
        setCurrentView('lead-detail')
      } else if (hash.startsWith('customers/')) {
        const id = hash.replace('customers/', '')
        setSelectedCustomerId(id)
        setCurrentView('customer-360')
      } else if (['leads', 'pipeline', 'crm/search', 'crm/tags', 'crm/custom-fields', 'crm/pipelines', 'crm/settings'].includes(hash)) {
        if (hash === 'pipeline') setCurrentView('pipeline')
        else if (hash === 'crm/search') setCurrentView('search')
        else if (hash === 'crm/tags') setCurrentView('tags')
        else if (hash === 'crm/custom-fields') setCurrentView('custom-fields')
        else if (hash === 'crm/pipelines') setCurrentView('pipelines')
        else if (hash === 'crm/settings') setCurrentView('settings')
        else setCurrentView('leads')
      }
    }
    handleHash()
    window.addEventListener('hashchange', handleHash)
    return () => window.removeEventListener('hashchange', handleHash)
  }, [])

  const navigateToLead = (leadId: string) => {
    setSelectedLeadId(leadId)
    setCurrentView('lead-detail')
    window.location.hash = `leads/${leadId}`
  }

  const navigateToCustomer = (customerId: string) => {
    setSelectedCustomerId(customerId)
    setCurrentView('customer-360')
    window.location.hash = `customers/${customerId}`
  }

  const setView = (view: CrmSubView) => {
    setCurrentView(view)
    if (view === 'leads') window.location.hash = 'leads'
    else if (view === 'pipeline') window.location.hash = 'pipeline'
    else if (view === 'search') window.location.hash = 'crm/search'
    else if (view === 'tags') window.location.hash = 'crm/tags'
    else if (view === 'custom-fields') window.location.hash = 'crm/custom-fields'
    else if (view === 'pipelines') window.location.hash = 'crm/pipelines'
    else if (view === 'settings') window.location.hash = 'crm/settings'
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%' }}>
      {/* CRM Global Navigation Header Bar */}
      <div className="crm-subnav">
        <button
          className={`crm-subnav-btn ${currentView === 'leads' ? 'active' : ''}`}
          onClick={() => setView('leads')}
        >
          <TrendingUp size={14} />
          <span>Leads</span>
        </button>

        <button
          className={`crm-subnav-btn ${currentView === 'pipeline' ? 'active' : ''}`}
          onClick={() => setView('pipeline')}
        >
          <Kanban size={14} />
          <span>Pipeline</span>
        </button>

        <button
          className={`crm-subnav-btn ${currentView === 'search' ? 'active' : ''}`}
          onClick={() => setView('search')}
        >
          <Search size={14} />
          <span>CRM Search</span>
        </button>

        <button
          className={`crm-subnav-btn ${currentView === 'pipelines' ? 'active' : ''}`}
          onClick={() => setView('pipelines')}
        >
          <Workflow size={14} />
          <span>Workflows</span>
        </button>

        <button
          className={`crm-subnav-btn ${currentView === 'custom-fields' ? 'active' : ''}`}
          onClick={() => setView('custom-fields')}
        >
          <Sliders size={14} />
          <span>Custom Fields</span>
        </button>

        <button
          className={`crm-subnav-btn ${currentView === 'tags' ? 'active' : ''}`}
          onClick={() => setView('tags')}
        >
          <Tag size={14} />
          <span>Tags</span>
        </button>

        <button
          className={`crm-subnav-btn ${currentView === 'settings' ? 'active' : ''}`}
          onClick={() => setView('settings')}
        >
          <Settings size={14} />
          <span>Settings</span>
        </button>
      </div>

      {/* Render Subview */}
      <div style={{ flex: 1, minHeight: 0 }}>
        {currentView === 'leads' && (
          <LeadListView
            token={token}
            onSelectLead={navigateToLead}
            onSelectCustomer={navigateToCustomer}
          />
        )}

        {currentView === 'lead-detail' && selectedLeadId && (
          <LeadDetailView
            token={token}
            leadId={selectedLeadId}
            onBack={() => setView('leads')}
            onSelectCustomer={navigateToCustomer}
          />
        )}

        {currentView === 'customer-360' && selectedCustomerId && (
          <Customer360View
            token={token}
            customerId={selectedCustomerId}
            onBack={() => setView('leads')}
            onSelectLead={navigateToLead}
          />
        )}

        {currentView === 'pipeline' && (
          <PipelineKanbanView
            token={token}
            onSelectLead={navigateToLead}
            onSelectCustomer={navigateToCustomer}
          />
        )}

        {currentView === 'search' && (
          <CrmSearchView
            token={token}
            onSelectCustomer={navigateToCustomer}
            onSelectLead={navigateToLead}
          />
        )}

        {currentView === 'tags' && <CrmTagsView token={token} />}

        {currentView === 'custom-fields' && <CrmCustomFieldsView token={token} />}

        {currentView === 'pipelines' && <CrmPipelinesView token={token} />}

        {currentView === 'settings' && <CrmSettingsView token={token} />}
      </div>
    </div>
  )
}

export default CrmModule
