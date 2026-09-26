import React, { useEffect, useState } from 'react';
import {
  FileText,
  Plus,
  RefreshCw,
  Search,
  CheckCircle,
  Clock,
  RotateCcw,
  Sparkles,
  Send,
  Eye,
  AlertTriangle,
  ChevronRight,
  History,
  X,
} from 'lucide-react';
import { adminApi } from '../../services/adminApi';
import type { NotificationTemplateInfo, NotificationTemplateVersionInfo } from '../../types';

interface NotificationTemplatesViewProps {
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export function NotificationTemplatesView({ toast }: NotificationTemplatesViewProps) {
  const [templates, setTemplates] = useState<NotificationTemplateInfo[]>([]);
  const [allowedVariables, setAllowedVariables] = useState<{ variable: string; description: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<NotificationTemplateInfo | null>(null);
  const [versions, setVersions] = useState<NotificationTemplateVersionInfo[]>([]);

  // Create / Edit modal state
  const [showModal, setShowModal] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<NotificationTemplateInfo | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    event_type: 'lead.created',
    channel: 'WHATSAPP',
    content: 'Hello {{lead.name}}, thank you for contacting {{organization.name}}. An agent from {{department.name}} will assist you shortly.',
    change_summary: '',
  });

  // Live preview state
  const [previewRendered, setPreviewRendered] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const res = await adminApi.getTemplates();
      setTemplates(res.templates || []);
      setAllowedVariables(res.allowed_variables || []);
    } catch (err: any) {
      toast(err.message || 'Failed to load notification templates.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const handleOpenCreate = () => {
    setEditingTemplate(null);
    setFormData({
      name: '',
      event_type: 'lead.created',
      channel: 'WHATSAPP',
      content: 'Hello {{lead.name}}, welcome to {{organization.name}}! Our {{department.name}} team is ready to assist you.',
      change_summary: '',
    });
    setShowModal(true);
    updatePreview('Hello {{lead.name}}, welcome to {{organization.name}}! Our {{department.name}} team is ready to assist you.');
  };

  const handleOpenEdit = async (tmpl: NotificationTemplateInfo) => {
    setEditingTemplate(tmpl);
    try {
      const detail = await adminApi.getTemplate(tmpl.id);
      setSelectedTemplate(detail.template);
      setVersions(detail.versions || []);
      const currentContent = detail.versions?.[0]?.content || '';
      setFormData({
        name: tmpl.name,
        event_type: tmpl.event_type,
        channel: tmpl.channel,
        content: currentContent,
        change_summary: '',
      });
      setShowModal(true);
      updatePreview(currentContent, tmpl.id);
    } catch (err: any) {
      toast(err.message || 'Failed to fetch template detail', 'error');
    }
  };

  const handleViewHistory = async (tmpl: NotificationTemplateInfo) => {
    try {
      const detail = await adminApi.getTemplate(tmpl.id);
      setSelectedTemplate(detail.template);
      setVersions(detail.versions || []);
    } catch (err: any) {
      toast(err.message || 'Failed to load version history.', 'error');
    }
  };

  const updatePreview = async (content: string, id?: number) => {
    if (!content) {
      setPreviewRendered('');
      return;
    }
    setPreviewLoading(true);
    try {
      const res = await adminApi.previewTemplate(content, undefined, id);
      setPreviewRendered(res.rendered);
    } catch (err) {
      // Fallback local substitution
      setPreviewRendered(content.replace(/\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}/g, '[$1]'));
    } finally {
      setPreviewLoading(false);
    }
  };

  const insertVariable = (variable: string) => {
    const placeholder = `{{${variable}}}`;
    const newContent = formData.content + (formData.content.endsWith(' ') || !formData.content ? '' : ' ') + placeholder;
    setFormData((prev) => ({ ...prev, content: newContent }));
    updatePreview(newContent, editingTemplate?.id);
  };

  const handleSaveDraft = async () => {
    if (!formData.name.trim() || !formData.content.trim()) {
      toast('Template name and content are required.', 'error');
      return;
    }

    try {
      if (editingTemplate) {
        await adminApi.updateTemplate(editingTemplate.id, {
          name: formData.name,
          event_type: formData.event_type,
          channel: formData.channel,
          content: formData.content,
          change_summary: formData.change_summary || 'Draft update',
        });
        toast('Draft saved successfully.', 'success');
      } else {
        await adminApi.createTemplate({
          name: formData.name,
          event_type: formData.event_type,
          channel: formData.channel,
          content: formData.content,
        });
        toast('New template created as draft.', 'success');
      }
      setShowModal(false);
      fetchTemplates();
    } catch (err: any) {
      toast(err.message || 'Failed to save template.', 'error');
    }
  };

  const handlePublish = async () => {
    if (!formData.name.trim() || !formData.content.trim()) {
      toast('Template name and content are required.', 'error');
      return;
    }

    try {
      let tmplId = editingTemplate?.id;
      if (!tmplId) {
        const created = await adminApi.createTemplate({
          name: formData.name,
          event_type: formData.event_type,
          channel: formData.channel,
          content: formData.content,
        });
        tmplId = created.id;
      }
      await adminApi.publishTemplate(tmplId, {
        content: formData.content,
        change_summary: formData.change_summary || 'Published active version',
      });
      toast('Template published and activated.', 'success');
      setShowModal(false);
      fetchTemplates();
    } catch (err: any) {
      toast(err.message || 'Failed to publish template.', 'error');
    }
  };

  const handleRollback = async (tmplId: number, targetVer: number) => {
    if (!confirm(`Are you sure you want to rollback to Version ${targetVer}?`)) return;
    try {
      await adminApi.rollbackTemplate(tmplId, targetVer);
      toast(`Rolled back to v${targetVer} successfully.`, 'success');
      fetchTemplates();
      if (selectedTemplate?.id === tmplId) {
        const detail = await adminApi.getTemplate(tmplId);
        setSelectedTemplate(detail.template);
        setVersions(detail.versions || []);
      }
    } catch (err: any) {
      toast(err.message || 'Rollback failed.', 'error');
    }
  };

  const filteredTemplates = templates.filter(
    (t) =>
      t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.event_type.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="pm-settings-panel">
      {/* Header */}
      <div className="pm-panel-header-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-primary, #fff)' }}>
            Notification Templates
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '0.85rem', color: 'var(--text-secondary, #94a3b8)' }}>
            Isolated tenant-specific WhatsApp notification templates with version control, rollback safety, and sandboxed preview.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            type="button"
            className="pm-btn pm-btn-outline"
            onClick={fetchTemplates}
            title="Refresh templates"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
          <button
            type="button"
            className="pm-btn pm-btn-primary"
            onClick={handleOpenCreate}
          >
            <Plus size={15} />
            <span>Create Template</span>
          </button>
        </div>
      </div>

      {/* Search and Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 18 }}>
        <div className="pm-search-input-wrap" style={{ flex: 1, position: 'relative' }}>
          <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#64748b' }} />
          <input
            type="text"
            className="pm-input"
            style={{ paddingLeft: 36, width: '100%' }}
            placeholder="Search templates by name or event trigger (e.g. lead.created)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Template Table */}
      <div className="pm-table-container">
        <table className="pm-table">
          <thead>
            <tr>
              <th>Template Name</th>
              <th>Trigger Event</th>
              <th>Channel</th>
              <th>Active Version</th>
              <th>Status</th>
              <th>Last Updated</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '36px 0', color: '#94a3b8' }}>
                  Loading notification templates...
                </td>
              </tr>
            ) : filteredTemplates.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '36px 0', color: '#94a3b8' }}>
                  No notification templates found. Click "Create Template" to configure your first automated message.
                </td>
              </tr>
            ) : (
              filteredTemplates.map((t) => (
                <tr key={t.id}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <FileText size={16} style={{ color: '#38bdf8' }} />
                      <span style={{ fontWeight: 600, color: 'var(--text-primary, #fff)' }}>{t.name}</span>
                    </div>
                  </td>
                  <td>
                    <code style={{ fontSize: '0.8rem', background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: 4 }}>
                      {t.event_type}
                    </code>
                  </td>
                  <td>
                    <span style={{ fontSize: '0.8rem', color: '#52bb89', fontWeight: 500 }}>WhatsApp</span>
                  </td>
                  <td>
                    <span style={{ fontSize: '0.82rem', fontWeight: 600 }}>v{t.current_version}</span>
                  </td>
                  <td>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        padding: '2px 8px',
                        borderRadius: 12,
                        textTransform: 'uppercase',
                        background: t.status === 'published' ? 'rgba(82, 187, 137, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                        color: t.status === 'published' ? '#52bb89' : '#f59e0b',
                      }}
                    >
                      {t.status}
                    </span>
                  </td>
                  <td style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                    {new Date(t.updated_at).toLocaleDateString()}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', gap: 6 }}>
                      <button
                        type="button"
                        className="pm-btn pm-btn-sm pm-btn-outline"
                        onClick={() => handleOpenEdit(t)}
                        title="Edit & Preview"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="pm-btn pm-btn-sm pm-btn-outline"
                        onClick={() => handleViewHistory(t)}
                        title="Version History & Rollback"
                      >
                        <History size={13} />
                        <span>History</span>
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Version History Drawer / Modal */}
      {selectedTemplate && (
        <div className="pm-modal-overlay" onClick={() => setSelectedTemplate(null)}>
          <div className="pm-modal" style={{ maxWidth: 640 }} onClick={(e) => e.stopPropagation()}>
            <div className="pm-modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <History size={18} style={{ color: '#38bdf8' }} />
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>
                  Version History: {selectedTemplate.name}
                </h3>
              </div>
              <button
                type="button"
                className="pm-modal-close"
                onClick={() => setSelectedTemplate(null)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="pm-modal-body" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
              <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: 0 }}>
                Every published iteration is permanently immutable. You can safely rollback to any previous version at any time.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {versions.map((ver) => {
                  const isCurrent = ver.version === selectedTemplate.current_version;
                  return (
                    <div
                      key={ver.id}
                      style={{
                        padding: 12,
                        borderRadius: 8,
                        background: isCurrent ? 'rgba(56, 189, 248, 0.08)' : 'rgba(255,255,255,0.03)',
                        border: isCurrent ? '1px solid rgba(56, 189, 248, 0.4)' : '1px solid rgba(255,255,255,0.06)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontWeight: 700, fontSize: '0.9rem', color: isCurrent ? '#38bdf8' : '#fff' }}>
                            Version {ver.version}
                          </span>
                          {isCurrent && (
                            <span style={{ fontSize: '0.7rem', background: '#38bdf8', color: '#0f172a', fontWeight: 700, padding: '1px 6px', borderRadius: 4 }}>
                              ACTIVE
                            </span>
                          )}
                        </div>
                        <span style={{ fontSize: '0.78rem', color: '#64748b' }}>
                          {new Date(ver.published_at).toLocaleString()}
                        </span>
                      </div>
                      <p style={{ margin: '4px 0 8px', fontSize: '0.82rem', color: '#cbd5e1', fontStyle: 'italic' }}>
                        {ver.change_summary || 'No change description provided'}
                      </p>
                      <div style={{ background: 'rgba(0,0,0,0.3)', padding: 8, borderRadius: 4, fontSize: '0.8rem', color: '#94a3b8', whiteSpace: 'pre-wrap' }}>
                        {ver.content}
                      </div>
                      {!isCurrent && (
                        <div style={{ marginTop: 8, textAlign: 'right' }}>
                          <button
                            type="button"
                            className="pm-btn pm-btn-sm pm-btn-outline"
                            onClick={() => handleRollback(selectedTemplate.id, ver.version)}
                          >
                            <RotateCcw size={12} />
                            <span>Rollback to v{ver.version}</span>
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="pm-modal-footer">
              <button
                type="button"
                className="pm-btn pm-btn-outline"
                onClick={() => setSelectedTemplate(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create / Edit Template Modal with Live Sandboxed WhatsApp Preview */}
      {showModal && (
        <div className="pm-modal-overlay" onClick={() => setShowModal(false)}>
          <div
            className="pm-modal"
            style={{ maxWidth: 900, width: '95%' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="pm-modal-header">
              <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 600 }}>
                {editingTemplate ? `Edit Template: ${editingTemplate.name}` : 'Create Notification Template'}
              </h3>
              <button
                type="button"
                className="pm-modal-close"
                onClick={() => setShowModal(false)}
              >
                <X size={18} />
              </button>
            </div>

            <div className="pm-modal-body" style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 24 }}>
              {/* Form Controls */}
              <div>
                <div className="pm-form-group" style={{ marginBottom: 14 }}>
                  <label className="pm-form-label">Template Name</label>
                  <input
                    type="text"
                    className="pm-input"
                    placeholder="e.g. Lead Welcome Notification"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
                  <div className="pm-form-group">
                    <label className="pm-form-label">Trigger Event</label>
                    <select
                      className="pm-input"
                      value={formData.event_type}
                      onChange={(e) => setFormData({ ...formData, event_type: e.target.value })}
                    >
                      <option value="lead.created">lead.created (New Enquiry)</option>
                      <option value="conversation.assigned">conversation.assigned (Agent Assigned)</option>
                      <option value="campaign.completed">campaign.completed (Broadcast Finished)</option>
                      <option value="payment.received">payment.received (Invoice Cleared)</option>
                      <option value="security.alert">security.alert (Login Alert)</option>
                    </select>
                  </div>
                  <div className="pm-form-group">
                    <label className="pm-form-label">Channel</label>
                    <select
                      className="pm-input"
                      value={formData.channel}
                      disabled
                    >
                      <option value="WHATSAPP">WhatsApp Cloud API</option>
                    </select>
                  </div>
                </div>

                <div className="pm-form-group" style={{ marginBottom: 10 }}>
                  <label className="pm-form-label" style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Message Body</span>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                      Click any variable pill below to insert
                    </span>
                  </label>
                  <textarea
                    className="pm-input"
                    rows={6}
                    style={{ fontFamily: 'inherit', resize: 'vertical' }}
                    value={formData.content}
                    onChange={(e) => {
                      const val = e.target.value;
                      setFormData({ ...formData, content: val });
                      updatePreview(val, editingTemplate?.id);
                    }}
                  />
                </div>

                {/* Variable Pills Allowlist */}
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 6 }}>
                    Allowlisted Context Variables
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {allowedVariables.map((v) => (
                      <button
                        key={v.variable}
                        type="button"
                        onClick={() => insertVariable(v.variable)}
                        className="pm-btn pm-btn-sm"
                        style={{
                          background: 'rgba(56, 189, 248, 0.1)',
                          color: '#38bdf8',
                          border: '1px solid rgba(56, 189, 248, 0.25)',
                          fontSize: '0.75rem',
                          padding: '3px 8px',
                          borderRadius: 14,
                        }}
                        title={v.description}
                      >
                        +{`{{${v.variable}}}`}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="pm-form-group">
                  <label className="pm-form-label">Change Summary (optional)</label>
                  <input
                    type="text"
                    className="pm-input"
                    placeholder="Brief description of modifications (e.g. Added department routing disclaimer)"
                    value={formData.change_summary}
                    onChange={(e) => setFormData({ ...formData, change_summary: e.target.value })}
                  />
                </div>
              </div>

              {/* WhatsApp Synthetic Live Preview Box */}
              <div>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Eye size={14} style={{ color: '#52bb89' }} />
                  <span>WhatsApp Live Preview</span>
                </div>

                {/* Mock Phone Container */}
                <div
                  style={{
                    background: '#0b141a',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 16,
                    padding: 12,
                    boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
                  }}
                >
                  {/* Phone Header */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      borderBottom: '1px solid rgba(255,255,255,0.08)',
                      paddingBottom: 8,
                      marginBottom: 12,
                    }}
                  >
                    <div style={{ width: 28, height: 28, borderRadius: '50%', background: '#52bb89', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '0.75rem', fontWeight: 700 }}>
                      C
                    </div>
                    <div>
                      <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#fff' }}>Convernix Cloud</div>
                      <div style={{ fontSize: '0.65rem', color: '#52bb89' }}>Official Business Account</div>
                    </div>
                  </div>

                  {/* WhatsApp Chat Bubble */}
                  <div
                    style={{
                      background: '#005c4b',
                      borderRadius: '8px 8px 8px 2px',
                      padding: 10,
                      maxWidth: '92%',
                      position: 'relative',
                    }}
                  >
                    <p style={{ margin: 0, fontSize: '0.85rem', color: '#e9edef', whiteSpace: 'pre-wrap', lineHeight: 1.45 }}>
                      {previewLoading ? 'Generating synthetic render...' : previewRendered || 'Message body is empty'}
                    </p>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'flex-end',
                        gap: 3,
                        marginTop: 4,
                        fontSize: '0.65rem',
                        color: 'rgba(255,255,255,0.6)',
                      }}
                    >
                      <span>14:32</span>
                      <CheckCircle size={10} style={{ color: '#53bdeb' }} />
                    </div>
                  </div>

                  {/* Sandboxed notice */}
                  <div style={{ marginTop: 14, padding: 8, borderRadius: 6, background: 'rgba(255,255,255,0.03)', fontSize: '0.7rem', color: '#64748b' }}>
                    Preview rendered using synthetic allowlist context. Zero runtime eval/exec vulnerability.
                  </div>
                </div>
              </div>
            </div>

            <div className="pm-modal-footer">
              <button
                type="button"
                className="pm-btn pm-btn-outline"
                onClick={() => setShowModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="pm-btn pm-btn-outline"
                onClick={handleSaveDraft}
              >
                Save as Draft
              </button>
              <button
                type="button"
                className="pm-btn pm-btn-primary"
                onClick={handlePublish}
              >
                <Send size={14} />
                <span>Publish Version</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

