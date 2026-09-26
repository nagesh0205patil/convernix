import React, { useEffect, useRef, useState } from 'react';
import type { ReactNode, FormEvent } from 'react';
import { ArrowRight, ArrowUpRight, Check, Copy, Download, CircleHelp, Users, Building2, MessageCircle, Workflow, X, ShieldCheck, FileText } from 'lucide-react';
import { CTAButton } from './UI';
import type { ModalKind, OpenModal } from './UI';
function DemoForm({ title }: { title?: string }) {
  const [request, setRequest] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const endpoint = import.meta.env.VITE_DEMO_ENDPOINT as string | undefined;
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(''); setBusy(true);
    const data = Object.fromEntries(new FormData(event.currentTarget).entries());
    const summary = `Convernix demo request\n\nName: ${data.name}\nWork email: ${data.email}\nCompany: ${data.company}\nTeam size: ${data.size}\nNotes: ${data.notes || 'None'}\n`;
    try {
      if (endpoint) { const result = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); if (!result.ok) throw new Error('Your request could not be submitted. Please try again.'); setSubmitted(true); }
      setRequest(summary);
    } catch (e) { setError(e instanceof Error ? e.message : 'Something went wrong. Please try again.'); } finally { setBusy(false); }
  };
  const download = () => { const url = URL.createObjectURL(new Blob([request], { type: 'text/plain' })); const a = document.createElement('a'); a.href = url; a.download = 'convernix-demo-request.txt'; a.click(); URL.revokeObjectURL(url); };
  if (request) return <div className="form-success"><span className="success-icon"><Check size={27}/></span><h2 id="modal-title">{submitted ? 'Let’s start a conversation.' : 'Your request is ready.'}</h2><p>{submitted ? 'Your demo request was submitted successfully. Our team will follow up using your work email.' : 'This preview prepares your request locally. No request has been sent. Copy or download it to share with your Cloudtronix contact.'}</p><textarea aria-label="Demo request summary" readOnly value={request} rows={8}/><div className="modal-actions"><CTAButton onClick={async () => { try { await navigator.clipboard.writeText(request); setCopied(true); } catch { setError('Copy is unavailable. Please select the text above or download the request.'); } }}>{copied ? <Check size={16}/> : <Copy size={16}/>} {copied ? 'Copied' : 'Copy request'}</CTAButton><CTAButton secondary onClick={download}><Download size={16}/>Download</CTAButton></div>{error && <p className="form-error" role="alert">{error}</p>}</div>;
  return <><span className="eyebrow"><span/>LET’S CONNECT</span><h2 id="modal-title">{title || 'Meet your new workspace.'}</h2><p className="modal-description">Tell us a little about your team. We’ll help you explore what better customer conversations could look like.</p><form className="demo-form" onSubmit={submit}><div className="form-two-col"><label>Full name<input name="name" autoComplete="name" placeholder="Alex Morgan" required maxLength={100}/></label><label>Work email<input name="email" type="email" autoComplete="email" placeholder="alex@company.com" required maxLength={200}/></label></div><div className="form-two-col"><label>Company<input name="company" autoComplete="organization" placeholder="Your company" required maxLength={150}/></label><label>Team size<select name="size" defaultValue="" required><option value="" disabled>Select team size</option><option>1–5 people</option><option>6–20 people</option><option>21–50 people</option><option>51–200 people</option><option>200+ people</option></select></label></div><label>What would you like to solve? <span className="optional">(optional)</span><textarea name="notes" rows={3} placeholder="Tell us about your team and customer conversations…" maxLength={2000}/></label>{!endpoint && <p className="form-notice"><CircleHelp size={16}/>Preview form: your details stay in this page. Prepare a request to copy or download.</p>}{error && <p className="form-error" role="alert">{error}</p>}<button className="button button-primary form-submit" type="submit" disabled={busy}>{busy ? 'Submitting…' : endpoint ? 'Request a demo' : 'Prepare demo request'}<ArrowRight size={16}/></button><small className="form-footnote">Please don’t include access tokens, account secrets, or other sensitive credentials.</small></form></>;
}
export default function Modal({
  kind,
  topic,
  close,
  openModal,
  signIn,
  onNavigate,
}: {
  kind: ModalKind;
  topic?: string;
  close: () => void;
  openModal: OpenModal;
  signIn?: ReactNode;
  onNavigate?: (page: 'home' | 'pricing', hash?: string) => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = dialogRef.current; const previous = document.activeElement as HTMLElement | null; const overflow = document.body.style.overflow;
    dialog?.showModal(); document.body.style.overflow = 'hidden';
    return () => { dialog?.close(); document.body.style.overflow = overflow; previous?.focus(); };
  }, []);
  const resources = [
    { icon: MessageCircle, title: 'Connect WhatsApp Business', text: 'Start with your Meta business setup. Prepare your WhatsApp Business Account ID, Phone Number ID, app credentials, access token, and webhook configuration.', href: '#integrations' },
    { icon: Users, title: 'Set up your team', text: 'Create departments, invite authorized agents, and decide who can access conversations and administrative settings.', href: '#departments' },
    { icon: Workflow, title: 'Build your first workflow', text: 'Define your welcome message, customer menu, routing conditions, and agent assignment.', href: '#automation' },
    { icon: CircleHelp, title: 'Find a quick answer', text: 'Read answers to common questions about number setup, shared access, templates, and future AI capabilities.', href: '#faq' },
  ];
  return <dialog className={`modal modal-${kind}`} ref={dialogRef} aria-labelledby="modal-title" onCancel={close} onClick={event => { if (event.target === event.currentTarget) close(); }}><div className="modal-content"><button className="modal-close icon-button" onClick={close} aria-label="Close dialog"><X size={20}/></button>
    {kind === 'demo' && <DemoForm title={topic}/>}
    {(kind === 'signin' || kind === 'signup') && (React.isValidElement(signIn) ? React.cloneElement(signIn as React.ReactElement<any>, {
      initialMode: kind === 'signup' ? 'register' : 'signin',
      initialTier: topic,
      onSwitchMode: (next: 'signin' | 'register') => openModal(next === 'register' ? 'signup' : 'signin', topic),
    }) : signIn)}
    {kind === 'pricing' && <><span className="eyebrow"><span/>A WORKSPACE THAT GROWS WITH YOU</span><h2 id="modal-title">Zoho-Simple Pricing in INR</h2><p className="modal-description">Explore our 15-day free trial plans: Basic, Standard, and Premium tiers for official WhatsApp Business operations starting at ₹2,499/month.</p><div className="pricing-options"><div><Users size={24}/><h3>Basic & Standard</h3><p>Starting at ₹2,499/mo. 5 GB to 10 GB media storage, multi-agent inbox, automated routing, instant lead alerts, and broadcast campaigns.</p></div><div><Building2 size={24}/><h3>Premium Scale</h3><p>₹8,499/mo. 15 GB media storage, up to 25 WhatsApp numbers, 100 agent seats, 500 campaigns, and dedicated support.</p></div></div><p className="modal-fineprint">Billed in Indian Rupees (INR). 15-day free trial, no credit card required. Meta WhatsApp messaging fees apply at actuals with 0% platform markup.</p><div className="modal-actions"><CTAButton href="#pricing" onClick={() => { close(); onNavigate?.('pricing'); }}>Compare Plans & Features <ArrowRight size={16}/></CTAButton><CTAButton secondary onClick={() => openModal('demo', 'Pricing & Volume Inquiries')}>Talk to Sales</CTAButton></div></>}
    {kind === 'resources' && <><span className="eyebrow"><span/>THE STARTING POINT</span><h2 id="modal-title">{topic || 'A little guidance goes a long way.'}</h2><p className="modal-description">Explore the essentials of your Convernix workspace. Full product and API documentation will be available with the platform.</p><div className="resource-list">{resources.map(({ icon: Icon, title, text, href }) => <a key={title} href={href} onClick={close}><span className="mini-icon"><Icon size={21}/></span><div><h3>{title}</h3><p>{text}</p></div><ArrowUpRight size={17}/></a>)}</div></>}
    {kind === 'security' && <><span className="modal-symbol"><ShieldCheck size={27}/></span><h2 id="modal-title">Built around responsible access.</h2><p className="modal-description">Convernix’s security approach centers on who can access your workspace, how connections are configured, and the visibility administrators need.</p><ul className="security-detail-list"><li><Check/>Role-based access and scoped user permissions</li><li><Check/>Controlled handling of Meta credentials and tokens</li><li><Check/>Webhook verification and session management</li><li><Check/>Audit visibility and administrative oversight</li><li><Check/>Encrypted transport where applicable</li></ul><p className="modal-fineprint">For deployment-specific security details, retention practices, and technical review materials, speak with our team. No third-party security certifications are claimed on this page.</p><CTAButton onClick={() => openModal('demo', 'Let’s talk security.')}>Arrange a security walkthrough <ArrowRight size={16}/></CTAButton></>}
    {kind === 'company' && <><span className="eyebrow"><span/>THE PEOPLE BEHIND THE PLATFORM</span><h2 id="modal-title">{topic || 'Built by Cloudtronix.'}</h2><p className="modal-description">Convernix is a Cloudtronix product built to bring business conversations, teams, and workflows into one shared workspace.</p><p className="modal-description">{topic === 'Careers' ? 'For information about current opportunities at Cloudtronix, start a conversation with our team.' : topic === 'Partners' ? 'Interested in working with Cloudtronix? Tell us about your business and how you would like to collaborate.' : 'Our focus is simple: help businesses manage their WhatsApp customer communication with more clarity, ownership, and control.'}</p><CTAButton onClick={() => openModal('demo', 'Talk to the Cloudtronix team.')}>Talk to our team <ArrowRight size={16}/></CTAButton></>}
    {kind === 'legal' && <><span className="modal-symbol"><FileText size={25}/></span><h2 id="modal-title">{topic || 'Legal information'}</h2><p className="modal-description">The production {topic?.toLowerCase() || 'legal documents'} will be provided by Cloudtronix before the service is made available. This website preview is not a contract or a published legal policy.</p><p className="modal-description">This preview has no analytics or advertising cookies. Interactive demo messages and form inputs are held in the current page and reset when you reload. A configured demo-request service will receive details only when you submit the form.</p><CTAButton secondary onClick={close}>Got it <Check size={16}/></CTAButton></>}
  </div></dialog>;
}
