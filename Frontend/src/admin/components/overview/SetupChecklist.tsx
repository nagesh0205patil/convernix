import React from 'react';
import { Check, ChevronRight } from 'lucide-react';
import type { OnboardingStepItem, AdminSection, AdminSubTab } from '../../types';

interface SetupChecklistProps {
  steps: OnboardingStepItem[];
  completionPercentage: number;
  onNavigate: (section: AdminSection, subTab?: AdminSubTab) => void;
}

export function SetupChecklist({ steps, completionPercentage, onNavigate }: SetupChecklistProps) {
  return (
    <div className="pm-admin-setup-card-pro" role="region" aria-label="Onboarding Progress">
      <div className="pm-admin-setup-top">
        <div>
          <span className="pm-admin-subtitle">Account Setup</span>
          <h2>Complete your account setup</h2>
        </div>
        <div className="pm-admin-progress-wrap">
          <strong>{completionPercentage}% completed</strong>
          <div
            className="pm-admin-progress-bar"
            role="progressbar"
            aria-valuenow={completionPercentage}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Account setup completion progress"
          >
            <span style={{ width: `${completionPercentage}%` }} />
          </div>
        </div>
      </div>

      <div className="pm-admin-setup-list">
        {steps.map((step) => {
          const isDone = step.status === 'completed';

          return (
            <div
              key={step.key}
              className={`pm-admin-step-pro ${isDone ? 'done' : ''}`}
            >
              <span className="pm-admin-step-icon" aria-hidden="true">
                {isDone ? <Check size={14} strokeWidth={2.5} /> : <ChevronRight size={14} />}
              </span>

              <div className="pm-admin-step-copy">
                <div className="pm-admin-step-row">
                  <strong>{step.name}</strong>
                  <span className={`pm-status-badge-mini ${isDone ? 'completed' : 'pending'}`}>
                    {isDone ? 'Completed' : 'Pending'}
                  </span>
                </div>
                <p>{step.desc}</p>
              </div>

              <button
                type="button"
                className={`pm-btn-step ${isDone ? 'secondary' : 'primary'}`}
                onClick={() => onNavigate(step.route, step.tab)}
              >
                {step.cta}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

