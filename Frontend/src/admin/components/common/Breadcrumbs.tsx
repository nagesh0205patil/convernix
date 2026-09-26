import React from 'react';
import { ChevronRight } from 'lucide-react';

export interface BreadcrumbItem {
  label: string;
  onClick?: () => void;
  active?: boolean;
}

export function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav className="pm-breadcrumbs" aria-label="Breadcrumb">
      <ol>
        {items.map((item, idx) => {
          const isLast = idx === items.length - 1;
          return (
            <li key={item.label} className={isLast ? 'active' : ''}>
              {idx > 0 && <ChevronRight size={12} className="pm-bc-separator" aria-hidden="true" />}
              {item.onClick && !isLast ? (
                <button type="button" onClick={item.onClick} className="pm-bc-link">
                  {item.label}
                </button>
              ) : (
                <span className="pm-bc-current" aria-current={isLast ? 'page' : undefined}>
                  {item.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

