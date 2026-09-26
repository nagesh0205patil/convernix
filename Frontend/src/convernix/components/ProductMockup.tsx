import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import {
  ArrowDown, ArrowRight, ArrowUpRight, Bot, Check, CheckCheck, ChevronDown,
  ChevronsUpDown, CircleHelp, ContactRound, FileText, Inbox, LayoutGrid,
  LockKeyhole, MessageCircle, MessageSquareText, MoreHorizontal, Search,
  Send, Settings2, ShieldCheck, Sparkles, StickyNote, UsersRound, Workflow, X,
} from 'lucide-react';
import './product-mockup.css';

type Status = 'Open' | 'Pending' | 'Resolved';
type Scope = 'all' | 'mine' | 'unassigned';
type Tab = 'active' | 'unread' | 'resolved';
type Message = { text: string; note: boolean };
type Conversation = {
  id: number;
  name: string;
  initials: string;
  color: string;
  company: string;
  email: string;
  phone: string;
  location: string;
  preview: string;
  time: string;
  unread: number;
  owner: string;
  department: string;
  status: Status;
  firstMessage: string;
  reply: string;
  messages: Message[];
  updatedAt?: number;
};

type Composer = { reply: string; note: string; isNote: boolean };
const emptyComposer: Composer = { reply: '', note: '', isNote: false };

function filterConversations(conversations: Conversation[], scope: Scope, tab: Tab, query: string) {
  return conversations.filter((person) => {
    const matchesScope = scope === 'mine' ? person.owner === 'You' : scope === 'unassigned' ? person.owner === 'Unassigned' : true;
    const matchesTab = tab === 'resolved' ? person.status === 'Resolved' : person.status !== 'Resolved' && (tab !== 'unread' || person.unread > 0);
    return matchesScope && matchesTab && `${person.name} ${person.preview} ${person.company}`.toLowerCase().includes(query.trim().toLowerCase());
  }).sort((a, b) => (b.updatedAt ?? -b.id) - (a.updatedAt ?? -a.id));
}

const initialConversations: Conversation[] = [
  { id: 1, name: 'Alex Morgan', initials: 'AM', color: 'lavender', company: 'Acme Inc.', email: 'alex@acme.example', phone: '+1 (202) 555-0142', location: 'San Francisco, US', preview: 'Hi, I need help with my invoice.', time: '2m', unread: 0, owner: 'You', department: 'Billing', status: 'Open', firstMessage: 'Hi, I need help with my invoice. Could you send me a copy for last month?', reply: 'Hey Alex! Of course. Let me pull up your invoice and get that sorted for you. 😊', messages: [] },
  { id: 2, name: 'Sarah Chen', initials: 'SC', color: 'coral', company: 'Studio North', email: 'sarah@studionorth.example', phone: '+1 (202) 555-0187', location: 'Seattle, US', preview: 'That sounds great, thank you!', time: '5m', unread: 2, owner: 'You', department: 'Sales', status: 'Open', firstMessage: 'We’re looking for a shared inbox for our team. Can we get a quick demo?', reply: 'Absolutely, Sarah! I can help you find the right setup for your team. How many people will be using the inbox?', messages: [] },
  { id: 3, name: 'James Wilson', initials: 'JW', color: 'blue', company: 'Orbit Labs', email: 'james@orbit.example', phone: '+44 7700 900142', location: 'London, UK', preview: 'Can you help me get started?', time: '12m', unread: 1, owner: 'Unassigned', department: 'Support', status: 'Open', firstMessage: 'Hi there! I just connected our account. Can you help me get started?', reply: 'Welcome, James! Let’s set up your team inbox. You can begin by inviting your teammates from Settings.', messages: [] },
  { id: 4, name: 'Priya Sharma', initials: 'PS', color: 'mint', company: 'Bloom & Co.', email: 'priya@bloom.example', phone: '+1 (202) 555-0139', location: 'New York, US', preview: 'I’d like to explore the Pro plan.', time: '24m', unread: 0, owner: 'Emma Wilson', department: 'Sales', status: 'Pending', firstMessage: 'Hello! I’d like to explore the Pro plan for our growing team.', reply: 'Hi Priya! Happy to help. Tell me a little about your team and the workflows you’d like to simplify.', messages: [] },
  { id: 5, name: 'Daniel Kim', initials: 'DK', color: 'amber', company: 'Fieldwork', email: 'daniel@fieldwork.example', phone: '+1 (202) 555-0164', location: 'Austin, US', preview: 'Is there an update on my request?', time: '38m', unread: 0, owner: 'Unassigned', department: 'Support', status: 'Open', firstMessage: 'Hi, is there an update on my account setup request?', reply: 'Thanks for checking in, Daniel. I’m looking into your request and will help you with the next steps.', messages: [] },
];

