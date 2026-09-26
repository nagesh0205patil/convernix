import React, { type ReactNode } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T, index: number) => ReactNode;
  width?: string;
  align?: 'left' | 'center' | 'right';
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor?: (item: T, index: number) => string | number;
  emptyState?: ReactNode;
  emptyMessage?: string;
  loading?: boolean;
  page?: number;
  pageSize?: number;
  totalItems?: number;
  onPageChange?: (newPage: number) => void;
  className?: string;
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor = (item: any, idx: number) => item?.id ?? idx,
  emptyState,
  emptyMessage,
  loading,
  page = 1,
  pageSize = 10,
  totalItems,
  onPageChange,
  className = '',
}: DataTableProps<T>) {
  const totalPages = totalItems ? Math.ceil(totalItems / pageSize) : 1;

  if (loading) {
    return (
      <div className="pm-table-loading" role="status" aria-label="Loading data">
        <div className="pm-spinner" />
        <span>Loading records...</span>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="pm-table-empty-container">
        {emptyState || (
          <p style={{ textAlign: 'center', color: 'var(--pm-text-muted)', padding: '24px 0', margin: 0 }}>
            {emptyMessage || 'No records found.'}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className={`pm-data-table-wrapper ${className}`}>
      <div className="pm-table-scroll">
        <table className="pm-enterprise-table" role="table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  style={{ width: col.width, textAlign: col.align || 'left' }}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((item, idx) => (
              <tr key={keyExtractor(item, idx)}>
                {columns.map((col) => (
                  <td key={col.key} style={{ textAlign: col.align || 'left' }}>
                    {col.render ? col.render(item, idx) : (item as any)[col.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalItems !== undefined && totalItems > pageSize && onPageChange && (
        <div className="pm-table-pagination">
          <span className="pm-pagination-info">
            Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, totalItems)} of {totalItems} entries
          </span>
          <div className="pm-pagination-controls">
            <button
              type="button"
              className="pm-page-btn"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              aria-label="Previous page"
            >
              <ChevronLeft size={14} />
            </button>
            <span className="pm-page-indicator">
              Page {page} of {totalPages}
            </span>
            <button
              type="button"
              className="pm-page-btn"
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              aria-label="Next page"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
