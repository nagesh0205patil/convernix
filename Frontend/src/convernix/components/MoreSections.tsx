import { ArrowRight, ArrowUpRight, Check, MessageCircle, ContactRound, Database, Headphones, Webhook, Code2, Layers3, Users, KeyRound, ShieldCheck, LockKeyhole, BriefcaseBusiness, Receipt, Network, Building2, Sparkles, Plus, Globe2 } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Brand, CTAButton, SectionHeader } from './UI';
import type { OpenModal, ModalKind } from './UI';
export function IntegrationsSection() {
  const integrations: [LucideIcon, string][] = [[ContactRound, 'CRM'], [Database, 'ERP'], [Headphones, 'Help desk'], [Webhook, 'Webhooks'], [Code2, 'REST API'], [Layers3, 'Business apps']];
  return <section className="section integrations-section" id="integrations"><div className="container integration-layout"><SectionHeader eyebrow="CONNECTED BY DESIGN" title={<>Fits your business.<br/><span className="muted-heading">Connects your tools.</span></>} description="Built around the official Meta WhatsApp Business Platform, with an integration roadmap for the tools your teams already use."/><div className="integration-visual"><div className="integration-core"><span className="whatsapp-tile"><MessageCircle size={30}/></span><div><span className="integration-status">CORE INTEGRATION</span><h3>WhatsApp Business Platform</h3><p>A direct connection through Meta’s Cloud API.</p></div><Check size={18}/></div><div className="integration-divider"><span/>A CONNECTED ECOSYSTEM, ON THE ROADMAP<span/></div><div className="integration-grid">{integrations.map(([Icon, title]) => <div className="integration-card" key={title}><Icon size={20}/><span>{title}</span><small>Planned</small></div>)}</div><p className="integration-note">Connect using your Meta account credentials and verified webhook configuration. Availability of future integrations may vary.</p></div></div></section>;
}
export function SecuritySection({ openModal }: { openModal: OpenModal }) {
  const items: [LucideIcon, string, string][] = [[Users, 'Access with intention', 'Role-based access, user permissions, and administrative controls.'], [KeyRound, 'Credentials with care', 'Secure credential handling and controlled connection settings.'], [ShieldCheck, 'Visibility by design', 'Audit visibility, session management, and webhook verification.'], [LockKeyhole, 'Protected connections', 'Encrypted transport where applicable across your communication workflow.']];
  return <section className="section security-section" id="security"><div className="container"><div className="security-panel"><div className="security-copy"><span className="security-emblem"><ShieldCheck size={31}/></span><SectionHeader eyebrow="CONFIDENCE, BUILT IN" title={<>Your conversations.<br/>Your control.</>} description="Customer communication deserves a workspace built around responsible access and clear oversight."/><button className="text-link" onClick={() => openModal('security')}>Explore our approach to security <ArrowUpRight size={16}/></button></div><div className="security-grid">{items.map(([Icon, title, desc]) => <article key={title}><Icon size={22}/><h3>{title}</h3><p>{desc}</p></article>)}</div></div></div></section>;
}
export function UseCases() {
  const cases: [LucideIcon, string, string][] = [[Headphones, 'Customer support', 'Make helpful feel effortless. Keep every request, reply, and resolution connected.'], [BriefcaseBusiness, 'Sales teams', 'Turn a first hello into an opportunity. Route enquiries to the right representative.'], [Receipt, 'Billing & finance', 'Get payment and invoice questions to the people who can answer them.'], [Code2, 'Technical support', 'Connect customers with the right expertise, with all the context intact.'], [Network, 'Operations', 'Keep customer-facing work coordinated across your people and processes.'], [Building2, 'Enterprise service', 'Bring multiple departments and busy teams together with centralized control.']];
  return <section className="section usecases-section" id="solutions"><div className="container"><SectionHeader eyebrow="MADE FOR YOUR KIND OF WORK" title={<>Different teams.<br/><span className="muted-heading">One better way to connect.</span></>} description="For every team that knows a good conversation can make all the difference." centered/><div className="usecase-grid">{cases.map(([Icon, title, desc]) => <a className="usecase-card" href="#collaboration" key={title}><span className="usecase-icon"><Icon size={22}/></span><h3>{title}</h3><p>{desc}</p><ArrowUpRight className="usecase-arrow" size={17}/></a>)}</div></div></section>;
}
export function AISection() {
  return <section className="section ai-section"><div className="container"><div className="ai-panel"><div className="ai-orb" aria-hidden="true"><div className="ai-orbit one"/><div className="ai-orbit two"/><div className="ai-orbit three"/><div className="ai-orb-core"><Sparkles size={34}/></div><span className="ai-spark spark-one"/><span className="ai-spark spark-two"/></div><div className="ai-copy"><span className="coming-soon"><Sparkles size={13}/>ON THE HORIZON · COMING SOON</span><h2>A little intelligence.<br/><span className="muted-heading">A lot more possibility.</span></h2><p>We’re building toward the next generation of customer communication—with AI that helps your team stay thoughtful, informed, and focused.</p><div className="ai-capabilities">{['Conversation summaries', 'Suggested replies', 'Intent & sentiment detection', 'Automatic categorization', 'AI-assisted routing', 'Knowledge-assisted answers'].map(item => <span key={item}><Sparkles size={12}/>{item}</span>)}</div><small>These AI capabilities are in development and are not available yet.</small></div></div></div></section>;
}
export function FAQ() {
  const faqs = [
    ['Can we use our existing WhatsApp Business number?', 'Convernix is designed to connect to an official WhatsApp Business Platform number. The setup path depends on your current account and Meta eligibility. Our team can walk you through number registration or migration before you connect.'],
    ['Can multiple employees use the same WhatsApp number?', 'Yes. Authorized agents work from the shared Convernix inbox. You can organize them into departments, assign conversation ownership, and control access without asking everyone to open WhatsApp Web.'],
    ['How does automatic message routing work?', 'You configure workflows using customer menu choices, keywords, conditions, or business rules. Incoming conversations are then directed to the relevant department or agent. Explore the workflow preview above to see an example.'],
    ['What do I need to connect my WhatsApp account?', 'Setup may require a WhatsApp Business Account ID, Phone Number ID, Meta App ID and App Secret, an appropriate access token, and webhook verification details. Exact requirements depend on your Meta setup. Credentials belong in the secure application setup—not in a demo request.'],
    ['Can we send outbound messages and use templates?', 'Authorized users can initiate supported conversations using approved WhatsApp message templates and applicable customer consent. Outbound messaging must follow the WhatsApp Business Platform’s current rules.'],
    ['Are the AI features available today?', 'The AI capabilities shown here are on the roadmap. Conversation summaries, suggested replies, intent detection, and other AI-assisted features are clearly marked Coming Soon and are not currently available.'],
  ];
  return <section className="section faq-section" id="faq"><div className="container faq-layout"><div><SectionHeader eyebrow="A LITTLE MORE CLARITY" title={<>Good questions.<br/><span className="muted-heading">Straight answers.</span></>}/><p className="faq-aside">Everything else can start with a conversation.</p><a className="text-link" href="#get-started">Let’s talk <ArrowUpRight size={16}/></a></div><div className="faq-list">{faqs.map(([question, answer]) => <details name="convernix-faq" key={question}><summary>{question}<Plus size={18}/></summary><p>{answer}</p></details>)}</div></div></section>;
}
export function CTASection({ openModal }: { openModal: OpenModal }) {
  return <section className="final-cta" id="get-started"><div className="container final-cta-inner" id="demo"><div className="cta-orbit"/><span className="eyebrow"><span/>BETTER CONVERSATIONS START HERE</span><h2>One number.<br/>A whole new way to work.</h2><p>Turn WhatsApp into your team’s customer communication platform.<br/>Connect your number. Bring your team. Make every conversation count.</p><div className="hero-buttons"><CTAButton onClick={() => openModal('demo')}>Book a demo <ArrowRight size={17}/></CTAButton><CTAButton secondary onClick={() => openModal('demo', 'Talk to our team')}>Talk to our team <ArrowUpRight size={16}/></CTAButton></div><span className="powered-by">Thoughtfully built. Powered by <strong>Cloudtronix.</strong></span></div></section>;
}
export function Footer({
  openModal,
  onNavigate,
}: {
  openModal: OpenModal;
  onNavigate?: (page: 'home' | 'pricing', hash?: string) => void;
}) {
  const columns = [
    {
      title: 'Product',
      links: [
        ['Shared inbox', '#platform'],
        ['Pricing', '#pricing'],
        ['Automation', '#automation'],
        ['Message routing', '#departments'],
        ['Departments', '#departments'],
        ['Analytics', '#analytics'],
        ['WhatsApp templates', '#templates'],
      ],
    },
    {
      title: 'Solutions',
      links: [
        ['Sales', '#solutions'],
        ['Customer support', '#solutions'],
        ['Billing', '#solutions'],
        ['Operations', '#solutions'],
        ['Enterprise', '#security'],
      ],
    },
    {
      title: 'Resources',
      links: [
        ['Documentation', 'resources'],
        ['Help center', '#faq'],
        ['API documentation', 'resources'],
        ['Product updates', 'resources'],
        ['Contact', 'demo'],
      ],
    },
    {
      title: 'Company',
      links: [
        ['About Cloudtronix', 'company'],
        ['Contact', 'demo'],
        ['Careers', 'company'],
        ['Partners', 'company'],
      ],
    },
    {
      title: 'Legal',
      links: [
        ['Privacy policy', 'legal'],
        ['Terms of service', 'legal'],
        ['Cookie policy', 'legal'],
        ['Security', '#security'],
      ],
    },
  ];

  const handleLinkClick = (e: React.MouseEvent, target: string) => {
    if (!onNavigate) return;
    if (target === '#pricing') {
      e.preventDefault();
      onNavigate('pricing');
    } else if (target.startsWith('#')) {
      e.preventDefault();
      onNavigate('home', target);
    }
  };

  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-top">
          <div className="footer-brand">
            <Brand onNavigate={onNavigate} />
            <p>
              Every conversation, connected.<br />
              Every team, empowered.
            </p>
            <span className="footer-location">
              <Globe2 size={13} />
              Built for businesses everywhere.
            </span>
          </div>
          <div className="footer-columns">
            {columns.map((column) => (
              <div className="footer-column" key={column.title}>
                <h3>{column.title}</h3>
                {column.links.map(([label, target]) =>
                  target.startsWith('#') ? (
                    <a
                      href={target}
                      key={label}
                      onClick={(e) => handleLinkClick(e, target)}
                    >
                      {label}
                    </a>
                  ) : (
                    <button
                      key={label}
                      onClick={() => openModal(target as ModalKind, label)}
                    >
                      {label}
                    </button>
                  )
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="footer-bottom">
        <span>© {new Date().getFullYear()} Cloudtronix. All rights reserved.</span>
        <span className="footer-bottom-note">One number. Multiple teams. Infinite potential.</span>
        <a
          href="#"
          className="back-to-top"
          aria-label="Back to top"
          onClick={(e) => {
            e.preventDefault();
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }}
        >
          Back to top <ArrowUpRight size={13} />
        </a>
      </div>
    </footer>
  );
}

