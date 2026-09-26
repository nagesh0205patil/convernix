import React, { useState } from 'react'
import {
  Search,
  User,
  TrendingUp,
  Phone,
  Mail,
  ExternalLink,
  Tag as TagIcon
} from 'lucide-react'
import { crmApi } from '../services/crmApi'

interface CrmSearchViewProps {
  token: string
  onSelectCustomer: (customerId: string) => void
  onSelectLead: (leadId: string) => void
}

export const CrmSearchView: React.FC<CrmSearchViewProps> = ({
  token,
  onSelectCustomer,
  onSelectLead,
}) => {
  const [query, setQuery] = useState('')
  const [entityType, setEntityType] = useState('all')
  const [results, setResults] = useState<any>({ customers: [], leads: [] })
  const [searching, setSearching] = useState(false)
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    setSearching(true)
    setError(null)
    setSearched(true)
    try {
      const data = await crmApi.search(token, query.trim(), entityType)
      setResults(data)
    } catch (err: any) {
      setError(err.message || 'Search failed')
    } finally {
      setSearching(false)
    }
  }

  const customerList = results?.customers || []
  const leadList = results?.leads || []

  return (
    <div className="crm-container">
      <div className="crm-header">
        <div className="crm-header-title-group">
          <div className="crm-header-icon">
            <Search size={20} />
          </div>
          <div>
            <h1 className="crm-header-title">CRM Global Search</h1>
            <p className="crm-header-subtitle">
              Secure blind-index search across Customers, Leads, and WhatsApp contacts
            </p>
          </div>
        </div>
      </div>

      <div className="crm-content">
        <form onSubmit={handleSearch} className="crm-filter-bar">
          <div className="crm-search-box">
            <Search size={15} color="#64748b" />
            <input
              type="text"
              placeholder="Search by name, phone number, email, or lead title..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
            />
          </div>

          <select
            className="crm-filter-select"
            value={entityType}
            onChange={(e) => setEntityType(e.target.value)}
          >
            <option value="all">All Records</option>
            <option value="customer">Customers Only</option>
            <option value="lead">Leads Only</option>
          </select>

          <button type="submit" className="crm-btn crm-btn-primary" disabled={searching || !query.trim()}>
            {searching ? 'Searching...' : 'Search'}
          </button>
        </form>

        {error && (
          <div className="crm-alert-warning" style={{ marginBottom: '16px' }}>
            {error}
          </div>
        )}

        {searched && !searching && customerList.length === 0 && leadList.length === 0 && (
          <div style={{ textAlign: 'center', padding: '48px', color: '#64748b' }}>
            No records found matching "{query}".
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Customers Section */}
          {(entityType === 'all' || entityType === 'customer') && customerList.length > 0 && (
            <div>
              <h3 style={{ fontSize: '0.95rem', color: '#f8fafc', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <User size={16} color="#818cf8" />
                <span>Customers ({customerList.length})</span>
              </h3>
              <div className="crm-table-container">
                <table className="crm-table">
                  <thead>
                    <tr>
                      <th>Display Name</th>
                      <th>Phone</th>
                      <th>Email</th>
                      <th>Status</th>
                      <th>Source</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {customerList.map((c: any) => (
                      <tr key={c.customer_id}>
                        <td style={{ fontWeight: 600, color: '#f8fafc' }}>{c.display_name}</td>
                        <td style={{ fontFamily: 'monospace' }}>{c.phone_masked || '—'}</td>
                        <td style={{ fontFamily: 'monospace' }}>{c.email_masked || '—'}</td>
                        <td>
                          <span className="crm-badge crm-badge-stage">{c.status}</span>
                        </td>
                        <td>{c.source}</td>
                        <td>
                          <button
                            className="crm-btn crm-btn-secondary"
                            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                            onClick={() => onSelectCustomer(c.customer_id)}
                          >
                            Open 360
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Leads Section */}
          {(entityType === 'all' || entityType === 'lead') && leadList.length > 0 && (
            <div>
              <h3 style={{ fontSize: '0.95rem', color: '#f8fafc', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <TrendingUp size={16} color="#10b981" />
                <span>Leads ({leadList.length})</span>
              </h3>
              <div className="crm-table-container">
                <table className="crm-table">
                  <thead>
                    <tr>
                      <th>Title</th>
                      <th>Customer</th>
                      <th>Stage</th>
                      <th>Priority</th>
                      <th>Value</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leadList.map((l: any) => (
                      <tr key={l.lead_id}>
                        <td style={{ fontWeight: 600, color: '#f8fafc' }}>{l.title}</td>
                        <td>
                          <button
                            style={{ background: 'none', border: 'none', color: '#818cf8', cursor: 'pointer', padding: 0 }}
                            onClick={() => onSelectCustomer(l.customer_id)}
                          >
                            {l.customer_name || 'Customer'}
                          </button>
                        </td>
                        <td>
                          <span className="crm-badge crm-badge-stage">{l.stage_name || l.status}</span>
                        </td>
                        <td>
                          <span className={`crm-badge crm-badge-priority-${l.priority.toLowerCase()}`}>
                            {l.priority}
                          </span>
                        </td>
                        <td style={{ color: '#10b981', fontWeight: 600 }}>
                          {l.expected_value ? `$${Number(l.expected_value).toLocaleString()}` : '—'}
                        </td>
                        <td>
                          <button
                            className="crm-btn crm-btn-secondary"
                            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                            onClick={() => onSelectLead(l.lead_id)}
                          >
                            View Lead
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
