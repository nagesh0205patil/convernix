import React, { type ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  secondaryAction?: ReactNode;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  secondaryAction,
}: EmptyStateProps) {
  return (
    <div className="pm-empty-state-pro" role="region" aria-label={title}>
      <div className="pm-empty-state-icon" aria-hidden="true">
        <Icon size={32} />
      </div>
      <h3 className="pm-empty-state-title">{title}</h3>
      <p className="pm-empty-state-desc">{description}</p>
      {(actionLabel || secondaryAction) && (
        <div className="pm-empty-state-actions">
          {actionLabel && onAction && (
            <button type="button" className="pm-primary-btn" onClick={onAction}>
              {actionLabel}
            </button>
          )}
          {secondaryAction}
        </div>
      )}
    </div>
  );
}

