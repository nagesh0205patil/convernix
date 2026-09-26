import { useState } from 'react';
import { ArrowRight, ArrowUpRight, Check, CheckCheck, ChevronRight, Command, Inbox, Users, GitBranch, FileText, ContactRound, BarChart3, Headphones, BriefcaseBusiness, MessagesSquare, Network, Building2, ShieldCheck, Play, LockKeyhole, MessageCircle, Layers3, Search, Plus, Receipt, ArrowLeftRight, CircleCheck, Code2, Send } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { CTAButton, SectionHeader } from './UI';
import type { OpenModal } from './UI';
import ProductMockup from './ProductMockup';

export function Hero({ openModal }: { openModal: OpenModal }) {
  return <section className="hero" aria-labelledby="hero-heading"><div className="hero-glow"/><div className="hero-grid"/>
    <div className="container hero-content"><a className="announcement" href="#automation"><span className="announcement-dot"/>A smarter way to work on WhatsApp<span className="announcement-divider"/><ArrowRight size={14}/></a>
      <div className="hero-eyebrow">WHATSAPP BUSINESS COMMUNICATION PLATFORM</div>
      <h1 id="hero-heading">One WhatsApp number.<br/><span>Your entire team, connected.</span></h1>
      <p className="hero-description">Bring every conversation, department, and teammate together.<br className="desktop-break"/> A shared workspace that turns customer messages into meaningful connections.</p>
      <div className="hero-buttons"><CTAButton onClick={() => openModal('demo')}>Book a demo <ArrowRight size={17}/></CTAButton><CTAButton href="#platform" secondary><span className="play-circle"><Play size={11} fill="currentColor"/></span>Explore the platform</CTAButton></div>
      <div className="hero-trust"><span><ShieldCheck size={14}/>Official WhatsApp API integration</span><span><Users size={14}/>Built for teams</span><span><LockKeyhole size={13}/>Centralized & secure</span></div>
      <div className="product-stage" id="platform"><div className="preview-topline"><span><span className="live-dot"/>YOUR TEAM’S NEW HOME BASE</span><span>One workspace. All the context.</span></div><ProductMockup/><div className="product-shadow"/></div>
      <div className="platform-caption"><span className="whatsapp-icon"><MessageCircle size={16}/></span>Powered by the official WhatsApp Business Platform<span className="caption-dot">·</span><span>Designed & developed by <strong>Cloudtronix</strong></span></div>
    </div>
  </section>;
}
export function ValueStrip() {
  const values: [LucideIcon, string, string][] = [[MessageCircle, 'Official WhatsApp integration', 'Your number. A more powerful workspace.'], [Layers3, 'One shared workspace', 'Every conversation, in the right place.'], [GitBranch, 'Intelligent routing', 'The right team, from the first message.'], [ShieldCheck, 'Secure team access', 'The right access for every teammate.']];
  return <div className="value-strip container">{values.map(([Icon, title, desc]) => <div className="value-item" key={title}><Icon size={22}/><div><h3>{title}</h3><p>{desc}</p></div></div>)}</div>;
}
export function FeaturesSection() {
  const items: [LucideIcon, string, string][] = [
    [Building2, 'Organized departments', 'Give Sales, Support, Billing, and Operations their own space to do great work.'],
    [ContactRound, 'The full customer picture', 'Keep contact details, tags, and interaction history right beside the conversation.'],
    [ArrowLeftRight, 'Seamless handovers', 'Transfer conversations between people and departments without losing the context.'],
    [FileText, 'Approved templates', 'Start supported conversations with approved WhatsApp Business message templates.'],
    [MessagesSquare, 'Private team notes', 'Bring in a teammate and share helpful context, visible only to your team.'],
    [CircleCheck, 'Clear conversation status', 'Track open, assigned, pending, and resolved conversations with clear ownership.'],
    [Users, 'Thoughtful agent assignment', 'Assign available agents and give every conversation a clear, accountable owner.'],
    [BarChart3, 'Visibility that matters', 'See response times, team activity, and conversation trends in one place.'],
  ];
  return <section className="section features-section" id="features"><div className="container"><SectionHeader eyebrow="BUILT FOR REAL CONVERSATIONS" title={<>Everything your team needs.<br/><span className="muted-heading">Finally, in one place.</span></>} description="Less switching between tools. More time for your customers. Give your team a workspace that works the way they do." centered/>
    <div className="feature-bento"><a href="#platform" className="bento-card inbox-bento"><span className="feature-icon"><Inbox size={23}/></span><h3>A shared inbox. A united team.</h3><p>One home for every WhatsApp conversation. Collaborate with clarity, respond with context, and leave no customer waiting.</p><span className="text-link">Explore the shared inbox <ArrowUpRight size={16}/></span><div className="mini-inbox" aria-hidden="true"><div className="mini-inbox-header"><span>Team inbox <span className="count-badge">12</span></span><span><Search size={13}/><Plus size={13}/></span></div><div className="mini-inbox-row"><span className="avatar peach">AM</span><div><strong>Alex Morgan <small>2 min</small></strong><p>Hi, I need help with my invoice.</p></div><span className="mini-tag">Billing</span></div><div className="mini-inbox-row"><span className="avatar violet">JL</span><div><strong>Jamie Lee <small>5 min</small></strong><p>Thanks! That’s exactly what I needed.</p></div><span className="mini-tag green">Resolved</span></div><div className="sample-caption">Illustrative conversations</div></div></a>
    <a href="#automation" className="bento-card routing-bento"><span className="feature-icon"><GitBranch size={23}/></span><h3>Right message. Right teammate.</h3><p>Turn incoming messages into organized workflows. Route by customer choice, keywords, or the rules you define.</p><span className="text-link">Discover intelligent routing <ArrowUpRight size={16}/></span><div className="mini-routing" aria-hidden="true"><div className="route-source"><MessageCircle size={17}/><span>Incoming message</span><span className="live-dot"/></div><div className="route-line"/><div className="route-rule"><GitBranch size={16}/>Match routing rule<Check size={13}/></div><div className="route-branches"><span><BriefcaseBusiness size={14}/>Sales</span><span className="selected"><Receipt size={14}/>Billing</span><span><Headphones size={14}/>Support</span></div><div className="route-status"><span className="avatar small violet">SP</span>Assigned to Sarah Parker<CheckCheck size={14}/></div></div></a></div>
    <div className="feature-grid">{items.map(([Icon, title, desc]) => <article className="feature-card" key={title}><Icon size={21}/><h3>{title}</h3><p>{desc}</p></article>)}</div>
  </div></section>;
}
const departments: { name: string; icon: LucideIcon; people: string[]; color: string; copy: string }[] = [
  { name: 'Sales', icon: BriefcaseBusiness, people: ['AK', 'JT', 'MR'], color: 'peach', copy: 'A new product enquiry reaches your sales team, ready for a personal follow-up.' },
  { name: 'Customer support', icon: Headphones, people: ['ML', 'RJ', 'AS'], color: 'blue', copy: 'Customer questions land with support, along with the full conversation history.' },
  { name: 'Billing', icon: Receipt, people: ['SP', 'DK', 'LN'], color: 'violet', copy: 'Invoice and payment questions go straight to Billing, with a clear owner from the start.' },
  { name: 'Technical support', icon: Code2, people: ['JC', 'TW', 'NK'], color: 'mint', copy: 'Technical requests reach the people with the right expertise to help.' },
  { name: 'Operations', icon: Network, people: ['ER', 'CP', 'BV'], color: 'rose', copy: 'Delivery and service coordination reach your operations team without a detour.' },
];
export function DepartmentSection() {
  const [selected, setSelected] = useState(2);
  return <section className="section department-section" id="departments"><div className="container"><div className="department-intro"><SectionHeader eyebrow="ONE NUMBER. NO SILOS." title={<>Your customers see one business.<br/><span className="muted-heading">Let your teams work like one.</span></>}/><p>Business WhatsApp wasn’t designed for complex teams. Convernix brings order to shared access, duplicate replies, and unclear ownership—without changing your number.</p></div>
    <div className="department-map"><div className="number-node"><span className="whatsapp-tile"><MessageCircle size={26}/></span><div><strong>One WhatsApp Business number</strong><span>A familiar number. A better experience.</span></div><span className="connected-label"><span className="live-dot"/>Connected</span></div><div className="map-trunk"/><div className="platform-node"><Command size={22}/><span>Convernix <small>Intelligent routing & shared context</small></span><GitBranch size={20}/></div><div className="department-branches"/>
      <div className="department-cards">{departments.map(({ name, icon: Icon, people, color }, i) => <button className={`department-card ${selected === i ? 'selected' : ''}`} aria-pressed={selected === i} key={name} onClick={() => setSelected(i)}><span className={`department-icon ${color}`}><Icon size={20}/></span><strong>{name}</strong><span className="agent-stack">{people.map(person => <span className={`avatar small ${color}`} key={person}>{person}</span>)}</span><span className="department-card-bottom">Dedicated team <ChevronRight size={12}/></span></button>)}</div>
      <div className="routing-explanation" aria-live="polite"><span className="routing-explanation-icon"><GitBranch size={17}/></span><p>{departments[selected].copy}</p><span className="demo-label">Example routing</span></div>
    </div>
  </div></section>;
}
export function HowItWorks() {
  const steps: [LucideIcon, string, string][] = [[MessageCircle, 'A customer says hello', 'They message your existing WhatsApp Business number.'], [Inbox, 'The message arrives', 'Convernix brings it into your centralized workspace.'], [GitBranch, 'Your rules do the routing', 'A menu choice, keyword, or condition finds the right team.'], [Users, 'An owner takes the lead', 'The right department or available agent gets the conversation.'], [Send, 'Your team makes it personal', 'Reply, collaborate, and resolve—all from Convernix.']];
  return <section className="section how-section" id="how-it-works"><div className="container"><SectionHeader eyebrow="FROM HELLO TO HANDLED" title={<>A simple journey.<br/><span className="muted-heading">A better conversation.</span></>} centered/><div className="steps-grid">{steps.map(([Icon, title, desc], i) => <article className="step" key={title}><div className="step-top"><span className={`step-icon ${i === 0 ? 'whatsapp' : ''}`}><Icon size={23}/></span><span className="step-number">0{i + 1}</span>{i !== steps.length - 1 && <ArrowRight className="step-arrow" size={16}/>}</div><h3>{title}</h3><p>{desc}</p></article>)}</div></div></section>;
}
