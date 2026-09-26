import { useId, useState } from 'react';
import { ArrowDownLeft, ArrowRight, ArrowUpRight, BarChart3, Check, CheckCheck, ChevronDown, Clock3, FileCheck2, History, LockKeyhole, MessageSquare, MoreHorizontal, ShieldCheck, Sparkles, UserRound, Users, Workflow } from 'lucide-react';
import './feature-showcases.css';

const roleContent = {
  Agents: {
    heading: 'Great conversations.\nA team effort.',
    copy: 'Give every agent the context to help. Work together behind the scenes, then show up as one team for your customers.',
    benefits: ['A clear owner for every conversation', 'Private notes that keep everyone aligned', 'Smooth transfers between departments', 'The full conversation history, always there'],
    panelTitle: 'Conversation details',
    panelSubtitle: 'Everything you need, in one place',
    rows: [['Assigned to', 'Maya Patel'], ['Department', 'Customer success'], ['Priority', 'Normal']],
    note: 'Customer is upgrading to the team plan. Please share the onboarding guide.',
    noteAuthor: 'Alex Morgan',
    event: 'Maya accepted this conversation',
  },
  Managers: {
    heading: 'An aligned team.\nA clearer overview.',
    copy: 'Keep an eye on the queue and support your people. See who owns what and move conversations to the right team.',
    benefits: ['A live view of department queues', 'Balance ownership across your team', 'Coach agents with private internal notes', 'Follow every transfer and handoff'],
    panelTitle: 'Team overview',
    panelSubtitle: 'Customer success · sample workspace',
    rows: [['Open conversations', '24'], ['Available agents', '6'], ['Unassigned', '3']],
    note: 'Maya is covering onboarding today. Route new setup questions to her.',
    noteAuthor: 'Jordan Lee',
    event: 'Billing conversation transferred to Alex',
  },
  Administrators: {
    heading: 'The right access.\nFrom the start.',
    copy: 'Organize your workspace around the way your business works, with clear departments, permissions, and ownership.',
    benefits: ['Manage team members in one workspace', 'Set roles and department access', 'Keep conversation ownership organized', 'Review the history behind every handoff'],
    panelTitle: 'Workspace settings',
    panelSubtitle: 'Acme workspace · sample configuration',
    rows: [['Departments', '4 active'], ['Team members', '18'], ['Default routing', 'Unassigned queue']],
    note: 'The billing team now has its own department. Updated ownership rules are ready.',
    noteAuthor: 'Sam Wilson',
    event: 'Billing department access updated',
  },
  'Business owners': {
    heading: 'See the big picture.\nStay close to customers.',
    copy: 'Bring your teams into one connected view. Understand the workload and see how conversations move across your business.',
    benefits: ['See conversations across departments', 'Understand open and resolved workloads', 'Keep customer context as teams grow', 'Follow team activity and ownership'],
    panelTitle: 'Business overview',
    panelSubtitle: 'All departments · illustrative data',
    rows: [['Conversations today', '128'], ['Resolved today', '96'], ['Teams connected', '4']],
    note: 'Support and sales are sharing customer context for this week’s onboarding.',
    noteAuthor: 'Jordan Lee',
    event: 'Weekly department summary is available',
  },
};

type TeamRole = keyof typeof roleContent;

