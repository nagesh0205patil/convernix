import React, { useState, useEffect, useRef } from 'react';
import { Building2, Upload, AlertCircle } from 'lucide-react';
import { AdminPageHeader } from '../common/AdminPageHeader';
import type { OrganizationProfile as OrgProfileType } from '../../types';

interface OrganizationProfileProps {
  initialData: OrgProfileType;
  onSave: (data: Partial<OrgProfileType>) => Promise<boolean>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export function OrganizationProfile({ initialData, onSave, toast }: OrganizationProfileProps) {
  const [formData, setFormData] = useState<OrgProfileType>(initialData);
  const [isDirty, setIsDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setFormData(initialData);
    setIsDirty(false);
  }, [initialData]);

  // Prompt before window unload if dirty
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isDirty]);

  const handleChange = (field: keyof OrgProfileType, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setIsDirty(true);
    if (errors[field]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 2 * 1024 * 1024) {
        toast('Logo image must be under 2MB in size.', 'error');
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        handleChange('logo_url', reader.result as string);
        toast('Logo selected. Remember to save changes.', 'info');
      };
      reader.readAsDataURL(file);
    }
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!formData.organization_name?.trim()) {
      newErrors.organization_name = 'Organization name is required.';
    }
    if (!formData.legal_business_name?.trim()) {
      newErrors.legal_business_name = 'Legal business name is required.';
    }
    if (formData.business_email && !formData.business_email.includes('@')) {
      newErrors.business_email = 'Enter a valid business email address.';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) {
      toast('Please review the errors before saving.', 'error');
      return;
    }

    setSaving(true);
    const success = await onSave(formData);
    setSaving(false);
    if (success) {
      setIsDirty(false);
    }
  };

  const handleCancel = () => {
    setFormData(initialData);
    setIsDirty(false);
    setErrors({});
    toast('Changes discarded.', 'info');
  };

  return (
    <div className="pm-settings-panel">
      <AdminPageHeader
        breadcrumbs={[
          { label: 'Administration' },
          { label: 'Settings' },
          { label: 'Organization Profile' },
        ]}
        title="Organization Profile"
        subtitle="Manage business legal identity, primary contacts, regional localization, and company branding."
      />

      {isDirty && (
        <div className="pm-unsaved-warning" role="alert">
          <AlertCircle size={15} />
          <span>You have unsaved changes. Remember to save before navigating away.</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="pm-admin-form-pro" noValidate>
        <div className="pm-form-section">
          <h3>Business Identity & Registration</h3>
          <p className="pm-form-section-desc">
            Primary organizational entity information as recognized across the Convernix SaaS platform.
          </p>

          <div className="pm-form-grid-2">
            <div className="pm-form-field">
              <label htmlFor="org_name">
                Organization Name <span className="req">*</span>
              </label>
              <input
                id="org_name"
                type="text"
                value={formData.organization_name || ''}
                onChange={(e) => handleChange('organization_name', e.target.value)}
                className={errors.organization_name ? 'error' : ''}
                required
              />
              {errors.organization_name && <small className="field-err">{errors.organization_name}</small>}
            </div>

            <div className="pm-form-field">
              <label htmlFor="legal_name">
                Legal Business Name <span className="req">*</span>
              </label>
              <input
                id="legal_name"
                type="text"
                value={formData.legal_business_name || ''}
                onChange={(e) => handleChange('legal_business_name', e.target.value)}
                className={errors.legal_business_name ? 'error' : ''}
                required
              />
              {errors.legal_business_name && <small className="field-err">{errors.legal_business_name}</small>}
            </div>

            <div className="pm-form-field">
              <label htmlFor="org_id">
                Organization ID <span className="meta-ro">(Read-only)</span>
              </label>
              <input
                id="org_id"
                type="text"
                value={formData.org_id || 'ORG-CLD-2048'}
                readOnly
                className="pm-input-readonly"
                title="System identifier scoped for multi-tenant isolation"
              />
              <small className="field-help">Global tenant identifier for API scoping and routing</small>
            </div>

            <div className="pm-form-field">
              <label htmlFor="industry">Industry</label>
              <select
                id="industry"
                value={formData.industry || 'Technology'}
                onChange={(e) => handleChange('industry', e.target.value)}
              >
                <option value="Technology">Technology & Software</option>
                <option value="E-commerce">E-commerce & Retail</option>
                <option value="Healthcare">Healthcare & Life Sciences</option>
                <option value="Financial Services">Financial Services & Fintech</option>
                <option value="Education">Education & EdTech</option>
                <option value="Hospitality">Hospitality & Tourism</option>
                <option value="Logistics">Logistics & Supply Chain</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>
        </div>

        <div className="pm-form-section">
          <h3>Communication & Web Presence</h3>
          <div className="pm-form-grid-3">
            <div className="pm-form-field">
              <label htmlFor="business_email">Business Email</label>
              <input
                id="business_email"
                type="email"
                value={formData.business_email || ''}
                onChange={(e) => handleChange('business_email', e.target.value)}
                className={errors.business_email ? 'error' : ''}
                placeholder="contact@company.com"
              />
              {errors.business_email && <small className="field-err">{errors.business_email}</small>}
            </div>

            <div className="pm-form-field">
              <label htmlFor="business_phone">Business Phone</label>
              <input
                id="business_phone"
                type="tel"
                value={formData.business_phone || ''}
                onChange={(e) => handleChange('business_phone', e.target.value)}
                placeholder="+91 98765 43210"
              />
            </div>

            <div className="pm-form-field">
              <label htmlFor="website">Website URL</label>
              <input
                id="website"
                type="url"
                value={formData.website || ''}
                onChange={(e) => handleChange('website', e.target.value)}
                placeholder="https://company.com"
              />
            </div>
          </div>
        </div>

        <div className="pm-form-section">
          <h3>Regional & Localization</h3>
          <div className="pm-form-grid-3">
            <div className="pm-form-field">
              <label htmlFor="country">Country</label>
              <select
                id="country"
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

            <div className="pm-form-field">
              <label htmlFor="state">State / Province</label>
              <input
                id="state"
                type="text"
                value={formData.state || ''}
                onChange={(e) => handleChange('state', e.target.value)}
              />
            </div>

            <div className="pm-form-field">
              <label htmlFor="city">City</label>
              <input
                id="city"
                type="text"
                value={formData.city || ''}
                onChange={(e) => handleChange('city', e.target.value)}
              />
            </div>

            <div className="pm-form-field">
              <label htmlFor="postal_code">Postal / Zip Code</label>
              <input
                id="postal_code"
                type="text"
                value={formData.postal_code || ''}
                onChange={(e) => handleChange('postal_code', e.target.value)}
              />
            </div>

            <div className="pm-form-field">
              <label htmlFor="timezone">Timezone</label>
              <select
                id="timezone"
                value={formData.timezone || 'Asia/Kolkata'}
                onChange={(e) => handleChange('timezone', e.target.value)}
              >
                <option value="Asia/Kolkata">Asia/Kolkata (IST +05:30)</option>
                <option value="UTC">UTC (+00:00)</option>
                <option value="America/New_York">America/New_York (EST -05:00)</option>
                <option value="America/Los_Angeles">America/Los_Angeles (PST -08:00)</option>
                <option value="Europe/London">Europe/London (GMT +00:00)</option>
                <option value="Asia/Dubai">Asia/Dubai (GST +04:00)</option>
                <option value="Asia/Singapore">Asia/Singapore (SGT +08:00)</option>
              </select>
            </div>

            <div className="pm-form-field">
              <label htmlFor="default_language">Default Language</label>
              <select
                id="default_language"
                value={formData.default_language || 'English'}
                onChange={(e) => handleChange('default_language', e.target.value)}
              >
                <option value="English">English</option>
                <option value="Hindi">Hindi</option>
                <option value="Spanish">Spanish</option>
                <option value="Arabic">Arabic</option>
              </select>
            </div>
          </div>

          <div className="pm-form-field full-width" style={{ marginTop: 14 }}>
            <label htmlFor="business_address">Registered Office Address</label>
            <textarea
              id="business_address"
              rows={3}
              value={formData.business_address || ''}
              onChange={(e) => handleChange('business_address', e.target.value)}
              placeholder="Building, street, and business park address..."
            />
          </div>
        </div>

        {/* Logo Upload Box */}
        <div className="pm-form-section">
          <h3>Brand Identity</h3>
          <div className="pm-logo-upload-card">
            <div className="pm-logo-preview-box">
              {formData.logo_url ? (
                <img src={formData.logo_url} alt="Organization Logo Preview" className="pm-logo-img" />
              ) : (
                <Building2 size={32} className="pm-logo-fallback" />
              )}
            </div>

            <div className="pm-logo-copy">
              <strong>Organization Logo</strong>
              <p>Recommended: 512 × 512px PNG, JPG, or SVG. Maximum file size: 2MB.</p>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleLogoUpload}
                style={{ display: 'none' }}
              />
              <button
                type="button"
                className="pm-secondary-btn small"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload size={13} /> {formData.logo_url ? 'Replace Logo' : 'Upload Logo'}
              </button>
            </div>
          </div>
        </div>

        <div className="pm-form-actions-sticky">
          <button
            type="button"
            className="pm-secondary-btn"
            onClick={handleCancel}
            disabled={!isDirty || saving}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="pm-primary-btn"
            disabled={!isDirty || saving}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  );
}

