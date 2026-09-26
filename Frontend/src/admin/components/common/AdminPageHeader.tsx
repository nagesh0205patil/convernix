import React, { type ReactNode } from 'react';
import { Breadcrumbs, type BreadcrumbItem } from './Breadcrumbs';

interface AdminPageHeaderProps {
  breadcrumbs?: BreadcrumbItem[];
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export function AdminPageHeader({ breadcrumbs, title, subtitle, actions }: AdminPageHeaderProps) {
  return (
    <header className="pm-admin-header-pro">
      <div className="pm-admin-header-content">
        {breadcrumbs && breadcrumbs.length > 0 && <Breadcrumbs items={breadcrumbs} />}
        <div className="pm-admin-header-title-row">
          <div>
            <h1>{title}</h1>
            {subtitle && <p className="pm-admin-header-subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="pm-admin-header-actions">{actions}</div>}
        </div>
      </div>
    </header>
  );
}

