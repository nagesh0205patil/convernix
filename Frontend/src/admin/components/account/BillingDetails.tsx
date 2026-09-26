import React, { useState, useEffect } from 'react';
import { AdminPageHeader } from '../common/AdminPageHeader';
import type { BillingDetails as BillingDetailsType } from '../../types';

interface BillingDetailsProps {
  billing: BillingDetailsType;
  onSave: (data: Partial<BillingDetailsType>) => Promise<boolean>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export function BillingDetails({ billing, onSave, toast }: BillingDetailsProps) {
  const [formData, setFormData] = useState<BillingDetailsType>(billing);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setFormData(billing);
    setDirty(false);
  }, [billing]);

  const handleChange = (field: keyof BillingDetailsType, val: string) => {
    setFormData((prev) => ({ ...prev, [field]: val }));
    setDirty(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.legal_company_name?.trim()) {
      toast('Legal company name is required.', 'error');
      return;
    }
    if (!formData.billing_email?.includes('@')) {
      toast('Valid billing email is required.', 'error');
      return;
    }

    setSaving(true);
    const ok = await onSave(formData);
    setSaving(false);
    if (ok) {
      setDirty(false);
    }
  };

  return (
    <div className="pm-account-panel">
      <AdminPageHeader
        breadcrumbs={[
          { label: 'Administration' },
          { label: 'Account' },
          { label: 'Billing Details' },
        ]}
        title="Billing Details"
        subtitle="Manage formal company invoicing attributes, GST/VAT registration numbers, and invoice recipient emails."
      />

      <form onSubmit={handleSubmit} className="pm-admin-form-pro" noValidate>
        <div className="pm-form-section">
          <h3>Tax & Company Invoicing</h3>
          <p className="pm-form-section-desc">
            These details appear verbatim on your generated monthly tax invoices and payment receipts.
          </p>

          <div className="pm-form-grid-2">
            <div className="pm-form-field">
              <label htmlFor="bill_company">
                Legal Company Name <span className="req">*</span>
              </label>
              <input
                id="bill_company"
                type="text"
                value={formData.legal_company_name || ''}
                onChange={(e) => handleChange('legal_company_name', e.target.value)}
                placeholder="Cloudtronix Solutions Pvt Ltd"
                required
              />
            </div>

            <div className="pm-form-field">
              <label htmlFor="bill_email">
                Billing Email <span className="req">*</span>
              </label>
              <input
                id="bill_email"
                type="email"
                value={formData.billing_email || ''}
                onChange={(e) => handleChange('billing_email', e.target.value)}
                placeholder="billing@cloudtronix.io"
                required
              />
              <small className="field-help">PDF invoices and payment notices will be routed here</small>
            </div>

            <div className="pm-form-field">
              <label htmlFor="bill_tax">Tax / GST Number</label>
              <input
                id="bill_tax"
                type="text"
                value={formData.tax_id || ''}
                onChange={(e) => handleChange('tax_id', e.target.value)}
                placeholder="27AABCC1234D1ZQ (India) or VAT/EIN"
              />
              <small className="field-help">Applicable for Indian GST, European VAT, or US EIN tax credits</small>
            </div>

            <div className="pm-form-field">
              <label htmlFor="bill_country">Country</label>
              <select
                id="bill_country"
                value={formData.country || 'India'}
                onChange={(e) => handleChange('country', e.target.value)}
              >
                <option value="India">India</option>
                <option value="United States">United States</option>
                <option value="United Kingdom">United Kingdom</option>
                <option value="United Arab Emirates">United Arab Emirates</option>
                <option value="Singapore">Singapore</option>
              </select>
            </div>
          </div>
        </div>

        <div className="pm-form-section">
          <h3>Billing Address</h3>
          <div className="pm-form-grid-3">
            <div className="pm-form-field">
              <label htmlFor="bill_state">State / Province</label>
              <input
                id="bill_state"
                type="text"
                value={formData.state || ''}
                onChange={(e) => handleChange('state', e.target.value)}
              />
            </div>

            <div className="pm-form-field">
              <label htmlFor="bill_city">City</label>
              <input
                id="bill_city"
                type="text"
                value={formData.city || ''}
                onChange={(e) => handleChange('city', e.target.value)}
              />
            </div>

            <div className="pm-form-field">
              <label htmlFor="bill_postal">Postal / PIN Code</label>
              <input
                id="bill_postal"
                type="text"
                value={formData.postal_code || ''}
                onChange={(e) => handleChange('postal_code', e.target.value)}
              />
            </div>
          </div>

          <div className="pm-form-field full-width" style={{ marginTop: 14 }}>
            <label htmlFor="bill_address">Street Address</label>
            <textarea
              id="bill_address"
              rows={3}
              value={formData.address || ''}
              onChange={(e) => handleChange('address', e.target.value)}
            />
          </div>
        </div>

        <div className="pm-form-actions-sticky">
          <button
            type="button"
            className="pm-secondary-btn"
            onClick={() => {
              setFormData(billing);
              setDirty(false);
            }}
            disabled={!dirty || saving}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="pm-primary-btn"
            disabled={!dirty || saving}
          >
            {saving ? 'Saving...' : 'Save Billing Information'}
          </button>
        </div>
      </form>
    </div>
  );
}
