import React, { useEffect, useState } from 'react';
import {
  Building,
  Plus,
  RefreshCw,
  Search,
  Users,
  Clock,
  Shield,
  Archive,
  Edit2,
  CheckCircle,
  AlertCircle,
  X,
} from 'lucide-react';
import { adminApi } from '../../services/adminApi';
import type { AdminUser, DepartmentInfo } from '../../types';

interface DepartmentsManagementProps {
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export function DepartmentsManagement({ toast }: DepartmentsManagementProps) {
  const [departments, setDepartments] = useState<DepartmentInfo[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [includeArchived, setIncludeArchived] = useState(false);

  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [editingDept, setEditingDept] = useState<DepartmentInfo | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    manager_id: '' as string | number,
    start_time: '09:00',
    end_time: '18:00',
    timezone: 'Asia/Kolkata',
    weekend_support: false,
    is_active: true,
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [deptRes, usersRes] = await Promise.all([
        adminApi.getDepartments({ include_archived: includeArchived, search: searchQuery }),
        adminApi.getUsers(),
      ]);
      setDepartments(deptRes.departments || []);
      setUsers(usersRes.users || []);
    } catch (err: any) {
      toast(err.message || 'Failed to load departments', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [includeArchived]);

  const handleOpenCreate = () => {
    setEditingDept(null);
    setFormData({
      name: '',
      description: '',
      manager_id: '',
      start_time: '09:00',
      end_time: '18:00',
      timezone: 'Asia/Kolkata',
      weekend_support: false,
      is_active: true,
    });
    setShowModal(true);
  };

  const handleOpenEdit = (dept: DepartmentInfo) => {
    setEditingDept(dept);
    const bh = dept.business_hours || {};
    setFormData({
      name: dept.name,
      description: dept.description || '',
      manager_id: dept.manager || '',
      start_time: bh.start_time || '09:00',
      end_time: bh.end_time || '18:00',
      timezone: bh.timezone || 'Asia/Kolkata',
      weekend_support: !!bh.weekend_support,
      is_active: dept.is_active,
    });
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast('Department name is required.', 'error');
      return;
    }

    const business_hours = {
      start_time: formData.start_time,
      end_time: formData.end_time,
      timezone: formData.timezone,
      weekend_support: formData.weekend_support,
    };

    try {
      if (editingDept) {
        await adminApi.updateDepartment(editingDept.id, {
          name: formData.name.trim(),
          description: formData.description.trim(),
          manager_id: formData.manager_id ? Number(formData.manager_id) : undefined,
          business_hours,
          is_active: formData.is_active,
        });
        toast('Department updated successfully.', 'success');
      } else {
        await adminApi.createDepartment({
          name: formData.name.trim(),
          description: formData.description.trim(),
          manager_id: formData.manager_id ? Number(formData.manager_id) : undefined,
          business_hours,
        });
        toast('Department created successfully.', 'success');
      }
      setShowModal(false);
      fetchData();
    } catch (err: any) {
      toast(err.message || 'Failed to save department.', 'error');
    }
  };

  const handleArchive = async (dept: DepartmentInfo) => {
    if (
      !confirm(
        `Are you sure you want to archive "${dept.name}"?\n\nHistorical conversations, tickets, and audit records will be preserved safely. New enquiries will no longer be routed to this department.`
      )
    ) {
      return;
    }

    try {
      await adminApi.archiveDepartment(dept.id);
      toast(`Department "${dept.name}" archived.`, 'success');
      fetchData();
    } catch (err: any) {
      toast(err.message || 'Failed to archive department.', 'error');
    }
  };

  const filteredDepts = departments.filter((d) =>
    d.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="pm-settings-panel">
      {/* Top Header */}
      <div className="pm-panel-header-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-primary, #fff)' }}>
            Departments & Routing
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '0.85rem', color: 'var(--text-secondary, #94a3b8)' }}>
            Configure operational departments, business operating hours, assigned supervisors, and conversation queues.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            type="button"
            className="pm-btn pm-btn-outline"
            onClick={fetchData}
            title="Refresh departments"
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
            <span>New Department</span>
          </button>
        </div>
      </div>

