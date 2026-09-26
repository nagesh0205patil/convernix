import React, { useState } from 'react';
import type { InvoiceItem, BillingDetails } from '../../types';
import { StatusBadge } from '../common/StatusBadge';
import { FilterBar } from '../common/FilterBar';
import { DataTable } from '../common/DataTable';
import { FileText, Download, Eye, X } from 'lucide-react';

interface InvoicesViewProps {
  invoices: InvoiceItem[];
  billing: BillingDetails;
}

export function InvoicesView({ invoices, billing }: InvoicesViewProps) {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedInvoice, setSelectedInvoice] = useState<InvoiceItem | null>(null);

  const filteredInvoices = invoices.filter((inv) => {
    const matchesSearch =
      inv.invoice_number.toLowerCase().includes(search.toLowerCase()) ||
      inv.billing_period.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'all' || inv.status.toLowerCase() === statusFilter.toLowerCase();
    return matchesSearch && matchesStatus;
  });

  const handleDownload = (inv: InvoiceItem) => {
    // Simulated receipt download
    const element = document.createElement('a');
    const file = new Blob([
      `CONVERNIX INVOICE RECEIPT\n` +
      `Invoice Number: ${inv.invoice_number}\n` +
      `Period: ${inv.billing_period}\n` +
      `Date: ${inv.issue_date}\n` +
      `Billed To: ${billing.legal_company_name}\n` +
      `Tax ID: ${billing.tax_id}\n` +
      `Amount: ${inv.amount}\n` +
      `Status: ${inv.status.toUpperCase()}\n` +
      `Payment Method: ${inv.payment_method_desc}\n`
    ], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `${inv.invoice_number}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const columns = [
    {
      key: 'invoice_number',
      header: 'Invoice #',
      render: (inv: InvoiceItem) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FileText size={15} style={{ color: 'var(--pm-primary)' }} />
          <span style={{ fontWeight: 600, color: 'var(--pm-text)' }}>{inv.invoice_number}</span>
        </div>
      ),
    },
    {
      key: 'billing_period',
      header: 'Period',
      render: (inv: InvoiceItem) => <span>{inv.billing_period}</span>,
    },
    {
      key: 'issue_date',
      header: 'Issue Date',
      render: (inv: InvoiceItem) => <span style={{ color: 'var(--pm-text-muted)' }}>{inv.issue_date}</span>,
    },
    {
      key: 'amount',
      header: 'Amount',
      render: (inv: InvoiceItem) => (
        <span style={{ fontWeight: 600, color: 'var(--pm-text)' }}>
          {typeof inv.amount === 'number' ? `₹${inv.amount.toLocaleString('en-IN')}` : inv.amount}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (inv: InvoiceItem) => <StatusBadge status={inv.status} />,
    },
    {
      key: 'payment_method_desc',
      header: 'Payment Method',
      render: (inv: InvoiceItem) => (
        <span style={{ fontSize: '12px', color: 'var(--pm-text-muted)' }}>{inv.payment_method_desc}</span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      align: 'right' as const,
      render: (inv: InvoiceItem) => (
        <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
          <button
            type="button"
            className="pm-btn-secondary"
            style={{ padding: '4px 8px', fontSize: '12px' }}
            onClick={() => setSelectedInvoice(inv)}
            title="View Invoice"
            aria-label={`View invoice ${inv.invoice_number}`}
          >
            <Eye size={13} style={{ marginRight: '4px' }} /> View
          </button>
          <button
            type="button"
            className="pm-btn-secondary"
            style={{ padding: '4px 8px', fontSize: '12px' }}
            onClick={() => handleDownload(inv)}
            title="Download Invoice"
            aria-label={`Download invoice ${inv.invoice_number}`}
          >
            <Download size={13} />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="pm-view-container">
      <div className="pm-card" style={{ marginBottom: '20px' }}>
        <div className="pm-card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 className="pm-card-title">Invoices & Billing History</h3>
            <p className="pm-card-desc">
              View and download past tax invoices, receipts, and GST-compliant payment statements.
            </p>
          </div>
        </div>

        <FilterBar
          searchQuery={search}
          onSearchChange={setSearch}
          searchPlaceholder="Search invoices by number or period..."
          statusFilter={statusFilter}
          onStatusChange={setStatusFilter}
          statusOptions={[
            { value: 'all', label: 'All Invoices' },
            { value: 'paid', label: 'Paid' },
            { value: 'pending', label: 'Pending' },
            { value: 'failed', label: 'Failed' },
            { value: 'refunded', label: 'Refunded' },
          ]}
        />

        <DataTable
          columns={columns}
          data={filteredInvoices}
          emptyMessage="No invoices found matching your filter."
        />
      </div>

      {/* Invoice Detail Modal */}
      {selectedInvoice && (
        <div className="pm-modal-backdrop" onClick={() => setSelectedInvoice(null)}>
          <div
            className="pm-modal-content"
            style={{ maxWidth: '640px', width: '100%' }}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="invoice-modal-title"
          >
            <div className="pm-modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileText size={20} style={{ color: 'var(--pm-primary)' }} />
                <h3 id="invoice-modal-title" style={{ margin: 0, fontSize: '17px', color: 'var(--pm-text)' }}>
                  Tax Invoice {selectedInvoice.invoice_number}
                </h3>
              </div>
              <button
                type="button"
                className="pm-icon-btn"
                onClick={() => setSelectedInvoice(null)}
                aria-label="Close invoice details"
              >
                <X size={18} />
              </button>
            </div>

            <div className="pm-modal-body" style={{ padding: '20px' }}>
              {/* Top Meta info */}
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '24px', paddingBottom: '16px', borderBottom: '1px solid var(--pm-border)' }}>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--pm-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Billed By</div>
                  <div style={{ fontWeight: 600, color: 'var(--pm-text)', marginTop: '4px' }}>Convernix / Cloudtronix Technologies Pvt Ltd</div>
                  <div style={{ fontSize: '13px', color: 'var(--pm-text-muted)' }}>GSTIN: 27AABCC1234D1ZQ</div>
                  <div style={{ fontSize: '13px', color: 'var(--pm-text-muted)' }}>Pune, Maharashtra, India</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '12px', color: 'var(--pm-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Billed To</div>
                  <div style={{ fontWeight: 600, color: 'var(--pm-text)', marginTop: '4px' }}>{billing.legal_company_name || 'Organization Customer'}</div>
                  <div style={{ fontSize: '13px', color: 'var(--pm-text-muted)' }}>GSTIN / Tax ID: {billing.tax_id || 'Not Specified'}</div>
                  <div style={{ fontSize: '13px', color: 'var(--pm-text-muted)' }}>{billing.billing_email}</div>
                  <div style={{ fontSize: '13px', color: 'var(--pm-text-muted)' }}>{billing.address || billing.city || 'India'}</div>
                </div>
              </div>

              {/* Status & Date */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', background: 'var(--pm-bg-subtle)', padding: '12px 16px', borderRadius: '6px', marginBottom: '20px' }}>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--pm-text-muted)' }}>Issue Date</div>
                  <div style={{ fontWeight: 500, color: 'var(--pm-text)', fontSize: '13px', marginTop: '2px' }}>{selectedInvoice.issue_date}</div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--pm-text-muted)' }}>Billing Period</div>
                  <div style={{ fontWeight: 500, color: 'var(--pm-text)', fontSize: '13px', marginTop: '2px' }}>{selectedInvoice.billing_period}</div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--pm-text-muted)' }}>Payment Status</div>
                  <div style={{ marginTop: '2px' }}>
                    <StatusBadge status={selectedInvoice.status} />
                  </div>
                </div>
              </div>

              {/* Line Items */}
              <div style={{ marginBottom: '20px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--pm-border)', color: 'var(--pm-text-muted)', textAlign: 'left' }}>
                      <th style={{ padding: '8px 0', fontWeight: 500 }}>Description</th>
                      <th style={{ padding: '8px 0', fontWeight: 500, textAlign: 'right' }}>Qty</th>
                      <th style={{ padding: '8px 0', fontWeight: 500, textAlign: 'right' }}>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr style={{ borderBottom: '1px solid var(--pm-border)' }}>
                      <td style={{ padding: '12px 0' }}>
                        <div style={{ fontWeight: 500, color: 'var(--pm-text)' }}>Convernix Professional Plan</div>
                        <div style={{ fontSize: '12px', color: 'var(--pm-text-muted)' }}>
                          Subscription fee for {selectedInvoice.billing_period} (Includes 10 Seats, 3 WA Numbers, 25k Conversations)
                        </div>
                      </td>
                      <td style={{ padding: '12px 0', textAlign: 'right', color: 'var(--pm-text-muted)' }}>1</td>
                      <td style={{ padding: '12px 0', textAlign: 'right', fontWeight: 600, color: 'var(--pm-text)' }}>
                        {typeof selectedInvoice.amount === 'number' ? `₹${selectedInvoice.amount.toLocaleString('en-IN')}` : selectedInvoice.amount}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Totals */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', alignItems: 'flex-end', borderTop: '1px solid var(--pm-border)', paddingTop: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', width: '220px', fontSize: '13px', color: 'var(--pm-text-muted)' }}>
                  <span>Subtotal:</span>
                  <span>{typeof selectedInvoice.amount === 'number' ? `₹${(selectedInvoice.amount * 0.847).toFixed(2)}` : selectedInvoice.amount}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', width: '220px', fontSize: '13px', color: 'var(--pm-text-muted)' }}>
                  <span>CGST (9%) + SGST (9%):</span>
                  <span>Included (18%)</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', width: '220px', fontSize: '15px', fontWeight: 700, color: 'var(--pm-text)', marginTop: '4px', borderTop: '1px solid var(--pm-border)', paddingTop: '6px' }}>
                  <span>Total Paid:</span>
                  <span>{typeof selectedInvoice.amount === 'number' ? `₹${selectedInvoice.amount.toLocaleString('en-IN')}` : selectedInvoice.amount}</span>
                </div>
              </div>
            </div>

            <div className="pm-modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                type="button"
                className="pm-btn-secondary"
                onClick={() => setSelectedInvoice(null)}
              >
                Close
              </button>
              <button
                type="button"
                className="pm-btn-primary"
                onClick={() => handleDownload(selectedInvoice)}
              >
                <Download size={14} style={{ marginRight: '6px' }} /> Download PDF
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