export function TeamSection() {
  const [role, setRole] = useState<TeamRole>('Agents');
  const content = roleContent[role];

  return (
    <section className="section fs-team-section" id="collaboration" aria-labelledby="fs-team-heading">
      <div className="container">
        <div className="fs-role-switch" aria-label="Choose your team role">
          {(Object.keys(roleContent) as TeamRole[]).map((item) => (
            <button type="button" key={item} aria-pressed={role === item} onClick={() => setRole(item)}>{item}</button>
          ))}
        </div>
        <div className="fs-split fs-team-split">
          <div className="fs-copy">
            <span className="fs-eyebrow"><Users size={14} aria-hidden="true" /> BUILT FOR YOUR WHOLE TEAM</span>
            <h2 id="fs-team-heading">{content.heading.split('\n').map((line, index) => <span key={line} className={index === 1 ? 'fs-muted-heading' : undefined}>{line}</span>)}</h2>
            <p>{content.copy}</p>
            <ul className="fs-benefits">
              {content.benefits.map((benefit) => <li key={benefit}><Check size={15} aria-hidden="true" />{benefit}</li>)}
            </ul>
          </div>
          <div className="fs-team-visual">
            <div className="fs-team-halo" />
            <div className="fs-team-panel">
              <div className="fs-panel-heading"><span className="fs-square-icon"><UserRound size={17} /></span><div><strong>{content.panelTitle}</strong><span>{content.panelSubtitle}</span></div><MoreHorizontal size={19} className="fs-panel-more" aria-hidden="true" /></div>
              <div className="fs-detail-rows">{content.rows.map(([label, value]) => <div className="fs-detail-row" key={label}><span>{label}</span><strong>{label === 'Assigned to' && <span className="fs-avatar fs-avatar-small">MP</span>}{value}</strong></div>)}</div>
              <div className="fs-panel-rule" />
              <div className="fs-internal-note"><span className="fs-note-label"><LockKeyhole size={12} />Internal note<span>Only your team</span></span><p>{content.note}</p><div className="fs-note-author"><span className="fs-avatar fs-avatar-tiny">{content.noteAuthor.split(' ').map((name) => name[0]).join('')}</span>{content.noteAuthor}<span>Just now</span></div></div>
              <div className="fs-panel-history"><History size={13} /><span>{content.event}</span><span>10:42</span></div>
            </div>
            <div className="fs-team-float"><span className="fs-float-icon"><Workflow size={17} /></span><div><strong>Context comes with you.</strong><span>Every note. Every handoff. Every time.</span></div><Check size={15} /></div>
          </div>
        </div>
      </div>
    </section>
  );
}

const analyticsData = {
  '7 days': {
    values: ['1,284', '126', '1,158', '4m 12s'],
    points: '0,102 35,87 70,96 105,62 140,71 175,34 210,49 245,24 280,40 315,15 350,30 385,9 420,23',
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    departments: [{ name: 'Support', amount: 682, width: 85 }, { name: 'Sales', amount: 384, width: 58 }, { name: 'Billing', amount: 218, width: 34 }],
  },
  '30 days': {
    values: ['5,426', '318', '5,108', '4m 38s'],
    points: '0,96 35,80 70,91 105,74 140,87 175,47 210,62 245,34 280,54 315,26 350,43 385,16 420,6',
    labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
    departments: [{ name: 'Support', amount: 2890, width: 92 }, { name: 'Sales', amount: 1618, width: 63 }, { name: 'Billing', amount: 918, width: 41 }],
  },
};

type AnalyticsRange = keyof typeof analyticsData;

export function AnalyticsSection() {
  const [range, setRange] = useState<AnalyticsRange>('7 days');
  const gradientId = useId();
  const data = analyticsData[range];

  return (
    <section className="section fs-analytics-section" id="analytics" aria-labelledby="fs-analytics-heading">
      <div className="container fs-split fs-analytics-split">
        <div className="fs-analytics-visual">
          <div className="fs-dashboard">
            <div className="fs-dashboard-top"><div><BarChart3 size={15} /><strong>Conversation analytics</strong></div><span className="fs-sample-label">Illustrative data</span></div>
            <div className="fs-dashboard-subhead"><span>Understand your conversations</span><div className="fs-range-switch" aria-label="Analytics date range">{(Object.keys(analyticsData) as AnalyticsRange[]).map((item) => <button type="button" key={item} aria-pressed={range === item} onClick={() => setRange(item)}>{item}</button>)}</div></div>
            <div className="fs-metrics" aria-live="polite">{['Total', 'Open', 'Resolved', 'Avg. response'].map((label, i) => <div key={label}><span>{label}</span><strong>{data.values[i]}</strong></div>)}</div>
            <div className="fs-chart-top"><strong>Conversation volume</strong><span><i />Conversations</span></div>
            <div className="fs-line-chart" role="img" aria-label={`Illustrative conversation volume across ${range}. ${data.values[0]} total conversations.`}>
              <div className="fs-chart-grid"><span>400</span><span>200</span><span>0</span></div>
              <svg viewBox="0 0 420 130" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#a49cff" stopOpacity="0.23" /><stop offset="100%" stopColor="#a49cff" stopOpacity="0" /></linearGradient></defs><polygon points={`0,130 ${data.points} 420,130`} fill={`url(#${gradientId})`} /><polyline points={data.points} fill="none" stroke="#a49cff" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" /></svg>
            </div>
            <div className="fs-chart-labels">{data.labels.map((label) => <span key={label}>{label}</span>)}</div>
            <div className="fs-departments"><div className="fs-chart-top"><strong>Department performance</strong><span>Conversations handled</span></div>{data.departments.map((department) => <div className="fs-department" key={department.name}><span>{department.name}</span><div className="fs-bar-track"><div style={{ width: `${department.width}%` }} /></div><strong>{department.amount.toLocaleString('en-US')}</strong></div>)}</div>
          </div>
        </div>
        <div className="fs-copy fs-analytics-copy">
          <span className="fs-eyebrow"><BarChart3 size={14} aria-hidden="true" /> CLARITY, AT A GLANCE</span>
          <h2 id="fs-analytics-heading"><span>Less guesswork.</span><span className="fs-muted-heading">More perspective.</span></h2>
          <p>Turn everyday conversations into a clearer picture of your business. See what’s coming in, what’s getting resolved, and where your team needs support.</p>
          <div className="fs-analytics-points"><div><span className="fs-mini-icon"><MessageSquare size={17} /></span><div><strong>Know the state of your inbox</strong><p>Track total, open, and resolved conversations.</p></div></div><div><span className="fs-mini-icon"><Clock3 size={17} /></span><div><strong>Understand your team’s workload</strong><p>Follow response times and department activity.</p></div></div></div>
          <a className="fs-text-link" href="#demo">Get a closer look <ArrowRight size={15} /></a>
        </div>
      </div>
    </section>
  );
}

