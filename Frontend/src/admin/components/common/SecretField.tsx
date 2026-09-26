import React, { useState } from 'react';
import { Eye, EyeOff, Copy, Check, RefreshCw } from 'lucide-react';

interface SecretFieldProps {
  label: string;
  value?: string;
  hasValue?: boolean;
  onReplace?: (newValue: string) => void;
  maskedPlaceholder?: string;
}

export function SecretField({
  label,
  value,
  hasValue = true,
  onReplace,
  maskedPlaceholder = '••••••••••••••••••••••••••••••••',
}: SecretFieldProps) {
  const [revealed, setRevealed] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isReplacing, setIsReplacing] = useState(false);
  const [replacementValue, setReplacementValue] = useState('');

  const handleCopy = async () => {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const handleSaveReplacement = () => {
    if (replacementValue && onReplace) {
      onReplace(replacementValue);
      setIsReplacing(false);
      setReplacementValue('');
    }
  };

  return (
    <div className="pm-secret-field">
      <div className="pm-secret-label-row">
        <span className="pm-secret-label">{label}</span>
        <span className="pm-secret-badge">Encrypted Vault</span>
      </div>

      {!isReplacing ? (
        <div className="pm-secret-input-row">
          <div className="pm-secret-display" aria-live="polite">
            {revealed && value ? value : maskedPlaceholder}
          </div>

          <div className="pm-secret-actions">
            {value && (
              <button
                type="button"
                className="pm-secret-btn"
                onClick={() => setRevealed(!revealed)}
                title={revealed ? 'Hide secret' : 'Reveal secret'}
                aria-label={revealed ? `Hide ${label}` : `Reveal ${label}`}
              >
                {revealed ? <EyeOff size={14} /> : <Eye size={14} />}
                <span>{revealed ? 'Hide' : 'Reveal'}</span>
              </button>
            )}

            {value && (
              <button
                type="button"
                className="pm-secret-btn"
                onClick={handleCopy}
                title="Copy to clipboard"
                aria-label={`Copy ${label} to clipboard`}
              >
                {copied ? <Check size={14} color="#52bb89" /> : <Copy size={14} />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            )}

            {onReplace && (
              <button
                type="button"
                className="pm-secret-btn"
                onClick={() => setIsReplacing(true)}
                title="Replace credential"
                aria-label={`Replace ${label}`}
              >
                <RefreshCw size={14} />
                <span>Replace</span>
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="pm-secret-replace-row">
          <input
            type="password"
            value={replacementValue}
            onChange={(e) => setReplacementValue(e.target.value)}
            placeholder={`Enter new ${label.toLowerCase()}...`}
            className="pm-secret-replace-input"
            autoFocus
          />
          <button
            type="button"
            className="pm-primary-btn small"
            onClick={handleSaveReplacement}
            disabled={!replacementValue.trim()}
          >
            Save
          </button>
          <button
            type="button"
            className="pm-secondary-btn small"
            onClick={() => {
              setIsReplacing(false);
              setReplacementValue('');
            }}
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}

