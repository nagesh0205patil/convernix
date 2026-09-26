import React, { type ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: ReactNode;
  meta?: string;
  info?: string;
  icon: LucideIcon;
  actionLabel?: string;
  onAction?: () => void;
  badge?: ReactNode;
}

export function MetricCard({
  title,
  value,
  meta,
  info,
  icon: Icon,
  actionLabel,
  onAction,
  badge,
}: MetricCardProps) {
  return (
    <div className="pm-metric-card-pro">
      <div className="pm-metric-card-top">
        <div className="pm-metric-card-title-group">
          <div className="pm-metric-card-icon" aria-hidden="true">
            <Icon size={16} />
          </div>
          <span className="pm-metric-card-title">{title}</span>
        </div>
        {badge && <div>{badge}</div>}
      </div>

      <div className="pm-metric-card-body">
        <div className="pm-metric-card-value">{value}</div>
        {meta && <p className="pm-metric-card-meta">{meta}</p>}
        {info && <small className="pm-metric-card-info">{info}</small>}
      </div>

      {actionLabel && (
        <div className="pm-metric-card-footer">
          <button
            type="button"
            className="pm-btn-link"
            onClick={onAction}
            aria-label={`${actionLabel} for ${title}`}
          >
            {actionLabel} →
          </button>
        </div>
      )}
    </div>
  );
}