function Avatar({ person, small = false }: { person: Conversation; small?: boolean }) {
  return <span className={`pm-avatar pm-avatar-${person.color}${small ? ' pm-avatar-small' : ''}`}>{person.initials}</span>;
}

export default function ProductMockup() {
  const [conversations, setConversations] = useState(initialConversations);
  const [selectedId, setSelectedId] = useState<number | null>(1);
  const [query, setQuery] = useState('');
  const [scope, setScope] = useState<Scope>('all');
  const [tab, setTab] = useState<Tab>('active');
  const [composers, setComposers] = useState<Record<number, Composer>>({});
  const [mobilePanel, setMobilePanel] = useState<'conversations' | 'chat'>('chat');
  const [showDetails, setShowDetails] = useState(false);
  const chatThreadRef = useRef<HTMLDivElement>(null);
  const detailsRef = useRef<HTMLDivElement>(null);
  const detailsToggleRef = useRef<HTMLButtonElement>(null);
  const detailsId = useId();
  const selected = conversations.find((person) => person.id === selectedId);
  const composer = selected ? composers[selected.id] ?? emptyComposer : emptyComposer;
  const isNote = composer.isNote;
  const draft = isNote ? composer.note : composer.reply;
  const active = conversations.filter((person) => person.status !== 'Resolved');
  const scoped = conversations.filter((person) => scope === 'mine' ? person.owner === 'You' : scope === 'unassigned' ? person.owner === 'Unassigned' : true);
  const filtered = filterConversations(conversations, scope, tab, query);
  const unreadCount = active.reduce((count, person) => count + person.unread, 0);

  useEffect(() => {
    const thread = chatThreadRef.current;
    if (thread) thread.scrollTop = selected?.messages.length ? thread.scrollHeight : 0;
  }, [selected?.id, selected?.messages.length]);

  useEffect(() => {
    if (!showDetails) return;
    detailsRef.current?.querySelector<HTMLButtonElement>('button')?.focus();
    function dismissDetails(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape') {
        setShowDetails(false);
        detailsToggleRef.current?.focus();
      }
    }
    function closeOutside(event: PointerEvent) {
      if (event.target instanceof Node && !detailsRef.current?.contains(event.target) && !detailsToggleRef.current?.contains(event.target)) setShowDetails(false);
    }
    document.addEventListener('keydown', dismissDetails);
    document.addEventListener('pointerdown', closeOutside);
    return () => {
      document.removeEventListener('keydown', dismissDetails);
      document.removeEventListener('pointerdown', closeOutside);
    };
  }, [showDetails]);

  function updateComposer(update: Partial<Composer>) {
    if (!selected) return;
    setComposers((current) => ({ ...current, [selected.id]: { ...(current[selected.id] ?? emptyComposer), ...update } }));
  }

  function setDraft(text: string) {
    updateComposer(isNote ? { note: text } : { reply: text });
  }

  function setIsNote(note: boolean) {
    updateComposer({ isNote: note });
  }

  function changeView(nextScope = scope, nextTab = tab, nextQuery = query, records = conversations) {
    setScope(nextScope);
    setTab(nextTab);
    setQuery(nextQuery);
    if (!filterConversations(records, nextScope, nextTab, nextQuery).some((person) => person.id === selectedId)) {
      setSelectedId(null);
      setShowDetails(false);
    }
  }

  function updateSelected(update: Partial<Conversation>) {
    setConversations((current) => current.map((person) => person.id === selectedId ? { ...person, ...update } : person));
  }

  function assignOwner(owner: string) {
    const next = conversations.map((person) => person.id === selectedId ? { ...person, owner } : person);
    setConversations(next);
    changeView(scope, tab, query, next);
  }

  function changeScope(next: Scope) {
    changeView(next, 'active', '');
    setMobilePanel('conversations');
  }

  function browseConversations() {
    changeView('all', active.length ? 'active' : 'resolved', '');
    setMobilePanel('conversations');
  }

  function chooseConversation(person: Conversation) {
    setSelectedId(person.id);
    setConversations((current) => current.map((item) => item.id === person.id ? { ...item, unread: 0 } : item));
    setShowDetails(false);
    setMobilePanel('chat');
  }

  function sendMessage(event?: FormEvent) {
    event?.preventDefault();
    const text = draft.trim();
    if (!text || !selected) return;
    setConversations((current) => current.map((person) => person.id === selected.id ? { ...person, messages: [...person.messages, { text, note: isNote }], updatedAt: Date.now(), ...(isNote ? {} : { preview: text, time: 'Now' }) } : person));
    setDraft('');
  }

  function handleComposerKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      sendMessage();
    }
  }

  const customerDetails = selected && <>
    <div className="pm-profile">
      <Avatar person={selected} />
      <strong>{selected.name}</strong>
      <span>{selected.company}</span>
      <span className="pm-customer-tag">Customer</span>
    </div>
    <div className="pm-detail-section">
      <h4>Conversation details</h4>
      <label className="pm-detail-field"><span>Assigned to</span><span className="pm-detail-select"><span className="pm-agent-dot">{selected.owner === 'Unassigned' ? '?' : selected.owner === 'You' ? 'JD' : 'EW'}</span><select aria-label="Assign conversation to agent" value={selected.owner} onChange={(event) => assignOwner(event.target.value)}><option>You</option><option>Emma Wilson</option><option>Unassigned</option></select><ChevronDown size={11} /></span></label>
      <label className="pm-detail-field"><span>Department</span><span className="pm-detail-select"><span className="pm-purple-dot" /><select aria-label="Assign conversation to department" value={selected.department} onChange={(event) => updateSelected({ department: event.target.value })}><option>Billing</option><option>Sales</option><option>Support</option></select><ChevronDown size={11} /></span></label>
    </div>
    <div className="pm-detail-section pm-contact-fields"><h4>Contact information</h4><dl><dt>Email</dt><dd>{selected.email}</dd><dt>Phone</dt><dd>{selected.phone}</dd><dt>Location</dt><dd>{selected.location}</dd></dl></div>
    <div className="pm-detail-section"><h4>Tags</h4><div className="pm-tags"><span>Customer</span><span>Priority</span></div></div>
  </>;

  return (
    <div className="pm-shell" data-mobile-panel={mobilePanel} aria-label="Interactive Convernix product preview">
      <div className="pm-app-bar">
        <div className="pm-app-brand"><span className="pm-brand-icon"><MessageSquareText size={15} strokeWidth={2.4} /></span><strong>Convernix</strong><span className="pm-app-divider">/</span><span className="pm-workspace-name">Team workspace</span><ChevronDown className="pm-workspace-chevron" size={11} /></div>
        <span className="pm-preview-label"><span />Interactive preview <span className="pm-preview-sample">· sample data</span></span>
        <span className="pm-user-avatar" title="Preview account: Jamie Davis">JD</span>
      </div>

      <div className="pm-mobile-tabs" aria-label="Preview view"><button type="button" aria-pressed={mobilePanel === 'conversations'} onClick={() => { setMobilePanel('conversations'); setShowDetails(false); }}><Inbox size={14} />Conversations<span>{active.length}</span></button><button type="button" aria-pressed={mobilePanel === 'chat'} onClick={() => setMobilePanel('chat')}><MessageCircle size={14} />Chat</button></div>

      <div className="pm-workspace">
        <aside className="pm-sidebar" aria-label="Preview navigation">
          <div className="pm-sidebar-main">
            <div className="pm-sidebar-workspace"><span className="pm-team-logo"><LayoutGrid size={16} /></span><div><strong>Acme workspace</strong><span>Pro plan</span></div><ChevronsUpDown size={11} /></div>
            <span className="pm-nav-label">WORKSPACE</span>
            <nav className="pm-nav">
              <button type="button" aria-pressed={scope === 'all'} className={scope === 'all' ? 'pm-nav-active' : ''} onClick={() => changeScope('all')}><Inbox size={15} /><span>Team inbox</span><b>{active.length}</b></button>
              <button type="button" aria-pressed={scope === 'mine'} className={scope === 'mine' ? 'pm-nav-active' : ''} onClick={() => changeScope('mine')}><MessageCircle size={15} /><span>My conversations</span><small>{active.filter((person) => person.owner === 'You').length}</small></button>
              <button type="button" aria-pressed={scope === 'unassigned'} className={scope === 'unassigned' ? 'pm-nav-active' : ''} onClick={() => changeScope('unassigned')}><UsersRound size={15} /><span>Unassigned</span><small>{active.filter((person) => person.owner === 'Unassigned').length}</small></button>
              <a href="#departments"><LayoutGrid size={15} /><span>Departments</span></a>
              <a href="#features"><ContactRound size={15} /><span>Contacts</span></a>
            </nav>
            <span className="pm-nav-label pm-manage-label">MANAGE</span>
            <nav className="pm-nav"><a href="#templates"><FileText size={15} /><span>Templates</span></a><a href="#automation"><Workflow size={15} /><span>Automation</span><Sparkles className="pm-nav-sparkle" size={11} /></a><a href="#analytics"><LayoutGrid size={15} /><span>Reports</span></a><a href="#security"><Settings2 size={15} /><span>Settings</span></a></nav>
          </div>
          <div className="pm-sidebar-bottom"><span className="pm-channel-status"><span />WhatsApp connected</span><a href="#faq"><CircleHelp size={14} />Help & resources<ArrowUpRight size={12} /></a></div>
        </aside>

        <section className="pm-conversations" aria-label="Sample conversations">
          <div className="pm-list-heading"><h3>{scope === 'mine' ? 'My conversations' : scope === 'unassigned' ? 'Unassigned' : 'Team inbox'}<span>{filtered.length}</span></h3><Inbox size={16} aria-hidden="true" /></div>
          <label className="pm-search"><Search size={14} /><input aria-label="Search sample conversations" placeholder="Search conversations" value={query} onChange={(event) => changeView(scope, tab, event.target.value)} /><span>⌕</span></label>
          <div className="pm-list-tabs" aria-label="Filter conversations"><button type="button" aria-pressed={tab === 'active'} onClick={() => changeView(scope, 'active')}>All<span>{scoped.filter((person) => person.status !== 'Resolved').length}</span></button><button type="button" aria-pressed={tab === 'unread'} onClick={() => changeView(scope, 'unread')}>Unread</button><button type="button" aria-pressed={tab === 'resolved'} onClick={() => changeView(scope, 'resolved')}>Resolved</button></div>
          <div className="pm-list-sort"><span>{filtered.length} conversation{filtered.length === 1 ? '' : 's'}</span><span>Newest first<ArrowDown size={10} /></span></div>
          <div className="pm-conversation-items">
            {filtered.map((person) => <button className={`pm-conversation${selectedId === person.id ? ' pm-conversation-active' : ''}`} type="button" key={person.id} aria-pressed={selectedId === person.id} onClick={() => chooseConversation(person)}><span className="pm-avatar-wrap"><Avatar person={person} small /><span className="pm-whatsapp-mark"><MessageCircle size={8} fill="currentColor" /></span></span><span className="pm-conversation-content"><span className="pm-conversation-top"><strong>{person.name}</strong><time>{person.time}</time></span><span className="pm-conversation-preview">{person.preview}</span><span className="pm-conversation-meta"><span><span className={`pm-dept-dot pm-dept-${person.department.toLowerCase()}`} />{person.department}</span>{person.unread > 0 && <b>{person.unread}</b>}{person.status === 'Resolved' && <Check size={12} />}</span></span></button>)}
            {filtered.length === 0 && <div className="pm-empty" role="status"><Search size={23} /><strong>No conversations found</strong><span>{query ? 'Try a different name or message.' : 'No conversations in this view.'}</span><button type="button" onClick={browseConversations}>View all conversations<ArrowRight size={12} /></button></div>}
          </div>
          <div className="pm-inbox-footer"><CheckCheck size={12} /><span>{unreadCount ? `${unreadCount} unread message${unreadCount === 1 ? '' : 's'} across your inbox` : 'You’re all caught up'}</span></div>
        </section>

        <section className="pm-chat" aria-label={selected ? `Conversation with ${selected.name}` : 'Conversation preview'}>
          {selected ? <>
          <div className="pm-chat-header"><Avatar person={selected} small /><div className="pm-chat-person"><strong>{selected.name}</strong><span><span />WhatsApp</span></div><div className={`pm-status-select pm-status-${selected.status.toLowerCase()}`}><span className="pm-status-dot" /><select aria-label="Conversation status" value={selected.status} onChange={(event) => { const status = event.target.value as Status; updateSelected({ status }); setTab(status === 'Resolved' ? 'resolved' : 'active'); }}><option>Open</option><option>Pending</option><option>Resolved</option></select><ChevronDown size={11} /></div><button ref={detailsToggleRef} className="pm-details-toggle" type="button" aria-label={showDetails ? 'Close customer details' : 'Show customer details'} aria-expanded={showDetails} aria-controls={showDetails ? detailsId : undefined} onClick={() => setShowDetails((current) => !current)}><MoreHorizontal size={18} /></button></div>
          {showDetails && <div ref={detailsRef} id={detailsId} className="pm-inline-details" role="region" aria-label="Customer details"><div className="pm-inline-details-heading"><span>Contact details</span><button type="button" aria-label="Close customer details" onClick={() => { setShowDetails(false); detailsToggleRef.current?.focus(); }}><X size={14} /></button></div>{customerDetails}</div>}
          <div ref={chatThreadRef} className="pm-chat-thread" role="log" aria-live="polite" aria-label="Preview message history">
            <div className="pm-day-divider"><span />Today<span /></div>
            <div className="pm-received"><Avatar person={selected} small /><div><div className="pm-bubble pm-bubble-incoming">{selected.firstMessage}</div><span className="pm-message-time">09:41 AM</span></div></div>
            <div className="pm-routing"><span className="pm-routing-icon"><Workflow size={11} /></span><span>Routed to <strong>{selected.department}</strong> department</span></div>
            <div className="pm-outgoing"><div className="pm-reply-author">Jamie Davis<span>Agent</span></div><div className="pm-bubble pm-bubble-outgoing">{selected.reply}</div><span className="pm-message-time">09:42 AM<CheckCheck size={12} /></span></div>
            <div className="pm-assignment"><span className="pm-tiny-agent">{selected.owner === 'Emma Wilson' ? 'EW' : selected.owner === 'Unassigned' ? '?' : 'JD'}</span>{selected.owner === 'Unassigned' ? 'Waiting for an available teammate' : <span>Currently assigned to {selected.owner === 'You' ? 'Jamie Davis (you)' : selected.owner}</span>}</div>
            {selected.messages.map((message, index) => <div className={message.note ? 'pm-local-note' : 'pm-outgoing pm-added-message'} key={`${selected.id}-${index}`}>{message.note && <span><StickyNote size={12} />Internal note · Only visible to your team</span>}<div className={message.note ? '' : 'pm-bubble pm-bubble-outgoing'}>{message.text}</div><span className="pm-message-time">Just now{!message.note && <Check size={12} />}</span></div>)}
          </div>
          <form className={`pm-composer${isNote ? ' pm-composer-note' : ''}`} onSubmit={sendMessage}>
            <div className="pm-composer-tabs"><button type="button" aria-pressed={!isNote} onClick={() => setIsNote(false)}><MessageCircle size={12} />Reply</button><button type="button" aria-pressed={isNote} onClick={() => setIsNote(true)}><LockKeyhole size={11} />Internal note</button></div>
            <textarea aria-label={isNote ? 'Write an internal note' : 'Write a preview reply'} placeholder={isNote ? 'Add a note for your team…' : `Reply to ${selected.name.split(' ')[0]}…`} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={handleComposerKey} rows={2} />
            <div className="pm-composer-bottom"><span><ShieldCheck size={11} />Local preview</span><button className="pm-send-button" type="submit" disabled={!draft.trim()}>{isNote ? 'Add note' : 'Send'}<Send size={12} /></button></div>
          </form>
          <div className="pm-chat-footer"><Bot size={11} /><span>Powered by Convernix. Built for your team.</span></div>
          </> : <div className="pm-chat-empty"><span><MessageSquareText size={26} /></span><strong>{filtered.length ? 'Select a conversation' : 'A little room to breathe.'}</strong><p>{filtered.length ? 'Choose a customer to explore the shared inbox.' : 'There are no conversations matching this view.'}</p><button type="button" onClick={browseConversations}>Browse conversations<ArrowRight size={13} /></button></div>}
        </section>

        <aside className="pm-customer-details" aria-label="Customer details"><div className="pm-details-heading">Contact details<ContactRound size={14} /></div>{customerDetails || <div className="pm-details-empty">Select a conversation to view customer details.</div>}</aside>
      </div>
    </div>
  );
}
