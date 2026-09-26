import { useState, useEffect, useCallback, type ReactNode } from 'react';
import { Navbar } from './components/UI';
import type { OpenModal, ModalKind } from './components/UI';
import { Hero, ValueStrip, FeaturesSection, DepartmentSection, HowItWorks } from './components/Marketing';
import {
  IntegrationsSection,
  SecuritySection,
  UseCases,
  AISection,
  FAQ,
  CTASection,
  Footer,
} from './components/MoreSections';
import WorkflowSection from './components/WorkflowSection';
import { AnalyticsSection, TeamSection, TemplatesSection } from './components/FeatureShowcases';
import PricingPage from './components/PricingPage';
import Modal from './components/Modal';

type PageRoute = 'home' | 'pricing';

export default function App({ signIn }: { signIn: ReactNode }) {
  const [modal, setModal] = useState<{ kind: ModalKind; topic?: string } | null>(null);
  const openModal: OpenModal = (kind, topic) => setModal({ kind, topic });

  const getInitialPage = (): PageRoute => {
    if (typeof window !== 'undefined') {
      const hash = window.location.hash.toLowerCase();
      const path = window.location.pathname.toLowerCase();
      if (hash === '#pricing' || path === '/pricing') {
        return 'pricing';
      }
    }
    return 'home';
  };

  const [page, setPage] = useState<PageRoute>(getInitialPage);

  const navigate = useCallback((targetPage: PageRoute, targetHash?: string) => {
    setPage(targetPage);
    if (targetPage === 'pricing') {
      window.history.pushState(null, '', '#pricing');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      if (targetHash && targetHash !== '#') {
        window.history.pushState(null, '', targetHash);
        // Defer scroll to allow DOM update
        setTimeout(() => {
          const el = document.querySelector(targetHash);
          if (el) {
            el.scrollIntoView({ behavior: 'smooth' });
          } else {
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }
        }, 50);
      } else {
        window.history.pushState(null, '', window.location.pathname);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    }
  }, []);

  useEffect(() => {
    const handleUrlChange = () => {
      const hash = window.location.hash.toLowerCase();
      const path = window.location.pathname.toLowerCase();
      if (hash === '#pricing' || path === '/pricing') {
        setPage('pricing');
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else {
        setPage('home');
      }
    };

    window.addEventListener('hashchange', handleUrlChange);
    window.addEventListener('popstate', handleUrlChange);
    return () => {
      window.removeEventListener('hashchange', handleUrlChange);
      window.removeEventListener('popstate', handleUrlChange);
    };
  }, []);

  return (
    <div className="convernix-site">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <Navbar openModal={openModal} currentPage={page} onNavigate={navigate} />

      <main id="main">
        {page === 'pricing' ? (
          /* Dedicated Pricing Page View (Only shown when on pricing route) */
          <PricingPage openModal={openModal} onNavigate={navigate} />
        ) : (
          /* Main Landing Page View (Does NOT show pricing section) */
          <>
            <Hero openModal={openModal} />
            <ValueStrip />
            <FeaturesSection />
            <DepartmentSection />
            <HowItWorks />
            <WorkflowSection />
            <TeamSection />
            <TemplatesSection />
            <AnalyticsSection />
            <IntegrationsSection />
            <SecuritySection openModal={openModal} />
            <UseCases />
            <AISection />
            <FAQ />
            <CTASection openModal={openModal} />
          </>
        )}
      </main>

      <Footer openModal={openModal} onNavigate={navigate} />
      {modal && (
        <Modal
          signIn={signIn}
          key={modal.kind + (modal.topic || '')}
          {...modal}
          close={() => setModal(null)}
          openModal={openModal}
          onNavigate={navigate}
        />
      )}
    </div>
  );
}
