import React, { useState } from 'react';
import {
  Zap,
  CheckCircle2,
  Calendar,
  Users,
  MessageSquare,
  Sparkles,
  Shield,
  X,
} from 'lucide-react';
import { AdminPageHeader } from '../common/AdminPageHeader';
import { StatusBadge } from '../common/StatusBadge';
import { ConfirmationDialog } from '../common/ConfirmationDialog';
import type { SubscriptionPlanInfo } from '../../types';

interface SubscriptionViewProps {
  subscription: SubscriptionPlanInfo;
  onUpgrade: (tier: string) => Promise<boolean>;
  onCancel: (reason?: string) => Promise<boolean>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export function SubscriptionView({
  subscription,
  onUpgrade,
  onCancel,
  toast,
}: SubscriptionViewProps) {
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [busy, setBusy] = useState(false);

  const plans = [
    {
      tier: 'small',
      name: 'Basic',
      price: '₹2,499',
      period: '/ month',
      seats: '3 team seats',
      numbers: '1 WhatsApp number',
      conversations: '5,000 conversations/mo',
      campaigns: '5 monthly campaigns',
      storage: '5 GB storage',
      popular: false,
    },
    {
      tier: 'mid',
      name: 'Professional',
      price: '₹9,999',
      period: '/ month',
      seats: '10 team seats',
      numbers: '3 WhatsApp numbers',
      conversations: '25,000 conversations/mo',
      campaigns: '50 monthly campaigns',
      storage: '10 GB storage',
      popular: true,
    },
    {
      tier: 'large',
      name: 'Enterprise',
      price: '₹24,999',
      period: '/ month',
      seats: 'Unlimited seats',
      numbers: '25 WhatsApp numbers',
      conversations: '100,000+ conversations/mo',
      campaigns: 'Unlimited campaigns',
      storage: '25 GB storage',
      popular: false,
    },
  ];

  const handleSelectTier = async (tier: string) => {
    setBusy(true);
    const ok = await onUpgrade(tier);
    setBusy(false);
    if (ok) {
      toast(`Successfully updated plan tier.`, 'success');
      setShowUpgradeModal(false);
    }
  };

  const handleConfirmCancel = async () => {
    setBusy(true);
    const ok = await onCancel();
    setBusy(false);
    if (ok) {
      toast('Cancellation request submitted.', 'info');
      setShowCancelModal(false);
    }
  };

  return (
    <div className="pm-account-panel">
      <AdminPageHeader
        breadcrumbs={[
          { label: 'Administration' },
          { label: 'Account' },
          { label: 'Subscription' },
        ]}
        title="Subscription Management"
        subtitle="Review platform capacity tier, included WhatsApp numbers, seat quotas, and renewal cycle."
        actions={
          <div className="pm-header-action-group">
            <button
              type="button"
              className="pm-secondary-btn"
              onClick={() => setShowUpgradeModal(true)}
            >
              Change Plan
            </button>
            <button
              type="button"
              className="pm-primary-btn"
              onClick={() => setShowUpgradeModal(true)}
            >
              <Zap size={14} /> Upgrade Plan
            </button>
          </div>
        }
      />

      {/* Primary Current Plan Card */}
      <div className="pm-subscription-hero-card">
        <div className="pm-sub-hero-head">
          <div>
            <span className="pm-sub-label">Current Plan</span>
            <h2>{subscription.plan_name} Plan</h2>
          </div>
          <div className="pm-sub-price-tag">
            <strong>{subscription.price}</strong>
            <StatusBadge status={subscription.status} />
          </div>
        </div>

        <div className="pm-sub-details-grid">
          <div className="pm-sub-detail-cell">
            <Calendar size={16} className="pm-detail-icon" />
            <div>
              <small>Billing Cycle</small>
              <strong>{subscription.billing_cycle}</strong>
            </div>
          </div>

          <div className="pm-sub-detail-cell">
            <Calendar size={16} className="pm-detail-icon" />
            <div>
              <small>Next Renewal Date</small>
              <strong>{subscription.renewal_date}</strong>
            </div>
          </div>

          <div className="pm-sub-detail-cell">
            <Users size={16} className="pm-detail-icon" />
            <div>
              <small>Included Operator Seats</small>
              <strong>{subscription.seats_included} Included</strong>
            </div>
          </div>

          <div className="pm-sub-detail-cell">
            <MessageSquare size={16} className="pm-detail-icon" />
            <div>
              <small>Active WhatsApp Numbers</small>
              <strong>{subscription.numbers_included} Included</strong>
            </div>
          </div>

          <div className="pm-sub-detail-cell full">
            <Sparkles size={16} className="pm-detail-icon" />
            <div>
              <small>Message / Conversation Allowance</small>
              <strong>{subscription.allowance_conversations}</strong>
            </div>
          </div>
        </div>

        <div className="pm-sub-hero-footer">
          <div className="pm-sub-protect-note">
            <Shield size={14} color="#52bb89" />
            <span>Encrypted PCI billing with GST tax invoice generation.</span>
          </div>

          <button
            type="button"
            className="pm-btn-link danger"
            onClick={() => setShowCancelModal(true)}
          >
            Cancel Subscription
          </button>
        </div>
      </div>

      {/* Upgrade / Tier Comparison Modal */}
      {showUpgradeModal && (
        <div className="pm-modal-overlay" onClick={() => setShowUpgradeModal(false)} role="presentation">
          <div
            className="pm-plan-comparison-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="upgrade-modal-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="pm-modal-top-bar">
              <div>
                <h2 id="upgrade-modal-title">Upgrade Convernix Workspace Plan</h2>
                <p>Select the subscription tier suited for your WhatsApp operational volume.</p>
              </div>
              <button
                type="button"
                className="pm-modal-close"
                onClick={() => setShowUpgradeModal(false)}
                aria-label="Close upgrade modal"
              >
                <X size={16} />
              </button>
            </div>

            <div className="pm-pricing-tier-grid">
              {plans.map((p) => {
                const isCurrent = p.name.toLowerCase() === subscription.plan_name.toLowerCase();

                return (
                  <div
                    key={p.tier}
                    className={`pm-tier-card ${p.popular ? 'featured' : ''} ${isCurrent ? 'current' : ''}`}
                  >
                    {p.popular && <span className="pm-featured-pill">Most Popular</span>}
                    <h3>{p.name}</h3>
                    <div className="pm-tier-price">
                      <strong>{p.price}</strong>
                      <span>{p.period}</span>
                    </div>

                    <ul className="pm-tier-features">
                      <li><CheckCircle2 size={13} color="#25d366" /> {p.seats}</li>
                      <li><CheckCircle2 size={13} color="#25d366" /> {p.numbers}</li>
                      <li><CheckCircle2 size={13} color="#25d366" /> {p.conversations}</li>
                      <li><CheckCircle2 size={13} color="#25d366" /> {p.campaigns}</li>
                      <li><CheckCircle2 size={13} color="#25d366" /> {p.storage}</li>
                    </ul>

                    <button
                      type="button"
                      className={isCurrent ? 'pm-secondary-btn full-width' : 'pm-primary-btn full-width'}
                      disabled={isCurrent || busy}
                      onClick={() => handleSelectTier(p.tier)}
                    >
                      {isCurrent ? 'Current Plan' : `Upgrade to ${p.name}`}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Cancellation Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={showCancelModal}
        title="Cancel Subscription?"
        message="Canceling your subscription will schedule your workspace for deactivation at the end of the current billing period on 20 October 2026. You can re-activate anytime before then without losing your WhatsApp templates or routing rules."
        confirmLabel="Confirm Cancellation"
        isDanger={true}
        onConfirm={handleConfirmCancel}
        onCancel={() => setShowCancelModal(false)}
        loading={busy}
      />
    </div>
  );
}
