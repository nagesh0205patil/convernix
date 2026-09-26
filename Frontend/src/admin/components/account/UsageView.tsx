import React from 'react';
import type { UsageMetricItem } from '../../types';
import { UsageProgress } from '../common/UsageProgress';
import { MetricCard } from '../common/MetricCard';
import { Users, PhoneCall, MessageSquare, Database, ArrowUpRight, ShieldAlert } from 'lucide-react';

interface UsageViewProps {
  usage: {
    metrics: UsageMetricItem[];
    alerts: string[];
  };
  onNavigateToSubscription?: () => void;
}

export function UsageView({ usage, onNavigateToSubscription }: UsageViewProps) {
  const seatsMetric = usage.metrics.find((m) => m.key === 'team_members');
  const waMetric = usage.metrics.find((m) => m.key === 'whatsapp_numbers');
  const convMetric = usage.metrics.find((m) => m.key === 'conversations');
  const storageMetric = usage.metrics.find((m) => m.key === 'storage');

  return (
    <div className="pm-view-container">
      {/* High-level summary metrics */}
      <div className="pm-metrics-grid" style={{ marginBottom: '20px' }}>
        <MetricCard
          title="Team Seats Utilized"
          value={seatsMetric ? `${seatsMetric.used} / ${seatsMetric.total}` : '8 / 10'}
          meta={seatsMetric ? `${seatsMetric.percent}% of allocated capacity` : '80% used'}
          icon={Users}
        />
        <MetricCard
          title="Active WhatsApp Numbers"
          value={waMetric ? `${waMetric.used} / ${waMetric.total}` : '2 / 3'}
          meta={waMetric ? `${waMetric.percent}% connected` : '66% used'}
          icon={PhoneCall}
        />
        <MetricCard
          title="Conversations This Cycle"
          value={convMetric ? convMetric.used.toLocaleString() : '14,250'}
          meta={convMetric ? `Limit: ${convMetric.total.toLocaleString()}` : 'Limit: 25,000'}
          icon={MessageSquare}
        />
        <MetricCard
          title="Cloud Storage Consumed"
          value={storageMetric ? `${storageMetric.used} GB` : '2.4 GB'}
          meta={storageMetric ? `Limit: ${storageMetric.total} GB` : 'Limit: 10.0 GB'}
          icon={Database}
        />
      </div>

      {/* Main progress card */}
      <div className="pm-card" style={{ marginBottom: '20px' }}>
        <div className="pm-card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 className="pm-card-title">Capacity & Usage Gauges</h3>
            <p className="pm-card-desc">
              Monitor your team seat allocations, WhatsApp business phone lines, and monthly conversational volumes.
            </p>
          </div>
          {onNavigateToSubscription && (
            <button
              type="button"
              className="pm-btn-primary"
              style={{ fontSize: '12px' }}
              onClick={onNavigateToSubscription}
            >
              <ArrowUpRight size={14} style={{ marginRight: '4px' }} /> Upgrade Plan
            </button>
          )}
        </div>

        <UsageProgress
          metrics={usage.metrics}
          alerts={usage.alerts}
          onUpgradeClick={onNavigateToSubscription}
        />
      </div>

      {/* Resource Policy Guidance */}
      <div className="pm-card">
        <div className="pm-card-header">
          <h3 className="pm-card-title">Usage & Throttling Policies</h3>
          <p className="pm-card-desc">
            Rules governing fair usage, rate limits, and automatic alert thresholds.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', fontSize: '13px' }}>
          <div style={{ padding: '14px', background: 'var(--pm-bg-subtle)', borderRadius: '6px', border: '1px solid var(--pm-border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, color: 'var(--pm-text)', marginBottom: '6px' }}>
              <ShieldAlert size={16} style={{ color: 'var(--pm-warning)' }} />
              <span>80% Warning Threshold</span>
            </div>
            <p style={{ margin: 0, color: 'var(--pm-text-muted)', lineHeight: '1.5' }}>
              An in-app notification and email advisory are sent to Tenant Admins when any resource reaches 80% capacity.
            </p>
          </div>

          <div style={{ padding: '14px', background: 'var(--pm-bg-subtle)', borderRadius: '6px', border: '1px solid var(--pm-border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, color: 'var(--pm-text)', marginBottom: '6px' }}>
              <ShieldAlert size={16} style={{ color: 'var(--pm-danger)' }} />
              <span>90% Critical Threshold</span>
            </div>
            <p style={{ margin: 0, color: 'var(--pm-text-muted)', lineHeight: '1.5' }}>
              High-priority alerts are triggered. Upgrade recommendations appear directly in agent inboxes and administration headers.
            </p>
          </div>

          <div style={{ padding: '14px', background: 'var(--pm-bg-subtle)', borderRadius: '6px', border: '1px solid var(--pm-border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, color: 'var(--pm-text)', marginBottom: '6px' }}>
              <ShieldAlert size={16} style={{ color: 'var(--pm-danger)' }} />
              <span>100% Hard Cap</span>
            </div>
            <p style={{ margin: 0, color: 'var(--pm-text-muted)', lineHeight: '1.5' }}>
              Further seat invitations or line bindings are paused until an upgraded plan or capacity add-on pack is applied.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

