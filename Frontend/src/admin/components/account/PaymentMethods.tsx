import React, { useState } from 'react';
import { CreditCard, Plus, ShieldCheck, X } from 'lucide-react';
import { AdminPageHeader } from '../common/AdminPageHeader';
import { ConfirmationDialog } from '../common/ConfirmationDialog';
import type { PaymentCard } from '../../types';

interface PaymentMethodsProps {
  paymentMethods: PaymentCard[];
  onAddCard: (card: any) => Promise<boolean>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}

export function PaymentMethods({ paymentMethods, onAddCard, toast }: PaymentMethodsProps) {
  const [methods, setMethods] = useState<PaymentCard[]>(paymentMethods);
  const [showAddModal, setShowAddModal] = useState(false);
  const [removeTarget, setRemoveTarget] = useState<PaymentCard | null>(null);

  // Form state for adding card
  const [cardNumber, setCardNumber] = useState('');
  const [expMonth, setExpMonth] = useState('12');
  const [expYear, setExpYear] = useState('2029');
  const [cvc, setCvc] = useState('');
  const [adding, setAdding] = useState(false);

  const handleSetDefault = (id: number) => {
    setMethods((prev) =>
      prev.map((m) => ({ ...m, is_default: m.id === id }))
    );
    toast('Default payment method updated.', 'success');
  };

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanNum = cardNumber.replace(/\s+/g, '');
    if (cleanNum.length < 15) {
      toast('Please enter a valid card number.', 'error');
      return;
    }

    setAdding(true);
    const ok = await onAddCard({
      card_brand: cleanNum.startsWith('4') ? 'Visa' : 'Mastercard',
      last4: cleanNum.slice(-4),
      exp_month: parseInt(expMonth, 10),
      exp_year: parseInt(expYear, 10),
      is_default: true,
    });
    setAdding(false);
    if (ok) {
      setCardNumber('');
      setCvc('');
      setShowAddModal(false);
    }
  };

  const handleRemove = (id: number) => {
    setMethods((prev) => prev.filter((m) => m.id !== id));
    setRemoveTarget(null);
    toast('Payment method removed.', 'info');
  };

  return (
    <div className="pm-account-panel">
      <AdminPageHeader
        breadcrumbs={[
          { label: 'Administration' },
          { label: 'Account' },
          { label: 'Payment Methods' },
        ]}
        title="Payment Methods"
        subtitle="Manage credit and corporate purchasing cards for recurring WhatsApp platform subscription billing."
        actions={
          <button
            type="button"
            className="pm-primary-btn"
            onClick={() => setShowAddModal(true)}
          >
            <Plus size={14} /> Add Payment Method
          </button>
        }
      />

      <div className="pm-pci-badge-banner">
        <ShieldCheck size={16} color="#52bb89" />
        <span>
          Payment card security is protected via end-to-end PCI-DSS tokenization. Convernix never stores raw card credentials.
        </span>
      </div>

      <div className="pm-payment-cards-grid">
        {methods.map((card) => (
          <div key={card.id} className={`pm-saved-card ${card.is_default ? 'default' : ''}`}>
            <div className="pm-saved-card-top">
              <div className="pm-card-brand-badge">
                <CreditCard size={16} />
                <strong>{card.card_brand}</strong>
              </div>
              {card.is_default && (
                <span className="pm-status-badge-mini completed">Primary Default</span>
              )}
            </div>

            <div className="pm-saved-card-number">
              <span>••••</span>
              <span>••••</span>
              <span>••••</span>
              <strong>{card.last4}</strong>
            </div>

            <div className="pm-saved-card-footer">
              <div className="pm-card-exp">
                <small>Expires</small>
                <span>
                  {card.exp_month}/{card.exp_year.toString().slice(-2)}
                </span>
              </div>

              <div className="pm-card-actions">
                {!card.is_default && (
                  <button
                    type="button"
                    className="pm-btn-link"
                    onClick={() => handleSetDefault(card.id)}
                  >
                    Set Default
                  </button>
                )}
                <button
                  type="button"
                  className="pm-btn-link danger"
                  onClick={() => setRemoveTarget(card)}
                >
                  Remove
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Add Card Modal */}
      {showAddModal && (
        <div className="pm-modal-overlay" onClick={() => setShowAddModal(false)} role="presentation">
          <div
            className="pm-confirm-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="add-card-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="pm-confirm-dialog-header">
              <div className="pm-avatar-circle" aria-hidden="true">
                <CreditCard size={18} />
              </div>
              <div>
                <h3 id="add-card-title">Add Payment Method</h3>
                <p>Add a new credit or corporate card for subscription billing.</p>
              </div>
              <button
                type="button"
                className="pm-modal-close"
                onClick={() => setShowAddModal(false)}
                aria-label="Close modal"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleAddSubmit} className="pm-form-stack" style={{ marginTop: 16 }}>
              <div className="pm-form-field">
                <label htmlFor="card_num">Card Number</label>
                <input
                  id="card_num"
                  type="text"
                  maxLength={19}
                  value={cardNumber}
                  onChange={(e) => setCardNumber(e.target.value)}
                  placeholder="4242 •••• •••• 4242"
                  required
                  autoFocus
                />
              </div>

              <div className="pm-form-grid-3">
                <div className="pm-form-field">
                  <label htmlFor="card_month">Exp Month</label>
                  <select
                    id="card_month"
                    value={expMonth}
                    onChange={(e) => setExpMonth(e.target.value)}
                  >
                    {Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, '0')).map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="pm-form-field">
                  <label htmlFor="card_year">Exp Year</label>
                  <select
                    id="card_year"
                    value={expYear}
                    onChange={(e) => setExpYear(e.target.value)}
                  >
                    {[2026, 2027, 2028, 2029, 2030, 2031, 2032].map((y) => (
                      <option key={y} value={y}>
                        {y}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="pm-form-field">
                  <label htmlFor="card_cvc">CVC</label>
                  <input
                    id="card_cvc"
                    type="password"
                    maxLength={4}
                    value={cvc}
                    onChange={(e) => setCvc(e.target.value)}
                    placeholder="•••"
                    required
                  />
                </div>
              </div>

              <div className="pm-confirm-dialog-actions">
                <button
                  type="button"
                  className="pm-secondary-btn"
                  onClick={() => setShowAddModal(false)}
                  disabled={adding}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="pm-primary-btn"
                  disabled={adding}
                >
                  {adding ? 'Securing Card...' : 'Add Card'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Remove Confirmation */}
      <ConfirmationDialog
        isOpen={Boolean(removeTarget)}
        title="Remove Payment Method?"
        message={`Are you sure you want to remove ${removeTarget?.card_brand} ending in ${removeTarget?.last4}?`}
        confirmLabel="Remove Card"
        isDanger={true}
        onConfirm={() => removeTarget && handleRemove(removeTarget.id)}
        onCancel={() => setRemoveTarget(null)}
      />
    </div>
  );
}

