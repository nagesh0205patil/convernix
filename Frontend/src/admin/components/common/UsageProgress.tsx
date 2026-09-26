import React from 'react';
import { AlertCircle } from 'lucide-react';
import type { UsageMetricItem } from '../../types';

interface UsageProgressProps {
  metrics: UsageMetricItem[];
  alerts?: string[];
  onUpgradeClick?: () => void;
}

export function UsageProgress({ metrics, alerts = [], onUpgradeClick }: UsageProgressProps) {
  return (
    <div className="pm-usage-container">
      <div className="pm-usage-list">
        {metrics.map((item) => {
          const isDanger = item.percent >= 90;
          const isWarning = item.percent >= 80 && !isDanger;

          return (
            <div key={item.key} className="pm-usage-item">
              <div className="pm-usage-item-head">
                <div className="pm-usage-label-wrap">
                  <strong>{item.label}</strong>
                  <span className="pm-usage-units">
                    {item.used.toLocaleString()} / {item.total.toLocaleString()} {item.unit}
                  </span>
                </div>
                <span className={`pm-usage-pct ${isDanger ? 'danger' : isWarning ? 'warning' : ''}`}>
                  {item.percent}%
                </span>
              </div>

              <div
                className="pm-usage-track"
                role="progressbar"
                aria-valuenow={item.percent}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${item.label} capacity usage`}
              >
                <div
                  className={`pm-usage-fill ${isDanger ? 'danger' : isWarning ? 'warning' : ''}`}
                  style={{ width: `${Math.min(item.percent, 100)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {alerts.length > 0 && (
        <div className="pm-usage-alerts">
          {alerts.map((msg, i) => (
            <div key={i} className="pm-usage-alert-banner" role="alert">
              <AlertCircle size={15} className="pm-alert-icon" />
              <span>{msg}</span>
              {onUpgradeClick && (
                <button type="button" className="pm-usage-upgrade-btn" onClick={onUpgradeClick}>
                  Upgrade Capacity →
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

