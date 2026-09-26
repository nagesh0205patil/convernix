import { useState } from 'react';
import {
  Check,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  MessageCircle,
  ChevronDown,
  ChevronsUpDown,
  HelpCircle,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { CTAButton, SectionHeader } from './UI';
import type { OpenModal } from './UI';
import './pricing.css';

interface PricingPlan {
  id: 'small' | 'mid' | 'large';
  name: string;
  tagline: string;
  badge?: string;
  monthlyPrice: number;
  annualPrice: number;
  numbers: string;
  users: string;
  campaigns: string;
  progressiveTitle: string;
  features: string[];
  ctaLabel: string;
}

const PLANS: PricingPlan[] = [
  {
    id: 'small',
    name: 'Basic',
    tagline: 'Ideal for local businesses, retail shops, and startups starting with official WhatsApp automation.',
    monthlyPrice: 2499,
    annualPrice: 1999,
    numbers: '1 Number',
    users: '3 Seats',
    campaigns: '5 / mo',
    progressiveTitle: "What's included",
    ctaLabel: 'Start 15-Day Free Trial',
    features: [
      '1 Official WhatsApp Business Number (Meta API)',
      'Up to 3 Agent seats with Shared Team Inbox',
      '5 Broadcast Campaigns per month',
      '5 GB Media & File Storage included',
      'Centralized Team Inbox with Live Chat',
      'Instant WhatsApp notifications on new leads',
      'Customer directory & 90-day conversation history',
      'Rich media support (Images, PDFs, Audio)',
      'Basic Conversation Analytics & CSV Export',
      'Standard Email Support',
    ],
  },
  {
    id: 'mid',
    name: 'Standard',
    tagline: 'Built for growing D2C brands, sales teams, and multi-department businesses.',
    badge: 'Most Popular',
    monthlyPrice: 6499,
    annualPrice: 5199,
    numbers: '5 Numbers',
    users: '15 Seats',
    campaigns: '50 / mo',
    progressiveTitle: 'Everything in Basic, plus',
    ctaLabel: 'Start 15-Day Free Trial',
    features: [
      'Up to 5 WhatsApp Business Numbers (Sales, Support)',
      'Up to 15 Agent seats included',
      '50 Broadcast Campaigns per month',
      '10 GB Media & File Storage included',
      'Smart Multi-Department Routing',
      'Role-based permissions (Admin, Agent, Viewer)',
      'Regional number access controls (India, US, Both)',
      'Message delivery & real-time read receipts tracking',
      'Advanced Analytics Dashboard & Trend Reporting',
      'Unlimited CSV Exports & 1-Year History',
      'Priority Email & Live Chat Support',
    ],
  },
  {
    id: 'large',
    name: 'Premium',
    tagline: 'Comprehensive WhatsApp infrastructure for multi-branch organizations and high-volume operations.',
    badge: 'Premium Scale',
    monthlyPrice: 8499,
    annualPrice: 6799,
    numbers: '25 Numbers',
    users: '100 Seats',
    campaigns: '500 / mo',
    progressiveTitle: 'Everything in Standard, plus',
    ctaLabel: 'Start 15-Day Free Trial',
    features: [
      'Up to 25 WhatsApp Business Numbers',
      'Up to 100 Agent seats included',
      '500 Broadcast Campaigns per month',
      '15 GB Media & File Storage included',
      'Unlimited custom departments & routing rules',
      'Complete multi-tenant workspace isolation',
      'Meta WABA Setup & Green Tick verification guidance',
      'High-throughput Cloud API & Webhook processing',
      'Unlimited data retention & audit logging',
      '99.99% Uptime SLA & Dedicated Account Lead',
      '24/7 Priority Emergency Support',
    ],
  },
];

interface ComparisonRow {
  name: string;
  small: boolean | string;
  mid: boolean | string;
  large: boolean | string;
}

interface ComparisonCategory {
  id: string;
  title: string;
  rows: ComparisonRow[];
}

const COMPARISON_CATEGORIES: ComparisonCategory[] = [
  {
    id: 'essentials',
    title: 'The Essentials',
    rows: [
      { name: 'Official WhatsApp Business Numbers', small: '1 Number', mid: '5 Numbers', large: '25 Numbers' },
      { name: 'Agent / Team Seats', small: '3 Seats', mid: '15 Seats', large: '100 Seats' },
      { name: 'Monthly Broadcast Campaigns', small: '5 / month', mid: '50 / month', large: '500 / month' },
      { name: 'Message History Retention', small: '90 Days', mid: '1 Year', large: 'Unlimited' },
      { name: 'Media & File Storage', small: '5 GB', mid: '10 GB', large: '15 GB' },
      { name: '15-Day Full-Feature Free Trial', small: true, mid: true, large: true },
    ],
  },
  {
    id: 'inbox',
    title: 'Shared Team Inbox',
    rows: [
      { name: 'Live Multi-Agent Collaborative Inbox', small: true, mid: true, large: true },
      { name: 'Contact & Customer Directory', small: true, mid: true, large: true },
      { name: 'Rich Media Attachments (Images, PDFs, Audio, Video)', small: true, mid: true, large: true },
      { name: 'Delivery Status & Real-Time Read Receipts (Blue Ticks)', small: true, mid: true, large: true },
      { name: 'Global E.164 Phone Number Validation', small: true, mid: true, large: true },
      { name: 'Internal Agent Notes & Team Mentions', small: false, mid: true, large: true },
    ],
  },
  {
    id: 'automation',
    title: 'Automation & Routing',
    rows: [
      { name: 'Instant New-Lead WhatsApp Alerts', small: true, mid: true, large: true },
      { name: 'Multi-Department Routing (Sales, Support, Accounts)', small: false, mid: true, large: true },
      { name: 'Regional Access Controls (India, US, Both)', small: false, mid: true, large: true },
      { name: 'Real-Time Webhook Event Dispatching', small: false, mid: true, large: true },
      { name: 'Custom Auto-Assignment & Round Robin', small: false, mid: false, large: true },
    ],
  },
  {
    id: 'campaigns',
    title: 'Campaigns & Broadcasting',
    rows: [
      { name: 'Meta Pre-Approved Template Messaging', small: true, mid: true, large: true },
      { name: 'Dynamic Variable Personalization ({{1}}, {{2}})', small: true, mid: true, large: true },
      { name: 'Scheduled Broadcast Campaigns', small: false, mid: true, large: true },
      { name: 'Audience Segmentation & Custom Tag Filters', small: false, mid: true, large: true },
      { name: 'High-Throughput Bulk Dispatch Engine', small: false, mid: false, large: true },
    ],
  },
  {
    id: 'analytics',
    title: 'Analytics & Reporting',
    rows: [
      { name: 'Real-Time Message Traffic Analytics', small: 'Basic (7-Day)', mid: 'Advanced (90-Day)', large: 'Full Custom' },
      { name: 'Campaign Delivery & Read Rate Performance', small: true, mid: true, large: true },
      { name: 'Agent Workload & Response Time Metrics', small: false, mid: true, large: true },
      { name: 'CSV & Excel Data Export', small: '10 / month', mid: 'Unlimited', large: 'Unlimited' },
      { name: 'Custom BI & Automated Data Feeds', small: false, mid: false, large: true },
    ],
  },
  {
    id: 'security',
    title: 'Security & Administration',
    rows: [
      { name: 'Role-Based Access Control (RBAC)', small: 'Owner Only', mid: 'Admin, Agent, Viewer', large: 'Granular Custom RBAC' },
      { name: 'Complete Multi-Tenant Database Isolation', small: true, mid: true, large: true },
      { name: 'Audit Logs & Activity History', small: false, mid: true, large: true },
      { name: 'Meta WABA Direct Setup Assistance', small: 'Self-Serve + Docs', mid: 'Guided Onboarding', large: 'Dedicated Account Lead' },
      { name: 'Uptime Service Level Agreement (SLA)', small: '99.5%', mid: '99.9%', large: '99.99% Guaranteed' },
      { name: 'Technical Support Channels', small: 'Standard Email', mid: 'Priority Email & Chat', large: '24/7 Dedicated Slack/Phone' },
    ],
  },
];

const FAQS = [
  {
    q: 'How does the 15-day free trial work?',
    a: 'Every new workspace gets 15 days of full access to all features of your selected plan. No credit card is required to sign up. You can connect your official WhatsApp number, test the team inbox, and launch campaigns risk-free.',
  },
  {
    q: 'What are Meta WhatsApp conversation charges?',
    a: 'Meta charges per 24-hour conversation category (Marketing, Utility, Authentication, and Service). Convernix connects directly to your Meta Cloud API and passes these charges with 0% markup. You pay Meta directly at wholesale rates.',
  },
  {
    q: 'Can I upgrade or downgrade my tier at any time?',
    a: 'Yes, you can upgrade, downgrade, or switch billing cycles (Monthly vs Annual) at any time from your workspace settings. Upgrades take effect immediately with prorated billing.',
  },
  {
    q: 'Do I need an official WhatsApp Business Account (WABA)?',
    a: 'Yes, Convernix operates exclusively on the official Meta WhatsApp Business Cloud API. We guide you through the instant Facebook Business Manager embedded signup in under 10 minutes without third-party middleman delays.',
  },
];

export default function PricingPage({
  openModal,
  onNavigate,
}: {
  openModal: OpenModal;
  onNavigate?: (page: 'home' | 'pricing', hash?: string) => void;
}) {
  const [annual, setAnnual] = useState(false);
  const [openCategories, setOpenCategories] = useState<Record<string, boolean>>({
    essentials: true,
    inbox: true,
    automation: true,
    campaigns: true,
    analytics: true,
    security: true,
  });

  const formatINR = (val: number) =>
    new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(val);

  const toggleCategory = (id: string) => {
    setOpenCategories((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const allOpen = Object.values(openCategories).every(Boolean);
  const toggleAll = () => {
    const nextState = !allOpen;
    const updated: Record<string, boolean> = {};
    COMPARISON_CATEGORIES.forEach((cat) => {
      updated[cat.id] = nextState;
    });
    setOpenCategories(updated);
  };

  const renderTableCell = (val: boolean | string) => {
    if (typeof val === 'boolean') {
      return val ? (
        <span className="comp-tick" title="Included">
          <Check size={13} />
        </span>
      ) : (
        <span className="comp-dash" title="Not included">
          —
        </span>
      );
    }
    return <span className="comp-limit-badge">{val}</span>;
  };

  return (
    <div className="pricing-page-wrapper" id="pricing" aria-label="Subscription Pricing Page">
      <div className="container">
        {/* Breadcrumb / Back to Home navigation */}
        <div className="pricing-page-breadcrumb">
          <button
            type="button"
            className="pricing-breadcrumb-btn"
            onClick={() => onNavigate?.('home')}
          >
            <ArrowLeft size={14} />
            <span>Back to Home</span>
          </button>
          <span className="pricing-breadcrumb-sep">/</span>
          <span className="pricing-breadcrumb-current">Plans & Pricing</span>
        </div>

        {/* Section Header */}
        <div className="pricing-header-wrap">
          <div className="pricing-hero-badge">
            <Sparkles size={14} />
            <span>15-day free trial. No credit card required.</span>
          </div>

          <SectionHeader
            eyebrow="TRANSPARENT & PREDICTABLE PRICING"
            title={
              <>
                Simple plans in INR.<br />
                <span className="muted-heading">Scale as your conversations grow.</span>
              </>
            }
            description="Choose the right workspace capacity for your team. All plans connect directly to the official Meta WhatsApp Business Cloud API with zero platform markup."
            centered
          />

          {/* Billing Cycle Toggle */}
          <div className="pricing-toggle-container">
            <div className="pricing-toggle-pill" role="group" aria-label="Billing frequency toggle">
              <button
                type="button"
                className={`pricing-toggle-btn ${!annual ? 'active' : ''}`}
                onClick={() => setAnnual(false)}
                aria-pressed={!annual}
              >
                Monthly Billing
              </button>
              <button
                type="button"
                className={`pricing-toggle-btn ${annual ? 'active' : ''}`}
                onClick={() => setAnnual(true)}
                aria-pressed={annual}
              >
                Annual Billing
              </button>
            </div>
            <span className="pricing-save-badge">
              <Sparkles size={13} />
              Save 20%
            </span>
          </div>
        </div>

        {/* Pricing Cards Grid */}
        <div className="pricing-grid">
          {PLANS.map((plan) => {
            const price = annual ? plan.annualPrice : plan.monthlyPrice;
            const isFeatured = plan.id === 'mid';

            return (
              <div
                key={plan.id}
                className={`pricing-card ${isFeatured ? 'featured' : ''}`}
              >
                {plan.badge && (
                  <div className="pricing-popular-pill">
                    <Sparkles size={12} />
                    {plan.badge}
                  </div>
                )}

                <div className="pricing-card-top">
                  <div className="pricing-tier-name">
                    <span>{plan.name}</span>
                    <span className="pricing-tier-pill">{plan.id}</span>
                  </div>
                  <p className="pricing-tier-desc">{plan.tagline}</p>

                  <div className="pricing-price-block">
                    <span className="pricing-currency">₹</span>
                    <span className="pricing-figure">{formatINR(price)}</span>
                    <span className="pricing-cadence">/ month</span>
                  </div>
                  <div className="pricing-subtext">
                    {annual
                      ? `Billed annually (₹${formatINR(price * 12)}/yr) · +GST`
                      : 'Billed monthly · +GST'}
                  </div>
                </div>

                {/* Quota Highlights */}
                <div className="pricing-quota-row">
                  <div className="pricing-quota-item">
                    <strong>{plan.numbers}</strong>
                    <span>Numbers</span>
                  </div>
                  <div className="pricing-quota-item">
                    <strong>{plan.users}</strong>
                    <span>Seats</span>
                  </div>
                  <div className="pricing-quota-item">
                    <strong>{plan.campaigns}</strong>
                    <span>Campaigns</span>
                  </div>
                </div>

                {/* CTA Action */}
                <CTAButton
                  className="pricing-cta-btn"
                  secondary={!isFeatured}
                  onClick={() => openModal('signup', plan.id)}
                >
                  {plan.ctaLabel}
                  <ArrowRight size={15} />
                </CTAButton>

                {/* Feature Checklist with Progressive Disclosure Title */}
                <div className="pricing-features-title">
                  {plan.progressiveTitle}
                  <span />
                </div>
                <ul className="pricing-features-list">
                  {plan.features.map((feat, idx) => (
                    <li
                      key={idx}
                      className={`pricing-feature-item ${idx < 3 ? 'highlight' : ''}`}
                    >
                      <Check size={15} />
                      <span>{feat}</span>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>

        {/* ==========================================================
            ZOHO PROJECTS-STYLE FEATURE COMPARISON TABLE
            ========================================================== */}
        <div className="comp-table-section">
          <div className="comp-table-header">
            <div>
              <h3>Compare plans and features</h3>
              <p>Comprehensive side-by-side comparison across all tiers and infrastructure limits.</p>
            </div>
            <button
              type="button"
              className="comp-table-expand-all"
              onClick={toggleAll}
              aria-label={allOpen ? 'Collapse all comparison categories' : 'Expand all comparison categories'}
            >
              <ChevronsUpDown size={14} />
              {allOpen ? 'Collapse All' : 'Expand All'}
            </button>
          </div>

          <div className="comp-table-scroll-wrap">
            <table className="comp-table">
              <thead>
                <tr className="comp-thead-row">
                  <th scope="col">Features & Capabilities</th>
                  <th scope="col">
                    <span className="comp-th-badge">Basic</span>
                    <span className="comp-th-price">
                      ₹{formatINR(annual ? 1999 : 2499)}/mo
                    </span>
                    <CTAButton
                      secondary
                      className="comp-th-btn"
                      onClick={() => openModal('signup', 'small')}
                    >
                      Try for Free
                    </CTAButton>
                  </th>
                  <th scope="col">
                    <span className="comp-th-badge">Standard</span>
                    <span className="comp-th-price">
                      ₹{formatINR(annual ? 5199 : 6499)}/mo
                    </span>
                    <CTAButton
                      className="comp-th-btn"
                      onClick={() => openModal('signup', 'mid')}
                    >
                      Try for Free
                    </CTAButton>
                  </th>
                  <th scope="col">
                    <span className="comp-th-badge">Premium</span>
                    <span className="comp-th-price">
                      ₹{formatINR(annual ? 6799 : 8499)}/mo
                    </span>
                    <CTAButton
                      secondary
                      className="comp-th-btn"
                      onClick={() => openModal('signup', 'large')}
                    >
                      Try for Free
                    </CTAButton>
                  </th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON_CATEGORIES.map((cat) => {
                  const isOpen = !!openCategories[cat.id];
                  return (
                    <tr key={`cat-${cat.id}`} style={{ display: 'contents' }}>
                      <td colSpan={4} style={{ padding: 0 }}>
                        <div
                          className={`comp-category-heading ${isOpen ? 'open' : ''}`}
                          onClick={() => toggleCategory(cat.id)}
                          role="button"
                          tabIndex={0}
                          aria-expanded={isOpen}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              toggleCategory(cat.id);
                            }
                          }}
                        >
                          <span>{cat.title}</span>
                          <ChevronDown size={15} />
                        </div>
                      </td>
                      {isOpen &&
                        cat.rows.map((row, rIdx) => (
                          <tr key={`${cat.id}-${rIdx}`} className="comp-row">
                            <td>{row.name}</td>
                            <td>{renderTableCell(row.small)}</td>
                            <td>{renderTableCell(row.mid)}</td>
                            <td>{renderTableCell(row.large)}</td>
                          </tr>
                        ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Meta Cloud API Transparency Strip */}
        <div className="pricing-transparency-banner">
          <div className="pricing-transparency-copy">
            <div className="pricing-transparency-icon">
              <MessageCircle size={22} />
            </div>
            <div>
              <h3>Direct Meta Cloud API Pricing Transparency</h3>
              <p>
                Convernix charges strictly for multi-tenant software, agent workspaces, and campaign
                orchestration. Meta conversation fees (Marketing, Utility, Authentication, and Service)
                are billed directly to you by Meta at <strong>0% markup</strong>. You retain 100% direct
                ownership and verification of your Meta WhatsApp Business Account (WABA).
              </p>
            </div>
          </div>
          <CTAButton
            secondary
            className="pricing-transparency-btn"
            onClick={() => openModal('demo', 'Meta API Billing & Setup Guidance')}
          >
            Ask About Meta Billing <ArrowRight size={14} />
          </CTAButton>
        </div>

        {/* Pricing FAQs */}
        <div className="pricing-faq-section">
          <SectionHeader
            eyebrow="FREQUENTLY ASKED QUESTIONS"
            title="Everything you need to know about pricing"
            description="Got questions about trial periods, Meta billing, or enterprise onboarding? We're here to help."
            centered
          />
          <div className="pricing-faq-grid">
            {FAQS.map((faq, idx) => (
              <div key={idx} className="pricing-faq-card">
                <h4>
                  <HelpCircle
                    size={15}
                    style={{
                      display: 'inline',
                      verticalAlign: 'text-bottom',
                      marginRight: 6,
                      color: '#907de8',
                    }}
                  />
                  {faq.q}
                </h4>
                <p>{faq.a}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Dedicated Bottom Enterprise & Trial CTA */}
        <div className="pricing-bottom-banner">
          <div className="pricing-bottom-content">
            <span className="eyebrow"><Sparkles size={14} /> READY TO GET STARTED?</span>
            <h3>Transform your team’s WhatsApp communications today.</h3>
            <p>
              Join high-performing teams automating sales, support, and broadcasting on the official Meta Cloud API.
            </p>
            <div className="pricing-bottom-actions">
              <CTAButton onClick={() => openModal('signup', 'mid')}>
                Start 15-Day Free Trial <ArrowRight size={16} />
              </CTAButton>
              <CTAButton secondary onClick={() => openModal('demo', 'Custom Enterprise Requirements')}>
                Talk to Solutions Engineering
              </CTAButton>
            </div>
            <div className="pricing-bottom-perks">
              <span><ShieldCheck size={14} /> ISO 27001 & SOC 2 Type II Aligned</span>
              <span><Zap size={14} /> Instant Setup via Embedded Signup</span>
              <span><MessageCircle size={14} /> 100% Official Meta Cloud API</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