export function TemplatesSection() {
  const [template, setTemplate] = useState('order');
  const [name, setName] = useState('Alex');
  const [previewed, setPreviewed] = useState(false);
  const inputId = useId();
  const selectId = useId();
  const recipient = name.trim() || 'there';
  const message = template === 'order'
    ? `Hi ${recipient}, good news! Your order #1042 has been shipped and is on its way. Thanks for shopping with us!`
    : `Hi ${recipient}, a quick reminder about your appointment tomorrow at 10:00 AM. We look forward to seeing you. Please reply if you need to reschedule.`;

  return (
    <section className="section fs-templates-section" id="templates" aria-labelledby="fs-templates-heading">
      <div className="container fs-split fs-templates-split">
        <div className="fs-copy">
          <span className="fs-eyebrow"><ArrowUpRight size={15} aria-hidden="true" /> THOUGHTFUL OUTREACH</span>
          <h2 id="fs-templates-heading"><span>Start the conversation.</span><span className="fs-muted-heading">Keep the context.</span></h2>
          <p>A timely order update. A helpful appointment reminder. Reach opted-in customers with approved WhatsApp templates, and keep every reply in your shared inbox.</p>
          <div className="fs-template-points"><span><FileCheck2 size={16} />Approved message templates</span><span><ArrowDownLeft size={16} />Replies land in the right workspace</span></div>
          <p className="fs-platform-note"><ShieldCheck size={14} />Outbound messaging follows WhatsApp platform rules and requires customer opt-in.</p>
        </div>
        <div className="fs-template-panel">
          <div className="fs-panel-heading"><span className="fs-square-icon"><Sparkles size={17} /></span><div><strong>A little more personal.</strong><span>Try an interactive template preview</span></div><span className="fs-approved"><Check size={11} />Approved</span></div>
          <div className="fs-template-fields"><div><label htmlFor={selectId}>Message template</label><div className="fs-select-wrap"><select id={selectId} value={template} onChange={(event) => { setTemplate(event.target.value); setPreviewed(false); }}><option value="order">Order update</option><option value="appointment">Appointment reminder</option></select><ChevronDown size={14} aria-hidden="true" /></div></div><div><label htmlFor={inputId}>Customer name</label><input id={inputId} value={name} onChange={(event) => { setName(event.target.value); setPreviewed(false); }} maxLength={40} placeholder="Alex" autoComplete="off" /></div></div>
          <div className="fs-message-stage"><span className="fs-preview-label">MESSAGE PREVIEW</span><div className="fs-message-bubble"><p>{message}</p><div><span>10:42</span><CheckCheck size={14} /></div></div><span className="fs-stage-caption"><LockKeyhole size={10} />Sample content · visible only to you</span></div>
          <div className="fs-template-bottom"><span className="fs-preview-status" role="status">{previewed ? <><Check size={13} />Preview ready. No message was sent.</> : 'See how your message will look.'}</span><button type="button" className="fs-preview-button" onClick={() => setPreviewed(true)}>{previewed ? 'Preview ready' : 'Preview message'}{previewed ? <Check size={13} /> : <ArrowRight size={13} />}</button></div>
        </div>
      </div>
    </section>
  );
}
