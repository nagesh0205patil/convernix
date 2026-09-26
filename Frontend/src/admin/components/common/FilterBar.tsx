import React, { type ReactNode } from 'react';
import { Search, X } from 'lucide-react';

interface FilterOption {
  label: string;
  value: string;
}

export interface FilterSelectConfig {
  key: string;
  label: string;
  options: FilterOption[];
  value: string;
  onChange: (val: string) => void;
}

interface FilterBarProps {
  searchValue?: string;
  searchQuery?: string;
  onSearchChange?: (val: string) => void;
  searchPlaceholder?: string;
  filters?: FilterSelectConfig[];
  statusFilter?: string;
  onStatusChange?: (val: string) => void;
  statusOptions?: FilterOption[];
  actions?: ReactNode;
}

export function FilterBar({
  searchValue,
  searchQuery,
  onSearchChange,
  searchPlaceholder = 'Search records...',
  filters = [],
  statusFilter,
  onStatusChange,
  statusOptions,
  actions,
}: FilterBarProps) {
  const currentSearch = searchValue !== undefined ? searchValue : searchQuery || '';

  // Consolidate filters: explicit filters array + optional legacy statusFilter/options
  const allFilters = [...filters];
  if (statusFilter !== undefined && onStatusChange && statusOptions) {
    allFilters.push({
      key: 'status',
      label: 'Status',
      value: statusFilter,
      onChange: onStatusChange,
      options: statusOptions,
    });
  }

  return (
    <div className="pm-filter-bar-pro">
      <div className="pm-filter-bar-left">
        {onSearchChange !== undefined && (
          <div className="pm-search-box">
            <Search size={14} className="pm-search-icon" aria-hidden="true" />
            <input
              type="text"
              value={currentSearch}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder={searchPlaceholder}
              className="pm-search-input"
              aria-label={searchPlaceholder}
            />
            {currentSearch && (
              <button
                type="button"
                onClick={() => onSearchChange('')}
                className="pm-search-clear"
                aria-label="Clear search"
              >
                <X size={12} />
              </button>
            )}
          </div>
        )}

        {allFilters.map((filter) => (
          <div key={filter.key} className="pm-filter-select-wrap">
            <label htmlFor={`filter-${filter.key}`} className="sr-only">
              {filter.label}
            </label>
            <select
              id={`filter-${filter.key}`}
              value={filter.value}
              onChange={(e) => filter.onChange(e.target.value)}
              className="pm-filter-select"
            >
              {filter.options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>

      {actions && <div className="pm-filter-bar-actions">{actions}</div>}
    </div>
  );
}
