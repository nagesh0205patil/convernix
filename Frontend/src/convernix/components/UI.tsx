import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import {
  ArrowRight,
  ArrowUpRight,
  ChevronDown,
  Inbox,
  Users,
  Workflow,
  GitBranch,
  FileText,
  ContactRound,
  BarChart3,
  Settings2,
  Headphones,
  BriefcaseBusiness,
  MessagesSquare,
  Network,
  Building2,
  ShieldCheck,
  X,
  Menu,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type ModalKind = 'demo' | 'signin' | 'signup' | 'pricing' | 'resources' | 'security' | 'company' | 'legal';
export type OpenModal = (kind: ModalKind, topic?: string) => void;

export function Brand({ onNavigate }: { onNavigate?: (page: 'home' | 'pricing', hash?: string) => void }) {
  return (
    <a
      href="#"
      className="brand"
      aria-label="Convernix by Cloudtronix home"
      onClick={(e) => {
        if (onNavigate) {
          e.preventDefault();
          onNavigate('home');
        }
      }}
    >
      <svg className="brand-mark" viewBox="0 0 40 40" fill="none" aria-hidden="true">
        <rect width="40" height="40" rx="12" fill="currentColor" />
        <path d="M27 12H17a8 8 0 0 0 0 16h4l6-5H17a3 3 0 0 1 0-6h5Z" fill="#0b0d14" />
        <circle cx="29" cy="28" r="3" fill="#0b0d14" />
      </svg>
      <span className="brand-name">
        convernix<span className="brand-by">BY CLOUDTRONIX</span>
      </span>
    </a>
  );
}

export function CTAButton({
  children,
  onClick,
  href,
  secondary = false,
  className = '',
}: {
  children: ReactNode;
  onClick?: () => void;
  href?: string;
  secondary?: boolean;
  className?: string;
}) {
  const classes = `button ${secondary ? 'button-secondary' : 'button-primary'} ${className}`;
  return href ? (
    <a className={classes} href={href}>
      {children}
    </a>
  ) : (
    <button className={classes} onClick={onClick}>
      {children}
    </button>
  );
}

export function SectionHeader({
  eyebrow,
  title,
  description,
  centered = false,
}: {
  eyebrow: string;
  title: ReactNode;
  description?: string;
  centered?: boolean;
}) {
  return (
    <div className={`section-header ${centered ? 'centered' : ''}`}>
      <span className="eyebrow">
        <span />
        {eyebrow}
      </span>
      <h2>{title}</h2>
      {description && <p>{description}</p>}
    </div>
  );
}

export function Navbar({
  openModal,
  currentPage = 'home',
  onNavigate,
}: {
  openModal: OpenModal;
  currentPage?: 'home' | 'pricing';
  onNavigate?: (page: 'home' | 'pricing', hash?: string) => void;
}) {
  const [mobile, setMobile] = useState(false);
  const [dropdown, setDropdown] = useState<'product' | 'solutions' | null>(null);
  const navRef = useRef<HTMLElement>(null);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setDropdown(null);
        setMobile(false);
      }
    };
    const onOutside = (event: PointerEvent) => {
      if (!navRef.current?.contains(event.target as Node)) {
        setDropdown(null);
        setMobile(false);
      }
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onOutside);
    return () => {
      window.removeEventListener('scroll', onScroll);
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onOutside);
    };
  }, []);

  const close = () => {
    setDropdown(null);
    setMobile(false);
  };

  const handleNav = (page: 'home' | 'pricing', hash?: string) => {
    close();
    if (onNavigate) {
      onNavigate(page, hash);
    }
  };

  const products: [LucideIcon, string, string, string][] = [
    [Inbox, 'Shared inbox', 'A home for every conversation', '#platform'],
    [Users, 'Team collaboration', 'Work together with full context', '#collaboration'],
    [Workflow, 'Workflow automation', 'Put repetitive work on autopilot', '#automation'],
    [GitBranch, 'Message routing', 'Get customers to the right team', '#departments'],
    [FileText, 'WhatsApp templates', 'Start meaningful conversations', '#templates'],
    [ContactRound, 'Contact management', 'Keep the customer in context', '#features'],
    [BarChart3, 'Analytics', 'Make your work visible', '#analytics'],
    [Settings2, 'Administration', 'Your workspace, your controls', '#security'],
  ];

  const solutions: [LucideIcon, string, string, string][] = [
    [Headphones, 'Customer support', 'Make every customer feel heard', '#solutions'],
    [BriefcaseBusiness, 'Sales', 'Turn enquiries into opportunities', '#solutions'],
    [MessagesSquare, 'Customer engagement', 'Build lasting relationships', '#templates'],
    [Network, 'Operations', 'Keep everything moving', '#solutions'],
    [Building2, 'Multi-department teams', 'Bring your business together', '#departments'],
    [ShieldCheck, 'Enterprise teams', 'Visibility and control at scale', '#security'],
  ];

  return (
    <header className={`site-header ${scrolled ? 'is-scrolled' : ''}`}>
      <nav className="container navbar" aria-label="Main navigation" ref={navRef}>
        <Brand onNavigate={onNavigate} />
        <button
          className="mobile-toggle icon-button"
          aria-label={mobile ? 'Close navigation' : 'Open navigation'}
          aria-expanded={mobile}
          aria-controls="main-nav"
          onClick={() => setMobile(!mobile)}
        >
          {mobile ? <X /> : <Menu />}
        </button>

        <div id="main-nav" className={`nav-links ${mobile ? 'mobile-open' : ''}`}>
          {(['product', 'solutions'] as const).map((item) => (
            <div className="nav-dropdown" key={item}>
              <button
                className={`nav-link ${dropdown === item ? 'active' : ''}`}
                aria-expanded={dropdown === item}
                aria-controls={`${item}-menu`}
                onClick={() => setDropdown(dropdown === item ? null : item)}
              >
                {item === 'product' ? 'Product' : 'Solutions'}
                <ChevronDown size={13} />
              </button>
              {dropdown === item && (
                <div className="mega-menu" id={`${item}-menu`}>
                  <div className="mega-caption">
                    {item === 'product' ? 'YOUR CONVERSATION WORKSPACE' : 'BUILT AROUND YOUR TEAM'}
                  </div>
                  <div className="mega-grid">
                    {(item === 'product' ? products : solutions).map(([Icon, title, desc, link]) => (
                      <a
                        href={link}
                        className="mega-item"
                        key={title}
                        onClick={(e) => {
                          e.preventDefault();
                          handleNav('home', link);
                        }}
                      >
                        <span className="mini-icon">
                          <Icon size={19} />
                        </span>
                        <span>
                          <strong>{title}</strong>
                          <small>{desc}</small>
                        </span>
                        <ArrowUpRight size={14} />
                      </a>
                    ))}
                  </div>
                  <div className="mega-bottom">
                    <span>One number. Endless possibilities.</span>
                    <button
                      onClick={() => {
                        close();
                        openModal('demo');
                      }}
                    >
                      Explore with our team <ArrowRight size={14} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}

          <a
            className="nav-link"
            href="#features"
            onClick={(e) => {
              e.preventDefault();
              handleNav('home', '#features');
            }}
          >
            Features
          </a>
          <a
            className="nav-link"
            href="#integrations"
            onClick={(e) => {
              e.preventDefault();
              handleNav('home', '#integrations');
            }}
          >
            Integrations
          </a>
          <a
            className={`nav-link ${currentPage === 'pricing' ? 'active' : ''}`}
            href="#pricing"
            onClick={(e) => {
              e.preventDefault();
              handleNav('pricing');
            }}
          >
            Pricing
          </a>
          <button
            className="nav-link"
            onClick={() => {
              close();
              openModal('resources');
            }}
          >
            Resources
          </button>
          <a
            className="nav-link"
            href="#security"
            onClick={(e) => {
              e.preventDefault();
              handleNav('home', '#security');
            }}
          >
            Security
          </a>

          <div className="mobile-actions">
            <button
              className="nav-link"
              onClick={() => {
                close();
                openModal('signin');
              }}
            >
              Sign in
            </button>
            <CTAButton
              onClick={() => {
                close();
                openModal('demo');
              }}
            >
              Book a demo <ArrowUpRight size={15} />
            </CTAButton>
          </div>
        </div>

        <div className="nav-actions">
          <button className="sign-in" onClick={() => openModal('signin')}>
            Sign in <ArrowUpRight size={13} />
          </button>
          <CTAButton onClick={() => openModal('demo')}>
            Book a demo <ArrowUpRight size={15} />
          </CTAButton>
        </div>
      </nav>
    </header>
  );
}
