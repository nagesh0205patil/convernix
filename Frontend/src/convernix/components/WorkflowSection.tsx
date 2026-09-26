import { useEffect, useRef, useState } from 'react';
import {
  ArrowDown, ArrowRight, Check, ChevronDown, CircleHelp, Clock3,
  GitBranch, Headphones, MessageCircle, MessageSquare, Play,
  ReceiptText, Route, Settings2, ShoppingBag, Sparkles, Users, Zap,
} from 'lucide-react';
import './workflow.css';

const routes = [
  { id: 'sales', label: 'Sales', department: 'Sales Department', name: 'Arjun', initials: 'AK', icon: ShoppingBag, description: 'New enquiries reach your sales team, ready for a personal follow-up.' },
  { id: 'support', label: 'Support', department: 'Customer Support', name: 'Maya', initials: 'MS', icon: Headphones, description: 'Customer questions reach the support team with the full conversation attached.' },
  { id: 'billing', label: 'Billing', department: 'Finance Team', name: 'Priya', initials: 'PS', icon: ReceiptText, description: 'Invoice and payment questions go straight to your finance team.' },
  { id: 'technical', label: 'Technical', department: 'Technical Team', name: 'Rohan', initials: 'RM', icon: Settings2, description: 'Technical questions reach the people with the right expertise.' },
] as const;

const blocks = ['Send Message', 'Ask Question', 'Menu Options', 'Condition', 'Route Department', 'Assign Agent', 'Apply Tag', 'Wait', 'Webhook', 'Close Conversation'];

