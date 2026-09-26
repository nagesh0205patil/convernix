import React, { useState } from 'react';
import type { AuditLogEntry } from '../../types';
import { StatusBadge } from '../common/StatusBadge';
import { FilterBar } from '../common/FilterBar';
import { DataTable } from '../common/DataTable';
import { ShieldCheck, Download, Search, Info, Eye, X, Terminal } from 'lucide-react';
import { adminApi } from '../../services/adminApi';

interface AuditLogsViewProps {
  logs: AuditLogEntry[];
}

export function AuditLogsView({ logs }: AuditLogsViewProps) {
  const [search, setSearch] = useState('');
  const [moduleFilter, setModuleFilter] = useState('all');
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null);
  const [isExporting, setIsExporting] = useState(false);

  const filteredLogs = logs.filter((entry) => {
    const matchesSearch =
      entry.actor_name.toLowerCase().includes(search.toLowerCase()) ||
      entry.action.toLowerCase().includes(search.toLowerCase()) ||
      entry.resource.toLowerCase().includes(search.toLowerCase()) ||
      entry.ip_address.includes(search);
    const matchesModule = moduleFilter === 'all' || entry.module.toLowerCase() === moduleFilter.toLowerCase();
    return matchesSearch && matchesModule;
  });

  const handleExportCSV = async () => {
    setIsExporting(true);
    try {
      await adminApi.exportAuditLogsCsv();
    } catch {
      // Fallback to client-side CSV generation
      const headers = ['Timestamp', 'Actor', 'Action', 'Module', 'Resource', 'IP Address', 'Status'];
      const rows = filteredLogs.map((l) => [
        `"${l.created_at}"`,
        `"${l.actor_name}"`,
        `"${l.action}"`,
        `"${l.module}"`,
        `"${l.resource}"`,
        `"${l.ip_address}"`,
        `"${l.status}"`,
      ]);
      const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', `audit-logs-${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } finally {
      setIsExporting(false);
    }
  };

  const columns = [
    {
      key: 'created_at',
      header: 'Timestamp',
      render: (entry: AuditLogEntry) => (
        <span style={{ fontSize: '12px', color: 'var(--pm-text-muted)', fontFamily: 'monospace' }}>
          {entry.created_at}
        </span>
      ),
    },
    {
      key: 'actor_name',
      header: 'Actor',
      render: (entry: AuditLogEntry) => (
        <div>
          <div style={{ fontWeight: 600, color: 'var(--pm-text)' }}>{entry.actor_name}</div>
          {entry.actor_email && (
            <div style={{ fontSize: '11px', color: 'var(--pm-text-muted)' }}>{entry.actor_email}</div>
          )}
        </div>
      ),
    },
    {
      key: 'action',
      header: 'Action',
      render: (entry: AuditLogEntry) => (
        <span style={{ fontWeight: 500, color: 'var(--pm-text)' }}>{entry.action}</span>
      ),
    },
    {
      key: 'module',
      header: 'Module',
      render: (entry: AuditLogEntry) => (
        <span
          style={{
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: 600,
            background: 'var(--pm-bg-subtle)',
            color: 'var(--pm-text-muted)',
            border: '1px solid var(--pm-border)',
          }}
        >
          {entry.module}
        </span>
      ),
    },
    {
      key: 'resource',
      header: 'Target / Resource',
      render: (entry: AuditLogEntry) => (
        <span style={{ fontSize: '13px', color: 'var(--pm-text)' }}>{entry.resource}</span>
      ),
    },
    {
      key: 'ip_address',
      header: 'IP Address',
      render: (entry: AuditLogEntry) => (
        <span style={{ fontSize: '12px', fontFamily: 'monospace', color: 'var(--pm-text-muted)' }}>
          {entry.ip_address}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (entry: AuditLogEntry) => <StatusBadge status={entry.status} />,
    },
    {
      key: 'details',
      header: '',
      align: 'right' as const,
      render: (entry: AuditLogEntry) => (
        <button
          type="button"
          className="pm-btn-secondary"
          style={{ padding: '3px 8px', fontSize: '11px' }}
          onClick={() => setSelectedLog(entry)}
          aria-label={`View audit entry ${entry.id}`}
        >
          <Eye size={12} style={{ marginRight: '4px' }} /> Inspect
        </button>
      ),
    },
  ];

  return (
    <div className="pm-view-container">
      {/* Immutability compliance banner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '12px 16px',
          background: 'rgba(59, 130, 246, 0.08)',
          border: '1px solid rgba(59, 130, 246, 0.25)',
          borderRadius: '6px',
          marginBottom: '20px',
        }}
      >
        <ShieldCheck size={20} style={{ color: '#3b82f6', flexShrink: 0 }} />
        <div style={{ fontSize: '13px', color: 'var(--pm-text)', flex: 1 }}>
          <strong>Forensic Immutable Record:</strong> All administrative modifications, authentication attempts,
          and credential exposures are cryptographically serialized and retained for 365 days. Records cannot be altered
          or purged by tenant administrators.
        </div>
      </div>

      <div className="pm-card">
        <div className="pm-card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 className="pm-card-title">Security & Organization Audit Trail</h3>
            <p className="pm-card-desc">
              Chronological ledger of security configurations, user permissions, billing events, and integration updates.
            </p>
          </div>
          <button
            type="button"
            className="pm-btn-secondary"
            onClick={handleExportCSV}
            disabled={isExporting}
          >
            <Download size={14} style={{ marginRight: '6px' }} />
            {isExporting ? 'Exporting...' : 'Export CSV'}
          </button>
        </div>

        <FilterBar
          searchQuery={search}
          onSearchChange={setSearch}
          searchPlaceholder="Filter by actor, action, resource, or IP..."
          statusFilter={moduleFilter}
          onStatusChange={setModuleFilter}
          statusOptions={[
            { value: 'all', label: 'All Modules' },
            { value: 'IAM', label: 'IAM' },
            { value: 'Settings', label: 'Settings' },
            { value: 'Account', label: 'Account' },
            { value: 'Security', label: 'Security' },
            { value: 'WhatsApp', label: 'WhatsApp' },
          ]}
        />

        <DataTable
          columns={columns}
          data={filteredLogs}
          emptyMessage="No audit log entries found matching your search criteria."
        />
      </div>

      {/* Audit Log Inspection Modal */}
      {selectedLog && (
        <div className="pm-modal-backdrop" onClick={() => setSelectedLog(null)}>
          <div
            className="pm-modal-content"
            style={{ maxWidth: '580px', width: '100%' }}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="audit-modal-title"
          >
            <div className="pm-modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Terminal size={18} style={{ color: 'var(--pm-primary)' }} />
                <h3 id="audit-modal-title" style={{ margin: 0, fontSize: '16px', color: 'var(--pm-text)' }}>
                  Audit Event #{selectedLog.id}
                </h3>
              </div>
              <button
                type="button"
                className="pm-icon-btn"
                onClick={() => setSelectedLog(null)}
                aria-label="Close audit inspect"
              >
                <X size={18} />
              </button>
            </div>

            <div className="pm-modal-body" style={{ padding: '20px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', rowGap: '12px', fontSize: '13px' }}>
                <span style={{ color: 'var(--pm-text-muted)' }}>Action:</span>
                <strong style={{ color: 'var(--pm-text)' }}>{selectedLog.action}</strong>

                <span style={{ color: 'var(--pm-text-muted)' }}>Module:</span>
                <span>{selectedLog.module}</span>

                <span style={{ color: 'var(--pm-text-muted)' }}>Actor:</span>
                <div>
                  <div>{selectedLog.actor_name}</div>
                  {selectedLog.actor_email && (
                    <div style={{ fontSize: '12px', color: 'var(--pm-text-muted)' }}>{selectedLog.actor_email}</div>
                  )}
                </div>

                <span style={{ color: 'var(--pm-text-muted)' }}>Resource:</span>
                <code style={{ background: 'var(--pm-bg-subtle)', padding: '2px 6px', borderRadius: '4px' }}>
                  {selectedLog.resource}
                </code>

                <span style={{ color: 'var(--pm-text-muted)' }}>IP Address:</span>
                <code>{selectedLog.ip_address}</code>

                <span style={{ color: 'var(--pm-text-muted)' }}>Status:</span>
                <div>
                  <StatusBadge status={selectedLog.status} />
                </div>

                <span style={{ color: 'var(--pm-text-muted)' }}>Recorded At:</span>
                <span>{selectedLog.created_at}</span>
              </div>

              {selectedLog.metadata && Object.keys(selectedLog.metadata).length > 0 && (
                <div style={{ marginTop: '20px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--pm-text-muted)', marginBottom: '8px' }}>
                    EVENT PAYLOAD & CONTEXT
                  </div>
                  <pre
                    style={{
                      background: 'var(--pm-bg-subtle)',
                      padding: '12px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontFamily: 'monospace',
                      overflowX: 'auto',
                      border: '1px solid var(--pm-border)',
                      margin: 0,
                    }}
                  >
                    {JSON.stringify(selectedLog.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="pm-modal-footer" style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="pm-btn-primary"
                onClick={() => setSelectedLog(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