      {/* Filter Row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
        <div className="pm-search-input-wrap" style={{ width: 340, position: 'relative' }}>
          <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#64748b' }} />
          <input
            type="text"
            className="pm-input"
            style={{ paddingLeft: 36, width: '100%' }}
            placeholder="Search departments..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem', color: '#cbd5e1', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={includeArchived}
            onChange={(e) => setIncludeArchived(e.target.checked)}
          />
          <span>Include archived departments</span>
        </label>
      </div>

      {/* Departments Table */}
      <div className="pm-table-container">
        <table className="pm-table">
          <thead>
            <tr>
              <th>Department</th>
              <th>Assigned Manager</th>
              <th>Active Members</th>
              <th>Operating Hours</th>
              <th>Status</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: '36px 0', color: '#94a3b8' }}>
                  Loading departments...
                </td>
              </tr>
            ) : filteredDepts.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: '36px 0', color: '#94a3b8' }}>
                  No departments found.
                </td>
              </tr>
            ) : (
              filteredDepts.map((d) => {
                const bh = d.business_hours || {};
                const hoursText = bh.start_time && bh.end_time ? `${bh.start_time} - ${bh.end_time}` : '24x7 Coverage';
                return (
                  <tr key={d.id} style={{ opacity: d.is_archived ? 0.65 : 1 }}>
                    <td>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <Building size={16} style={{ color: d.is_archived ? '#94a3b8' : '#38bdf8' }} />
                          <span style={{ fontWeight: 600, color: 'var(--text-primary, #fff)' }}>{d.name}</span>
                          {d.is_archived && (
                            <span style={{ fontSize: '0.7rem', background: 'rgba(239, 68, 68, 0.2)', color: '#f87171', padding: '1px 6px', borderRadius: 4 }}>
                              ARCHIVED
                            </span>
                          )}
                        </div>
                        {d.description && (
                          <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: 2 }}>{d.description}</div>
                        )}
                      </div>
                    </td>
                    <td>
                      <span style={{ fontSize: '0.85rem', color: d.manager_name ? '#cbd5e1' : '#64748b' }}>
                        {d.manager_name || 'Unassigned'}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.85rem' }}>
                        <Users size={14} style={{ color: '#94a3b8' }} />
                        <span>{d.member_count} agents</span>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.82rem', color: '#cbd5e1' }}>
                        <Clock size={13} style={{ color: '#52bb89' }} />
                        <span>{hoursText}</span>
                      </div>
                    </td>
                    <td>
                      <span
                        style={{
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: 12,
                          background: d.is_active && !d.is_archived ? 'rgba(82, 187, 137, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                          color: d.is_active && !d.is_archived ? '#52bb89' : '#f87171',
                        }}
                      >
                        {d.is_archived ? 'Archived' : d.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: 6 }}>
                        <button
                          type="button"
                          className="pm-btn pm-btn-sm pm-btn-outline"
                          onClick={() => handleOpenEdit(d)}
                          title="Edit department settings"
                        >
                          <Edit2 size={12} />
                          <span>Edit</span>
                        </button>
                        {!d.is_archived && (
                          <button
                            type="button"
                            className="pm-btn pm-btn-sm pm-btn-outline"
                            onClick={() => handleArchive(d)}
                            title="Safely archive department (preserves historical references)"
                          >
                            <Archive size={12} />
                            <span>Archive</span>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Create / Edit Department Modal */}
      {showModal && (
        <div className="pm-modal-overlay" onClick={() => setShowModal(false)}>
          <div className="pm-modal" style={{ maxWidth: 540 }} onClick={(e) => e.stopPropagation()}>
            <form onSubmit={handleSave}>
              <div className="pm-modal-header">
                <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 600 }}>
                  {editingDept ? `Edit Department: ${editingDept.name}` : 'Create New Department'}
                </h3>
                <button
                  type="button"
                  className="pm-modal-close"
                  onClick={() => setShowModal(false)}
                >
                  <X size={18} />
                </button>
              </div>

              <div className="pm-modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div className="pm-form-group">
                  <label className="pm-form-label">Department Name *</label>
                  <input
                    type="text"
                    className="pm-input"
                    placeholder="e.g. Enterprise Sales, Escalation Support"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>

                <div className="pm-form-group">
                  <label className="pm-form-label">Description</label>
                  <textarea
                    className="pm-input"
                    rows={2}
                    placeholder="Workflow responsibility and routing objective"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  />
                </div>

                <div className="pm-form-group">
                  <label className="pm-form-label">Department Manager / Supervisor</label>
                  <select
                    className="pm-input"
                    value={formData.manager_id}
                    onChange={(e) => setFormData({ ...formData, manager_id: e.target.value })}
                  >
                    <option value="">Unassigned (Open Team)</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.name} ({u.role})
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div className="pm-form-group">
                    <label className="pm-form-label">Shift Start Time</label>
                    <input
                      type="time"
                      className="pm-input"
                      value={formData.start_time}
                      onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                    />
                  </div>
                  <div className="pm-form-group">
                    <label className="pm-form-label">Shift End Time</label>
                    <input
                      type="time"
                      className="pm-input"
                      value={formData.end_time}
                      onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                    />
                  </div>
                </div>

                <div className="pm-form-group">
                  <label className="pm-form-label">Timezone</label>
                  <select
                    className="pm-input"
                    value={formData.timezone}
                    onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                  >
                    <option value="Asia/Kolkata">Asia/Kolkata (IST +05:30)</option>
                    <option value="UTC">UTC (Universal Coordinated)</option>
                    <option value="America/New_York">America/New_York (EST/EDT)</option>
                    <option value="Europe/London">Europe/London (GMT/BST)</option>
                    <option value="Asia/Dubai">Asia/Dubai (GST +04:00)</option>
                    <option value="Asia/Singapore">Asia/Singapore (SGT +08:00)</option>
                  </select>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 4 }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem', color: '#cbd5e1', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={formData.weekend_support}
                      onChange={(e) => setFormData({ ...formData, weekend_support: e.target.checked })}
                    />
                    <span>Weekend On-Call Coverage enabled</span>
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem', color: '#cbd5e1', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={formData.is_active}
                      onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    />
                    <span>Department Active in Routing Directory</span>
                  </label>
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
                  type="submit"
                  className="pm-btn pm-btn-primary"
                >
                  Save Department
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