export default function WorkflowSection() {
  const [selected, setSelected] = useState<(typeof routes)[number]['id']>('billing');
  const [stage, setStage] = useState(-1);
  const [running, setRunning] = useState(false);
  const timeouts = useRef<number[]>([]);
  const route = routes.find((item) => item.id === selected)!;
  const RouteIcon = route.icon;

  useEffect(() => () => timeouts.current.forEach(window.clearTimeout), []);

  function selectRoute(id: (typeof routes)[number]['id']) {
    timeouts.current.forEach(window.clearTimeout);
    timeouts.current = [];
    setSelected(id);
    setStage(-1);
    setRunning(false);
  }

  function previewFlow() {
    timeouts.current.forEach(window.clearTimeout);
    timeouts.current = [];
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setStage(4);
      return;
    }
    setRunning(true);
    setStage(0);
    for (let nextStage = 1; nextStage <= 4; nextStage += 1) {
      timeouts.current.push(window.setTimeout(() => {
        setStage(nextStage);
        if (nextStage === 4) setRunning(false);
      }, nextStage * 520));
    }
  }

  return (
    <section id="automation" className="section container wf-section" aria-labelledby="wf-heading">
      <div className="wf-copy">
        <div className="wf-eyebrow"><GitBranch size={14} aria-hidden="true" /> WORKFLOW AUTOMATION</div>
        <h2 id="wf-heading">The right conversation.<br /><span>The right person.</span></h2>
        <p className="wf-description">Design customer journeys without changing your WhatsApp number. A friendly welcome, a few simple rules, and every message finds its way.</p>
        <ul className="wf-features">
          <li><span className="wf-feature-icon"><Route size={17} aria-hidden="true" /></span><span><strong>Route with purpose</strong><small>Connect customers to the right department.</small></span></li>
          <li><span className="wf-feature-icon"><Users size={17} aria-hidden="true" /></span><span><strong>Give every chat an owner</strong><small>Assign an agent with all the context intact.</small></span></li>
          <li><span className="wf-feature-icon"><Zap size={17} aria-hidden="true" /></span><span><strong>Build it your way</strong><small>Configure your flow with simple, reusable blocks.</small></span></li>
        </ul>
        <button className="wf-preview" type="button" onClick={previewFlow} disabled={running}>
          {running ? <Clock3 size={15} aria-hidden="true" /> : <Play size={14} aria-hidden="true" />}
          {running ? 'Running preview…' : 'Preview the workflow'}
          <ArrowRight size={16} aria-hidden="true" />
        </button>
      </div>

      <div className="wf-builder" role="group" aria-label="Interactive example of a message routing workflow">
        <div className="wf-toolbar">
          <span className="wf-toolbar-title"><GitBranch size={15} aria-hidden="true" /> Customer welcome <ChevronDown size={13} aria-hidden="true" /></span>
          <span className="wf-example-label">DEMO WORKFLOW</span>
        </div>
        <div className="wf-canvas">
          <div className={`wf-node wf-trigger ${stage >= 0 ? 'wf-traced' : ''}`}>
            <span className="wf-whatsapp"><MessageCircle size={19} aria-hidden="true" /></span>
            <span><small>TRIGGER</small><strong>Incoming WhatsApp message</strong></span>
            {stage >= 0 && <Check className="wf-node-check" size={14} aria-hidden="true" />}
          </div>
          <div className={`wf-connector ${stage >= 1 ? 'wf-connector-active' : ''}`} aria-hidden="true"><ArrowDown size={12} /></div>
          <div className={`wf-node wf-welcome ${stage >= 1 ? 'wf-traced' : ''}`}>
            <div className="wf-node-heading"><span className="wf-purple-icon"><MessageSquare size={15} aria-hidden="true" /></span><strong>Send a welcome message</strong><span className="wf-step-number">01</span></div>
            <div className="wf-message">Hi there! 👋 What can we help you with?</div>
            <div className="wf-question-caption"><CircleHelp size={11} aria-hidden="true" /> Wait for a customer selection</div>
          </div>
          <div className={`wf-connector wf-before-branches ${stage >= 2 ? 'wf-connector-active' : ''}`} aria-hidden="true"><span /></div>
          <div className="wf-branches" aria-label="Choose a sample customer request">
            {routes.map((item) => {
              const Icon = item.icon;
              return <button key={item.id} type="button" aria-pressed={selected === item.id} onClick={() => selectRoute(item.id)} className={`wf-branch ${selected === item.id ? 'wf-selected' : ''} ${selected === item.id && stage >= 2 ? 'wf-branch-traced' : ''}`}>
                <Icon size={15} aria-hidden="true" /><span>{item.label}</span>
              </button>;
            })}
          </div>
          <div className={`wf-connector wf-after-branches ${stage >= 3 ? 'wf-connector-active' : ''}`} aria-hidden="true"><ArrowDown size={12} /></div>
          <div className={`wf-node wf-assignment ${stage >= 3 ? 'wf-traced' : ''}`}>
            <div className="wf-node-heading"><span className="wf-purple-icon"><RouteIcon size={15} aria-hidden="true" /></span><span className="wf-department"><small>ROUTE TO DEPARTMENT</small><strong>{route.department}</strong></span><span className="wf-step-number">02</span></div>
            <div className={`wf-agent ${stage >= 4 ? 'wf-agent-assigned' : ''}`}>
              <span className="wf-avatar">{route.initials}</span>
              <span><strong>{route.name}</strong><small>{stage >= 4 ? 'Conversation assigned' : 'Available agent'}</small></span>
              {stage >= 4 ? <Check size={14} aria-hidden="true" /> : <Users size={14} aria-hidden="true" />}
            </div>
          </div>
          <div className="wf-route-description" aria-live="polite" aria-atomic="true">
            {running ? <><Sparkles size={13} aria-hidden="true" /><span>Following your {route.label.toLowerCase()} route…</span></> : stage === 4 ? <><Check size={13} aria-hidden="true" /><span>Preview complete. Assigned to {route.name} in {route.department}.</span></> : <><GitBranch size={13} aria-hidden="true" /><span>{route.description}</span></>}
          </div>
        </div>
        <div className="wf-palette">
          <div className="wf-palette-caption"><span className="wf-palette-dot" /> YOUR BUILDING BLOCKS</div>
          <div className="wf-blocks">{blocks.map((block) => <span key={block}>{block}</span>)}</div>
        </div>
      </div>
    </section>
  );
}
