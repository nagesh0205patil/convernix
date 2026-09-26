import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'
import Convernix from './convernix/App.tsx'
import './convernix/styles.css'
import './convernix/auth.css'
import TenantAdministrationConsole from './admin/TenantAdministrationConsole'
import './admin/admin.css'
import CrmModule from './crm/CrmModule'
import './crm/crm.css'
import {
  ArrowDown,
  ArrowUpRight,
  BadgeCheck,
  BarChart3,
  BellRing,
  Bot,
  BriefcaseBusiness,
  Building2,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  ChevronsUpDown,
  CircleHelp,
  ContactRound,
  CreditCard,
  Eye,
  FileClock,
  FileText,
  Fingerprint,
  Globe,
  Inbox,
  Kanban,
  KeyRound,
  LayoutGrid,
  LockKeyhole,
  LogOut,
  MessageCircle,
  MessageSquareText,
  Paperclip,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  Send,
  Settings2,
  Shield,
  ShieldCheck,
  Smile,
  Sparkles,
  StickyNote,
  TrendingUp,
  UserCog,
  UserRound,
  UsersRound,
  Workflow,
  X,
} from 'lucide-react'

const API = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')
const number = new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 1 })
const date = new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
const blankStats = { total_campaigns: 0, total_sent: 0, total_delivered: 0, total_opened: 0, total_clicked: 0 }
const blankCampaign = { name: '', message: '', target_audience: 'All customers', status: 'draft', scheduled_at: '' }
const blankMember = { email: '', role: 'viewer', number_access: 'both' }
const blankAnalytics = {
  totals: { enquiries: 0, campaigns: 0, sent: 0, delivered: 0, opened: 0, clicked: 0 },
  trend: { enquiries: [], campaigns: [] },
  enquiry_statuses: [],
  enquiry_teams: [],
  campaign_statuses: [],
}
const emojis = ['😀', '😂', '😊', '😍', '👍', '🙏', '🎉', '❤️', '✅', '🔥', '👏', '🤝', '😢', '😮', '💯', '📎']
const avatarColors = ['#514063', '#684a46', '#394e66', '#34534d', '#66513c', '#4a3861', '#2f495e']

function getAvatarColor(name = '') {
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return avatarColors[Math.abs(hash) % avatarColors.length]
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const d = new Date(timestamp)
  const now = new Date()
  const diffMs = now - d
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h`
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
}

const list = (data) => (Array.isArray(data) ? data : data?.results || [])
const personName = (u) => [u?.first_name, u?.last_name].filter(Boolean).join(' ') || u?.name || u?.username || u?.email || 'User'
const initials = (u) => `${u?.first_name?.[0] || u?.name?.[0] || u?.email?.[0] || 'U'}${u?.last_name?.[0] || ''}`.toUpperCase()
const roleName = (role) => ({ viewer: 'Viewer', editor: 'Editor', admin: 'Administrator', owner: 'Owner' }[role] || role)
const numberAccessName = (access) => ({ india: 'India only', us: 'US only', both: 'India and US' }[access] || 'India and US')

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('crm_access_token') || '')
  const [user, setUser] = useState(null)
  const [tenant, setTenant] = useState(null)
  const [platformTenants, setPlatformTenants] = useState([])
  const [page, setPage] = useState('inbox')
  const [busy, setBusy] = useState(false)
  const [login, setLogin] = useState({ email: '', password: '' })
  const [notice, setNotice] = useState(null)
  const [modal, setModal] = useState(null)
  const [adminSection, setAdminSection] = useState('overview')
  const [adminSettingsTab, setAdminSettingsTab] = useState('organization')
  const [adminIamTab, setAdminIamTab] = useState('users')
  const [adminAccountTab, setAdminAccountTab] = useState('subscription')
  const [query, setQuery] = useState('')
  const [_stats, setStats] = useState(blankStats)
  const [campaigns, setCampaigns] = useState([])
  const [enquiries, setEnquiries] = useState([])
  const [teams, setTeams] = useState([])
  const [members, setMembers] = useState([])
  const [enquiryPage, setEnquiryPage] = useState(1)
  const [enquiryPageSize, setEnquiryPageSize] = useState(20)
  const [enquiryCount, setEnquiryCount] = useState(0)
  const [enquiryRefresh, setEnquiryRefresh] = useState(0)
  const [conversations, setConversations] = useState([])
  const [activeConversation, setActiveConversation] = useState(null)
  const [businessNumbers, setBusinessNumbers] = useState([])
  const [selectedBusiness, setSelectedBusiness] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem('crm_business_number'))
    } catch {
      return null
    }
  })
  const [channel, setChannel] = useState({
    number: '',
    phone_number_id: '',
    forwarding_number: '',
    label: '',
    default_team: 'Support',
    is_active: true,
  })
  const [campaignForm, setCampaignForm] = useState(blankCampaign)
  const [memberForm, setMemberForm] = useState(blankMember)
  const [exportForm, setExportForm] = useState({ range: 'week', start_date: '', end_date: '' })
  const [selectedEnquiry, setSelectedEnquiry] = useState(null)
  const [providers, setProviders] = useState({ google: { enabled: false }, microsoft: { enabled: false } })
  const [analytics, setAnalytics] = useState(blankAnalytics)
  const [period, setPeriod] = useState({ year: String(new Date().getFullYear()), month: '' })

  const toast = (text, type = 'success') => setNotice({ text, type })
  useEffect(() => {
    if (!notice) return
    const id = setTimeout(() => setNotice(null), 4000)
    return () => clearTimeout(id)
  }, [notice])

  useEffect(() => {
    if (!token)
      fetch(`${API}/auth/providers/`)
        .then((r) => r.json())
        .then(setProviders)
        .catch(() => {})
  }, [token])

  useEffect(() => {
    const handleRoute = () => {
      const hash = window.location.hash.replace(/^#\/?/, '')
      const path = window.location.pathname.replace(/^\//, '')
      const target = hash || path
      if (
        target.startsWith('leads') ||
        target.startsWith('customers') ||
        target.startsWith('pipeline') ||
        target.startsWith('crm')
      ) {
        setPage('crm')
      }
    }
    handleRoute()
    window.addEventListener('hashchange', handleRoute)
    window.addEventListener('popstate', handleRoute)
    return () => {
      window.removeEventListener('hashchange', handleRoute)
      window.removeEventListener('popstate', handleRoute)
    }
  }, [])

  const api = useCallback(
    async (path, options = {}) => {
      const isForm = options.body instanceof FormData
      const response = await fetch(`${API}${path}`, {
        ...options,
        headers: {
          ...(!isForm ? { 'Content-Type': 'application/json' } : {}),
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(selectedBusiness?.id ? { 'X-Business-Number-ID': String(selectedBusiness.id) } : {}),
          ...options.headers,
        },
      })
      if (response.status === 401 && token) {
        localStorage.removeItem('crm_access_token')
        setToken('')
        setUser(null)
        throw new Error('Your session expired. Please sign in again.')
      }
      if (!response.ok) {
        let message = `Request failed (${response.status})`
        try {
          const data = await response.json()
          message = data.detail || Object.values(data).flat().join(' ') || message
        } catch {
          /* no body */
        }
        throw new Error(message)
      }
      return response.status === 204 ? null : response.json()
    },
    [token, selectedBusiness?.id],
  )

  const load = useCallback(async () => {
    if (!token) return
    setBusy(true)
    try {
      const me = await api('/auth/me/')
      setUser(me)
      try {
        const myTenant = await api('/tenant/me/')
        setTenant(myTenant)
      } catch {
        if (me.tenant) setTenant(me.tenant)
      }
      if (me.is_superuser) {
        try {
          const pt = await api('/platform/tenants/')
          setPlatformTenants(list(pt))
        } catch {
          /* non-blocking */
        }
      }
      const available = list(await api('/whatsapp/business-numbers/'))
      setBusinessNumbers(available)
      if (!selectedBusiness) return
      if (!available.some((item) => item.id === selectedBusiness.id)) {
        sessionStorage.removeItem('crm_business_number')
        setSelectedBusiness(null)
        return
      }
      const [s, c, e, t, m] = await Promise.all([
        api('/campaigns/stats/'),
        api('/campaigns/'),
        api('/whatsapp/enquiries/'),
        api('/team-directory/'),
        api('/inbox/conversations/'),
      ])
      setStats(s || blankStats)
      setCampaigns(list(c))
      setEnquiries(list(e))
      setEnquiryCount(e?.count ?? list(e).length)
      setTeams(t?.teams || [])
      setConversations(list(m))
      if (me.is_staff || ['admin', 'owner'].includes(me.role)) {
        const [people, settings] = await Promise.all([
          api('/team-members/'),
          api('/whatsapp/settings/').catch(() => null),
        ])
        setMembers(list(people))
        if (settings) setChannel(settings)
      }
    } catch (error) {
      toast(error.message, 'error')
    } finally {
      setBusy(false)
    }
  }, [api, token, selectedBusiness])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!token || !selectedBusiness || page !== 'contacts') return
    let active = true
    const timer = setTimeout(
      async () => {
        setBusy(true)
        try {
          const params = new URLSearchParams({ page: String(enquiryPage), page_size: String(enquiryPageSize) })
          if (query.trim()) params.set('search', query.trim())
          const data = await api(`/whatsapp/enquiries/?${params}`)
          if (active) {
            setEnquiries(list(data))
            setEnquiryCount(data?.count ?? list(data).length)
          }
        } catch (error) {
          if (active) toast(error.message, 'error')
        } finally {
          if (active) setBusy(false)
        }
      },
      query ? 300 : 0,
    )
    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [api, token, selectedBusiness, page, enquiryPage, enquiryPageSize, query, enquiryRefresh])

  useEffect(() => {
    if (!token || !selectedBusiness || page !== 'contacts') return
    const timer = setInterval(() => setEnquiryRefresh((value) => value + 1), 5000)
    return () => clearInterval(timer)
  }, [token, selectedBusiness, page])

  useEffect(() => {
    if (!token || !selectedBusiness) return
    let active = true
    api(`/analytics/dashboard/?year=${period.year}${period.month ? `&month=${period.month}` : ''}`)
      .then((data) => active && setAnalytics(data))
      .catch((error) => toast(error.message, 'error'))
    return () => {
      active = false
    }
  }, [api, token, selectedBusiness, period])

  useEffect(() => {
    if (!token || !selectedBusiness || !['inbox', 'mine', 'unassigned'].includes(page)) return
    let mounted = true,
      running = false
    const sync = async () => {
      if (running) return
      running = true
      try {
        const inbox = list(await api('/inbox/conversations/'))
        if (mounted) setConversations(inbox)
        if (activeConversation?.id) {
          const detail = await api(`/inbox/conversations/${activeConversation.id}/`)
          if (mounted) setActiveConversation((current) => (current?.id === detail.id ? detail : current))
        }
      } catch {
        /* Polling catch */
      } finally {
        running = false
      }
    }
    sync()
    const timer = setInterval(sync, 4000)
    const onFocus = () => sync()
    window.addEventListener('focus', onFocus)
    return () => {
      mounted = false
      clearInterval(timer)
      window.removeEventListener('focus', onFocus)
    }
  }, [api, token, selectedBusiness, page, activeConversation?.id])

  // SSE real-time hook — supplements polling with push-based updates
  useEffect(() => {
    if (!token || !selectedBusiness || !['inbox', 'mine', 'unassigned'].includes(page)) return
    const bizHeader = selectedBusiness?.id ? `&biz=${selectedBusiness.id}` : ''
    // EventSource doesn't support custom headers — pass token as query param
    // The backend validates it via query string fallback when Authorization header missing
    const url = `${API}/inbox/events/?token=${encodeURIComponent(token)}${bizHeader}`
    let es
    try {
      es = new EventSource(url)
      es.addEventListener('conversation.updated', (e) => {
        try {
          const updated = JSON.parse(e.data)
          setConversations((prev) => {
            const exists = prev.some((c) => c.id === updated.id)
            if (exists) return prev.map((c) => (c.id === updated.id ? { ...c, ...updated } : c))
            return [updated, ...prev]
          })
        } catch { /* parse error */ }
      })
      es.addEventListener('message.received', (e) => {
        try {
          const { conversationId } = JSON.parse(e.data)
          // Mark conversation as having new messages — polling will refresh detail
          setConversations((prev) =>
            prev.map((c) =>
              c.id === conversationId
                ? { ...c, unread_count: (c.unread_count || 0) + 1 }
                : c,
            ),
          )
        } catch { /* parse error */ }
      })
    } catch { /* SSE not supported or blocked */ }
    return () => { try { es?.close() } catch { /* ignore */ } }
  }, [token, selectedBusiness, page])

  async function signIn(event) {
    event.preventDefault()
    setBusy(true)
    try {
      const response = await fetch(`${API}/auth/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(login),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Incorrect email or password')
      localStorage.setItem('crm_access_token', data.access)
      sessionStorage.removeItem('crm_business_number')
      setSelectedBusiness(null)
      setUser(data.user)
      if (data.user?.tenant) setTenant(data.user.tenant)
      setToken(data.access)
    } catch (error) {
      toast(error.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  async function registerTenant(form) {
    setBusy(true)
    try {
      const response = await fetch(`${API}/auth/register-tenant/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await response.json()
      if (!response.ok) {
        const errorMsg = data.detail || (data.email ? data.email[0] : null) || (data.company_name ? data.company_name[0] : null) || 'Unable to register workspace'
        throw new Error(errorMsg)
      }
      localStorage.setItem('crm_access_token', data.access)
      sessionStorage.removeItem('crm_business_number')
      setSelectedBusiness(null)
      setUser(data.user)
      if (data.tenant) setTenant(data.tenant)
      setToken(data.access)
      toast(`Welcome to Convernix! ${data.tenant.name} workspace created.`)
    } catch (error) {
      toast(error.message, 'error')
      throw error
    } finally {
      setBusy(false)
    }
  }

  function logout() {
    localStorage.removeItem('crm_access_token')
    sessionStorage.removeItem('crm_business_number')
    setSelectedBusiness(null)
    setToken('')
    setUser(null)
    setTenant(null)
    setPlatformTenants([])
    setPage('inbox')
  }

  async function changeTenantTier(tenantId, newTier) {
    setBusy(true)
    try {
      const updated = await api(`/platform/tenants/${tenantId}/`, {
        method: 'PATCH',
        body: JSON.stringify({ tier: newTier }),
      })
      setPlatformTenants((items) => items.map((item) => (item.id === tenantId ? updated : item)))
      if (tenant?.id === tenantId) setTenant(updated)
      toast(`Tenant plan updated to ${updated.tier_display}`)
    } catch (error) {
      toast(error.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  async function toggleTenantStatus(tenantId, currentStatus) {
    const newStatus = currentStatus === 'active' ? 'suspended' : 'active'
    setBusy(true)
    try {
      const updated = await api(`/platform/tenants/${tenantId}/`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      })
      setPlatformTenants((items) => items.map((item) => (item.id === tenantId ? updated : item)))
      if (tenant?.id === tenantId) setTenant(updated)
      toast(`Tenant is now ${updated.status_display}`)
    } catch (error) {
      toast(error.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  async function deletePlatformTenant(tenantId, tenantName) {
    if (!confirm(`Are you sure you want to delete workspace "${tenantName}"? This will permanently delete this tenant.`)) return
    setBusy(true)
    try {
      await api(`/platform/tenants/${tenantId}/`, { method: 'DELETE' })
      setPlatformTenants((items) => items.filter((item) => item.id !== tenantId))
      toast(`Tenant "${tenantName}" removed`)
    } catch (error) {
      toast(error.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  async function handleCreatePlatformTenant(data) {
    setBusy(true)
    try {
      const created = await api('/platform/tenants/', {
        method: 'POST',
        body: JSON.stringify(data),
      })
      setPlatformTenants((items) => [created, ...items])
      setModal(null)
      toast(`Workspace "${created.name}" provisioned`)
    } catch (error) {
      toast(error.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  function selectBusiness(item) {
    sessionStorage.setItem('crm_business_number', JSON.stringify(item))
    setSelectedBusiness(item)
    setPage('inbox')
    setQuery('')
    setActiveConversation(null)
  }

  function leaveBusiness() {
    sessionStorage.removeItem('crm_business_number')
    setSelectedBusiness(null)
    setActiveConversation(null)
    setCampaigns([])
    setEnquiries([])
    setConversations([])
  }

  async function createCampaign(event) {
    event.preventDefault()
    setBusy(true)
    try {
      const created = await api('/campaigns/', {
        method: 'POST',
        body: JSON.stringify({ ...campaignForm, scheduled_at: campaignForm.scheduled_at || null }),
      })
      setCampaigns((v) => [created, ...v])
      setStats((v) => ({ ...v, total_campaigns: v.total_campaigns + 1 }))
      setCampaignForm(blankCampaign)
      setModal(null)
      toast('Campaign created successfully')
    } catch (error) {
      toast(error.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  async function deleteCampaign(id) {
    if (!confirm('Delete this campaign? This cannot be undone.')) return
    try {
      await api(`/campaigns/${id}/`, { method: 'DELETE' })
      setCampaigns((v) => v.filter((x) => x.id !== id))
      toast('Campaign deleted')
    } catch (error) {
      toast(error.message, 'error')
    }
  }

  async function createMember(event) {
    event.preventDefault()
    setBusy(true)
    try {
      await api('/iam/invitations/', { method: 'POST', body: JSON.stringify(memberForm) })
      setMemberForm(blankMember)
      setModal(null)
      toast('IAM invitation sent by email')
      const people = await api('/team-members/')
      setMembers(list(people))
    } catch (error) {
      toast(error.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  async function saveMemberAccess(id, role, number_access) {
    try {
      const updated = await api(`/team-members/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ role, number_access }),
      })
      setMembers((items) => items.map((item) => (item.id === id ? updated : item)))
      toast('User permissions updated')
      return true
    } catch (error) {
      toast(error.message, 'error')
      return false
    }
  }

  async function deleteMember(id) {
    if (!confirm('Permanently delete this user? They will no longer be able to sign in.')) return
    try {
      await api(`/team-members/${id}/`, { method: 'DELETE' })
      setMembers((v) => v.filter((x) => x.id !== id))
      toast('User deleted successfully')
    } catch (error) {
      toast(error.message, 'error')
    }
  }

  async function saveChannel(event) {
    event.preventDefault()
    setBusy(true)
    try {
      setChannel(await api('/whatsapp/settings/', { method: 'PATCH', body: JSON.stringify(channel) }))
      toast('WhatsApp channel updated')
    } catch (error) {
      toast(error.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  async function downloadEnquiries(event) {
    event.preventDefault()
    setBusy(true)
    try {
      const params = new URLSearchParams({ range: exportForm.range })
      if (exportForm.range === 'custom') {
        if (!exportForm.start_date || !exportForm.end_date) throw new Error('Select both start and end dates.')
        params.set('start_date', exportForm.start_date)
        params.set('end_date', exportForm.end_date)
      }
      const response = await fetch(`${API}/whatsapp/enquiries/export/?${params}`, {
        headers: { Authorization: `Bearer ${token}`, 'X-Business-Number-ID': String(selectedBusiness.id) },
      })
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Unable to export enquiries')
      }
      const blob = await response.blob()
      const disposition = response.headers.get('Content-Disposition') || ''
      const filename = disposition.match(/filename="?([^";]+)"?/)?.[1] || 'enquiries.csv'
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      setModal(null)
      toast('CSV export downloaded')
    } catch (error) {
      toast(error.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  async function downloadReport(type) {
    setBusy(true)
    try {
      const response = await fetch(
        `${API}/analytics/export/?type=${type}&year=${period.year}${period.month ? `&month=${period.month}` : ''}`,
        {
          headers: { Authorization: `Bearer ${token}`, 'X-Business-Number-ID': String(selectedBusiness.id) },
        },
      )
      if (!response.ok) throw new Error('Unable to download report')
      const blob = await response.blob()
      const disposition = response.headers.get('Content-Disposition') || ''
      const filename = disposition.match(/filename="?([^";]+)"?/)?.[1] || `${type}_report.csv`
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      URL.revokeObjectURL(url)
      toast(`${type === 'campaigns' ? 'Campaign' : 'Enquiry'} report downloaded`)
    } catch (error) {
      toast(error.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const scrollToLatest = () =>
    requestAnimationFrame(() => {
      const thread = document.getElementById('workspace-chat-thread')
      if (thread) thread.scrollTo({ top: thread.scrollHeight, behavior: 'smooth' })
    })

  async function openConversation(item) {
    try {
      // Fetch full conversation detail from inbox API
      const conversation = await api(`/inbox/conversations/${item.id}/`)
      setActiveConversation(conversation)
      // Mark as read — fire-and-forget, don't block UX
      api(`/inbox/conversations/${item.id}/read/`, {
        method: 'POST',
        body: JSON.stringify({ last_read_message_id: item.last_message_id || '' }),
      }).catch(() => {})
      setConversations((items) => items.map((x) => (x.id === item.id ? { ...x, unread_count: 0 } : x)))
      setTimeout(scrollToLatest, 50)
    } catch (error) {
      toast(error.message, 'error')
    }
  }

  async function sendConversationMessage(message, files = []) {
    if (!activeConversation) return false
    setBusy(true)
    try {
      const body = files.length ? new FormData() : JSON.stringify({ message })
      if (files.length) {
        body.append('message', message)
        files.forEach((file) => body.append('files', file))
      }
      // Use inbox API send endpoint
      await api(`/inbox/conversations/${activeConversation.id}/messages/send/`, {
        method: 'POST',
        body,
      })
      // Refresh conversation detail to pick up the new message
      const updated = await api(`/inbox/conversations/${activeConversation.id}/`)
      setActiveConversation(updated)
      setConversations((items) =>
        items
          .map((x) => (x.id === updated.id ? updated : x))
          .sort((a, b) => new Date(b.last_message_at) - new Date(a.last_message_at)),
      )
      setTimeout(scrollToLatest, 50)
      return true
    } catch (error) {
      toast(error.message, 'error')
      return false
    } finally {
      setBusy(false)
    }
  }

  const filter = (items, fields) =>
    items.filter((item) => fields.map((f) => item[f]).join(' ').toLowerCase().includes(query.toLowerCase()))

  const visible = {
    enquiries,
    conversations: filter(conversations, [
      'customer_name',
      'phone_number',
      'customer_email',
      'reference',
      'team_name',
      'last_message',
    ]),
    campaigns: filter(campaigns, ['name', 'status', 'target_audience']),
    iam: filter(
      user?.role === 'admin' || user?.role === 'owner' || user?.is_staff
        ? members
        : teams.flatMap((x) => x.members || []),
      ['first_name', 'last_name', 'name', 'email', 'team_name'],
    ),
  }

  const unreadInboxCount = conversations.reduce((acc, c) => acc + (c.unread_count || 0), 0)
  const canAdmin = user?.role === 'admin' || user?.role === 'owner' || user?.is_staff
  const canWrite = ['editor', 'admin', 'owner'].includes(user?.role) || user?.is_staff

  const inviteToken = new URLSearchParams(window.location.search).get('invite')
  if (!token && inviteToken)
    return (
      <div className="convernix-workspace crm-workspace">
        <AcceptInvite token={inviteToken} />
      </div>
    )

  if (!token)
    return (
      <Convernix
        signIn={
          <Login
            login={login}
            setLogin={setLogin}
            submit={signIn}
            registerTenant={registerTenant}
            busy={busy}
            notice={notice}
            providers={providers}
          />
        }
      />
    )

  if (page === 'admin')
    return (
      <TenantAdministrationConsole
        currentUser={user}
        onBackToApp={() => {
          if (selectedBusiness) {
            setPage('inbox')
          } else if (businessNumbers && businessNumbers.length > 0) {
            selectBusiness(businessNumbers[0])
          } else {
            setPage('inbox')
          }
        }}
        onOpenInbox={() => {
          if (selectedBusiness) {
            setPage('inbox')
          } else if (businessNumbers && businessNumbers.length > 0) {
            selectBusiness(businessNumbers[0])
          } else {
            setPage('inbox')
          }
        }}
      />
    )

  if (!selectedBusiness) {
    if (!busy && (!businessNumbers || businessNumbers.length === 0)) {
      return (
        <TenantAdministrationConsole
          currentUser={user}
          onBackToApp={businessNumbers && businessNumbers.length > 0 ? () => {
            selectBusiness(businessNumbers[0])
          } : undefined}
          onOpenInbox={businessNumbers && businessNumbers.length > 0 ? () => {
            selectBusiness(businessNumbers[0])
          } : undefined}
        />
      )
    }

    return (
      <div className="convernix-workspace crm-workspace">
        <BusinessSelector
          access={user?.number_access}
          numbers={businessNumbers}
          select={selectBusiness}
          logout={logout}
          busy={busy}
          tenant={tenant}
          openQuotaModal={() => setModal('quota')}
          isSuperuser={user?.is_superuser}
          openTenants={() => {
            setSelectedBusiness({ id: 0, label: 'Platform Management', number: 'System' })
            setPage('tenants')
          }}
          openAdmin={() => setPage('admin')}
        />
        {modal === 'quota' && (
          <Modal title="Plan & Resource Quota" close={() => setModal(null)}>
            <QuotaModalContent tenant={tenant} />
          </Modal>
        )}
      </div>
    )
  }

  return (
    <div className="convernix-workspace crm-workspace">
      {/* Top App Bar */}
      <header className="pm-app-bar">
        <div className="pm-app-brand">
          <span className="pm-brand-icon">
            <MessageSquareText size={15} strokeWidth={2.4} />
          </span>
          <strong>Convernix</strong>
          <span className="pm-app-divider">/</span>
          <span className="pm-workspace-name">{tenant?.name || 'Team workspace'}</span>
          {tenant && (
            <span
              className={`pm-tier-badge pm-tier-${tenant.tier}`}
              onClick={() => setModal('quota')}
              title="Click to view plan and quota details"
            >
              {tenant.tier_display || tenant.tier?.toUpperCase()}
            </span>
          )}
        </div>

        <div className="pm-header-center">
          <div className="pm-number-badge">
            <span className="pm-live-dot" />
            <span>
              {selectedBusiness.label} ({selectedBusiness.number})
            </span>
            <button
              className="pm-number-switch-btn"
              onClick={leaveBusiness}
              title="Switch WhatsApp number"
            >
              Switch number
            </button>
          </div>
        </div>

        <div className="pm-header-actions">
          <button
            className="pm-tool-btn"
            onClick={page === 'contacts' ? () => setEnquiryRefresh((v) => v + 1) : load}
            title="Refresh workspace"
          >
            <RefreshCw size={14} />
          </button>
          <div className="pm-header-user">
            <span className="pm-user-avatar" title={personName(user)}>
              {initials(user)}
            </span>
            <div className="pm-user-meta">
              <strong>{personName(user)}</strong>
              <small>
                {user?.role} · {user?.team_name || 'All teams'}
              </small>
            </div>
          </div>
          <button className="pm-logout-btn" onClick={logout} title="Sign out of Convernix">
            <LogOut size={14} />
          </button>
        </div>
      </header>

      {/* Main Workspace Shell */}
      <div className="pm-main-shell">
        {/* Sidebar */}
        <aside className="pm-sidebar">
          <div className="pm-sidebar-main">
            <div
              className="pm-sidebar-workspace"
              onClick={() => setModal('quota')}
              style={{ cursor: 'pointer' }}
              title="View Plan & Quota Usage"
            >
              <span className="pm-team-logo">
                <LayoutGrid size={16} />
              </span>
              <div>
                <strong>{tenant?.name || selectedBusiness.label}</strong>
                <span>{tenant?.tier_display || 'Growth'} · Plan Usage</span>
              </div>
              <ChevronsUpDown size={12} color="#717588" style={{ marginLeft: 'auto' }} />
            </div>

            <span className="pm-nav-label">WORKSPACE</span>
            <nav className="pm-nav">
              <button
                type="button"
                className={page === 'inbox' ? 'active' : ''}
                onClick={() => {
                  setPage('inbox')
                  setQuery('')
                }}
              >
                <Inbox size={15} />
                <span>Team inbox</span>
                {unreadInboxCount > 0 && <span className="pm-nav-badge">{unreadInboxCount}</span>}
              </button>

              <button
                type="button"
                className={page === 'mine' ? 'active' : ''}
                onClick={() => {
                  setPage('mine')
                  setQuery('')
                }}
              >
                <MessageCircle size={15} />
                <span>My conversations</span>
              </button>

              <button
                type="button"
                className={page === 'unassigned' ? 'active' : ''}
                onClick={() => {
                  setPage('unassigned')
                  setQuery('')
                }}
              >
                <UsersRound size={15} />
                <span>Unassigned</span>
              </button>

              <button
                type="button"
                className={page === 'departments' ? 'active' : ''}
                onClick={() => {
                  setPage('departments')
                  setQuery('')
                }}
              >
                <LayoutGrid size={15} />
                <span>Departments</span>
              </button>

              <button
                type="button"
                className={page === 'contacts' ? 'active' : ''}
                onClick={() => {
                  setPage('contacts')
                  setQuery('')
                  setEnquiryPage(1)
                }}
              >
                <ContactRound size={15} />
                <span>Contacts</span>
              </button>
            </nav>

            <span className="pm-nav-label pm-manage-label">CRM & LEADS</span>
            <nav className="pm-nav">
              <button
                type="button"
                className={page === 'crm' || page === 'crm-leads' ? 'active' : ''}
                onClick={() => {
                  setPage('crm-leads')
                  setQuery('')
                  window.location.hash = 'leads'
                }}
              >
                <TrendingUp size={15} />
                <span>Leads</span>
              </button>

              <button
                type="button"
                className={page === 'crm-pipeline' ? 'active' : ''}
                onClick={() => {
                  setPage('crm-pipeline')
                  setQuery('')
                  window.location.hash = 'pipeline'
                }}
              >
                <Kanban size={15} />
                <span>Pipeline</span>
              </button>

              <button
                type="button"
                className={page === 'crm-search' ? 'active' : ''}
                onClick={() => {
                  setPage('crm-search')
                  setQuery('')
                  window.location.hash = 'crm/search'
                }}
              >
                <Search size={15} />
                <span>CRM Search</span>
              </button>
            </nav>

            <span className="pm-nav-label pm-manage-label">MANAGE</span>
            <nav className="pm-nav">
              <button
                type="button"
                className={page === 'templates' ? 'active' : ''}
                onClick={() => {
                  setPage('templates')
                  setQuery('')
                }}
              >
                <FileText size={15} />
                <span>Templates</span>
              </button>

              <button
                type="button"
                className={page === 'automation' ? 'active' : ''}
                onClick={() => {
                  setPage('automation')
                  setQuery('')
                }}
              >
                <Workflow size={15} />
                <span>Automation</span>
                <Sparkles size={11} color="#8980c7" style={{ marginLeft: 'auto' }} />
              </button>

              <button
                type="button"
                className={page === 'reports' ? 'active' : ''}
                onClick={() => {
                  setPage('reports')
                  setQuery('')
                }}
              >
                <BarChart3 size={15} />
                <span>Reports</span>
              </button>

              {canAdmin && (
                <>
                  <button
                    type="button"
                    className={page === 'admin' ? 'active' : ''}
                    onClick={() => {
                      setPage('admin')
                      setAdminSection('overview')
                      setQuery('')
                    }}
                  >
                    <Shield size={15} />
                    <span>Administration</span>
                  </button>

                  <button
                    type="button"
                    className={page === 'settings' ? 'active' : ''}
                    onClick={() => {
                      setPage('settings')
                      setQuery('')
                    }}
                  >
                    <Settings2 size={15} />
                    <span>Settings</span>
                  </button>
                </>
              )}

              {user?.is_superuser && (
                <button
                  type="button"
                  className={page === 'tenants' ? 'active' : ''}
                  onClick={() => {
                    setPage('tenants')
                    setQuery('')
                  }}
                >
                  <Building2 size={15} />
                  <span>Tenants</span>
                  <span className="pm-nav-badge" style={{ background: '#7c3aed', color: '#fff' }}>
                    Admin
                  </span>
                </button>
              )}
            </nav>
          </div>

          <div className="pm-sidebar-bottom">
            <span className="pm-channel-status">
              <span />
              WhatsApp connected
            </span>
            <a
              href="#help"
              onClick={(e) => {
                e.preventDefault()
                toast('Need assistance? Reach out to support@convernix.example')
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '8px 8px 0',
                color: '#7d8398',
                fontSize: 10,
                borderTop: '1px solid var(--pm-border)',
              }}
            >
              <CircleHelp size={13} />
              Help & resources
              <ArrowUpRight size={11} style={{ marginLeft: 'auto' }} />
            </a>
          </div>
        </aside>

        {/* Content Area */}
        <main className="pm-content-area">
          {busy && <div className="loader" />}
          {notice && <div className={`toast ${notice.type}`}>{notice.text}</div>}

          {['inbox', 'mine', 'unassigned'].includes(page) && (
            <InboxShell
              scope={page === 'mine' ? 'mine' : page === 'unassigned' ? 'unassigned' : 'all'}
              conversations={visible.conversations}
              active={activeConversation}
              open={openConversation}
              send={sendConversationMessage}
              close={() => setActiveConversation(null)}
              busy={busy}
              token={token}
              businessId={selectedBusiness.id}
              user={user}
              query={query}
              setQuery={setQuery}
              setConversations={setConversations}
              toast={toast}
            />
          )}

          {page === 'departments' && (
            <DepartmentsView
              teams={teams}
              conversations={conversations}
              enquiries={enquiries}
              goInbox={(team) => {
                setPage('inbox')
                setQuery(team)
              }}
            />
          )}

          {page === 'contacts' && (
            <ContactsView
              data={visible.enquiries}
              total={enquiryCount}
              page={enquiryPage}
              pageSize={enquiryPageSize}
              setPage={setEnquiryPage}
              setPageSize={(size) => {
                setEnquiryPageSize(size)
                setEnquiryPage(1)
              }}
              exportCsv={() => setModal('export')}
              openEnquiry={setSelectedEnquiry}
              query={query}
              setQuery={setQuery}
            />
          )}

          {page === 'templates' && (
            <TemplatesView
              data={visible.campaigns}
              canWrite={canWrite}
              openCreate={() => setModal('campaign')}
              remove={canWrite ? deleteCampaign : null}
            />
          )}

          {page === 'automation' && (
            <AutomationView
              teams={teams}
              businessNumber={selectedBusiness}
              toast={toast}
              api={api}
              canWrite={canWrite}
            />
          )}

          {page === 'reports' && (
            <ReportsView
              data={analytics}
              period={period}
              setPeriod={setPeriod}
              download={downloadReport}
            />
          )}

          {page === 'admin' && canAdmin && (
            <AdministrationConsole
              user={user}
              tenant={tenant}
              selectedBusiness={selectedBusiness}
              section={adminSection}
              setSection={setAdminSection}
              settingsTab={adminSettingsTab}
              setSettingsTab={setAdminSettingsTab}
              iamTab={adminIamTab}
              setIamTab={setAdminIamTab}
              accountTab={adminAccountTab}
              setAccountTab={setAdminAccountTab}
              toast={toast}
            />
          )}

          {page === 'settings' && canAdmin && (
            <SettingsView
              channel={channel}
              setChannel={setChannel}
              submit={saveChannel}
              busy={busy}
              members={visible.iam}
              user={user}
              saveMember={saveMemberAccess}
              deleteMember={deleteMember}
              openInvite={() => setModal('member')}
            />
          )}

          {page === 'tenants' && user?.is_superuser && (
            <TenantsView
              tenants={platformTenants}
              openCreate={() => setModal('createTenant')}
              onUpdateTier={changeTenantTier}
              onToggleStatus={toggleTenantStatus}
              onDelete={deletePlatformTenant}
              busy={busy}
            />
          )}

          {(page === 'crm' || page === 'crm-leads' || page === 'crm-pipeline' || page === 'crm-search') && (
            <CrmModule
              token={token}
              initialSubView={
                page === 'crm-pipeline'
                  ? 'pipeline'
                  : page === 'crm-search'
                  ? 'search'
                  : 'leads'
              }
            />
          )}
        </main>
      </div>

      {/* Modals */}
      {modal === 'quota' && (
        <Modal title="Plan & Resource Quota" close={() => setModal(null)}>
          <QuotaModalContent tenant={tenant} />
        </Modal>
      )}

      {modal === 'createTenant' && (
        <Modal title="Provision Company Workspace" close={() => setModal(null)}>
          <PlatformCreateTenantForm
            submit={handleCreatePlatformTenant}
            busy={busy}
            close={() => setModal(null)}
          />
        </Modal>
      )}

      {modal === 'campaign' && (
        <Modal title="Create campaign" close={() => setModal(null)}>
          <CampaignForm
            data={campaignForm}
            setData={setCampaignForm}
            submit={createCampaign}
            busy={busy}
          />
        </Modal>
      )}

      {modal === 'member' && (
        <Modal title="Invite team member" close={() => setModal(null)}>
          <MemberForm
            data={memberForm}
            setData={setMemberForm}
            submit={createMember}
            busy={busy}
            owner={user?.role === 'owner'}
          />
        </Modal>
      )}

      {modal === 'export' && (
        <Modal title="Export contacts & enquiries" close={() => setModal(null)}>
          <ExportForm
            data={exportForm}
            setData={setExportForm}
            submit={downloadEnquiries}
            busy={busy}
          />
        </Modal>
      )}

      {selectedEnquiry && (
        <Modal title="Enquiry details" close={() => setSelectedEnquiry(null)}>
          <EnquiryDetails enquiry={selectedEnquiry} />
        </Modal>
      )}
    </div>
  )
}

/* ==========================================================
   3-PANE TEAM INBOX
   ========================================================== */
function InboxShell({
  scope,
  conversations,
  active,
  open,
  send,
  close,
  busy,
  token,
  businessId,
  user,
  query,
  setQuery,
  setConversations,
  toast,
}) {
  const [tab, setTab] = useState('active')
  const [drafts, setDrafts] = useState({})
  const [showEmoji, setShowEmoji] = useState(false)
  const [revealedPhones, setRevealedPhones] = useState({})
  const [revealingPhone, setRevealingPhone] = useState(false)
  const [messages, setMessages] = useState([])
  const [actionBusy, setActionBusy] = useState(false)
  const [deptQueues, setDeptQueues] = useState([])
  const fileInput = useRef(null)

  // Fetch department queue counts
  useEffect(() => {
    if (!token) return
    let mounted = true
    const load = () => {
      fetch(`${API}/inbox/departments/`, {
        headers: {
          Authorization: `Bearer ${token}`,
          ...(businessId ? { 'X-Business-Number-ID': String(businessId) } : {}),
        },
      })
        .then((r) => r.ok ? r.json() : null)
        .then((data) => mounted && data && setDeptQueues(data))
        .catch(() => {})
    }
    load()
    const t = setInterval(load, 15000)
    return () => { mounted = false; clearInterval(t) }
  }, [token, businessId])

  // Fetch messages from inbox API when active conversation changes
  useEffect(() => {
    if (!active?.id || !token) { setMessages([]); return }
    const controller = new AbortController()
    fetch(`${API}/inbox/conversations/${active.id}/messages/?page_size=100`, {
      signal: controller.signal,
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...(businessId ? { 'X-Business-Number-ID': String(businessId) } : {}),
      },
    })
      .then((r) => r.ok ? r.json() : null)
      .then((data) => data && setMessages(data.results || []))
      .catch(() => {})
    return () => controller.abort()
  }, [active?.id, token, businessId])

  // Helper: POST to inbox action endpoint
  const inboxAction = async (path, body = {}) => {
    setActionBusy(true)
    try {
      const res = await fetch(`${API}${path}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          ...(businessId ? { 'X-Business-Number-ID': String(businessId) } : {}),
        },
        body: JSON.stringify(body),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || `Action failed (${res.status})`)
      return data
    } finally {
      setActionBusy(false)
    }
  }

  // Claim unassigned conversation
  const handleClaim = async () => {
    if (!active) return
    try {
      const updated = await inboxAction(`/inbox/conversations/${active.id}/claim/`)
      open(updated)
      toast('Conversation claimed')
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  // Resolve conversation
  const handleResolve = async () => {
    if (!active) return
    try {
      const updated = await inboxAction(`/inbox/conversations/${active.id}/resolve/`)
      open(updated)
      toast('Conversation resolved')
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  // Reopen conversation
  const handleReopen = async () => {
    if (!active) return
    try {
      const updated = await inboxAction(`/inbox/conversations/${active.id}/reopen/`)
      open(updated)
      toast('Conversation reopened')
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const handleRevealPhone = async () => {
    if (!active) return
    const custId = active.contact?.id || active.customer_id || active.id
    if (!custId) return
    setRevealingPhone(true)
    try {
      const res = await fetch(`${API}/whatsapp/customers/${custId}/reveal-phone/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token || localStorage.getItem('crm_access_token') || ''}`,
          'Content-Type': 'application/json',
        },
      })
      if (res.ok) {
        const data = await res.json()
        setRevealedPhones((prev) => ({ ...prev, [active.id]: data.phone_number }))
        toast('Customer phone number revealed (audited)', 'info')
      } else {
        const err = await res.json().catch(() => ({}))
        toast(err.detail || 'Permission denied: Cannot reveal masked phone', 'error')
      }
    } catch {
      toast('Failed to reveal phone number', 'error')
    } finally {
      setRevealingPhone(false)
    }
  }

  const chatId = active?.id
  const draft = drafts[chatId] || { text: '', files: [], isNote: false }

  const updateDraft = (changes) => {
    if (!chatId) return
    setDrafts((items) => ({
      ...items,
      [chatId]: { ...(items[chatId] || { text: '', files: [], isNote: false }), ...changes },
    }))
  }

  // Status normalization: inbox API returns uppercase (OPEN/RESOLVED), legacy used lowercase
  const convStatus = (c) => (c?.status || '').toUpperCase()

  // Filter conversations according to scope, tab, and query
  const scopedConversations = conversations.filter((c) => {
    const status = convStatus(c)
    const isMine =
      c.assigned_user?.email === user?.email ||
      c.team_name === user?.team_name ||
      c.assigned_to === user?.email ||
      c.assigned_to === personName(user)
    const isUnassigned = !c.assigned_user && (!c.assigned_to || c.assigned_to === 'Unassigned')
    if (scope === 'mine' && !isMine) return false
    if (scope === 'unassigned' && !isUnassigned) return false
    if (tab === 'unread' && (c.unread_count || 0) === 0) return false
    if (tab === 'resolved' && status !== 'RESOLVED') return false
    if (tab === 'active' && status === 'RESOLVED') return false
    // Client-side text filter (API search is debounced; this gives instant feedback)
    if (query?.trim()) {
      const q = query.trim().toLowerCase()
      const name = customerName(c).toLowerCase()
      const preview = (c.last_message_preview_plain || c.last_message || '').toLowerCase()
      if (!name.includes(q) && !preview.includes(q)) return false
    }
    return true
  })

  const unreadCount = conversations.reduce((sum, c) => sum + (c.unread_count || 0), 0)

  async function handleSend(e) {
    if (e) e.preventDefault()
    const text = draft.text.trim()
    const files = draft.files || []
    if (!text && !files.length) return

    if (draft.isNote) {
      // Post internal note to inbox API
      try {
        const res = await fetch(`${API}/inbox/conversations/${chatId}/notes/`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
            ...(businessId ? { 'X-Business-Number-ID': String(businessId) } : {}),
          },
          body: JSON.stringify({ content: text }),
        })
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          throw new Error(err.detail || 'Failed to save note')
        }
        const newNote = await res.json()
        setMessages((prev) => [...prev, newNote])
        updateDraft({ text: '', files: [] })
        toast('Internal note saved')
      } catch (err) {
        toast(err.message, 'error')
      }
      return
    }

    const success = await send(text, files)
    if (success) {
      // Refresh messages after send
      if (chatId && token) {
        fetch(`${API}/inbox/conversations/${chatId}/messages/?page_size=100`, {
          headers: {
            Authorization: `Bearer ${token}`,
            ...(businessId ? { 'X-Business-Number-ID': String(businessId) } : {}),
          },
        })
          .then((r) => r.ok ? r.json() : null)
          .then((data) => data && setMessages(data.results || []))
          .catch(() => {})
      }
      updateDraft({ text: '', files: [] })
      if (fileInput.current) fileInput.current.value = ''
      setShowEmoji(false)
    }
  }

  // Compute owner label from inbox API (assigned_user.email) or legacy (assigned_to)
  const assignedEmail = active?.assigned_user?.email || active?.assigned_to || null
  const ownerLabel = active
    ? assignedEmail === user?.email || assignedEmail === personName(user)
      ? 'You'
      : assignedEmail || 'Unassigned'
    : 'Unassigned'

  // Customer name: inbox API uses contact.full_name, legacy uses customer_name
  const customerName = (c) =>
    c?.contact?.full_name || c?.customer_name || 'Customer'

  // Phone: inbox API uses contact.phone, legacy uses phone_number
  const customerPhone = (c) =>
    c?.contact?.masked_phone || c?.phone_number || c?.contact?.whatsapp_number || '—'

  // Debounced server-side search
  useEffect(() => {
    if (!query?.trim() || !token) return
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(
          `${API}/inbox/conversations/?search=${encodeURIComponent(query.trim())}&page_size=50`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              ...(businessId ? { 'X-Business-Number-ID': String(businessId) } : {}),
            },
          },
        )
        if (res.ok) {
          const data = await res.json()
          // Merge search results into existing list (upsert by id)
          setConversations((prev) => {
            const resultIds = new Set((data.results || []).map((c) => c.id))
            const filtered = prev.filter((c) => !resultIds.has(c.id))
            return [...(data.results || []), ...filtered]
          })
        }
      } catch { /* search error */ }
    }, 350)
    return () => clearTimeout(timer)
  }, [query, token, businessId])

  return (
    <div className="pm-inbox-shell">
      {/* Pane 1: Conversations List */}
      <section className="pm-conversations">
        <div className="pm-list-heading">
          <h3>
            {scope === 'mine' ? 'My conversations' : scope === 'unassigned' ? 'Unassigned' : 'Team inbox'}
            <span>{scopedConversations.length}</span>
          </h3>
          <Inbox size={15} color="#757b91" />
        </div>

        <label className="pm-search">
          <Search size={14} />
          <input
            placeholder="Search conversations..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>

        <div className="pm-list-tabs">
          <button
            type="button"
            className={tab === 'active' ? 'active' : ''}
            onClick={() => setTab('active')}
          >
            All <span>{conversations.filter((c) => convStatus(c) !== 'RESOLVED').length}</span>
          </button>
          <button
            type="button"
            className={tab === 'unread' ? 'active' : ''}
            onClick={() => setTab('unread')}
          >
            Unread
          </button>
          <button
            type="button"
            className={tab === 'resolved' ? 'active' : ''}
            onClick={() => setTab('resolved')}
          >
            Resolved
          </button>
        </div>

        {/* Department Queues — live counts from /api/inbox/departments/ */}
        {deptQueues.length > 0 && (
          <div style={{ padding: '6px 12px 4px', borderBottom: '1px solid #1e2133' }}>
            <div style={{ fontSize: 10, color: '#656b82', fontWeight: 600, letterSpacing: '0.06em', marginBottom: 5 }}>
              DEPARTMENT QUEUES
            </div>
            {deptQueues.map((d) => (
              <div
                key={d.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '3px 0',
                  fontSize: 12,
                  color: '#b3bad4',
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: d.open_count > 0 ? '#aaa4ff' : '#3d4463', display: 'inline-block', flexShrink: 0 }} />
                  {d.name}
                </span>
                <span style={{ display: 'flex', gap: 8, fontSize: 10 }}>
                  {d.unassigned_count > 0 && (
                    <span style={{ color: '#ffb450', fontWeight: 700 }}>{d.unassigned_count} new</span>
                  )}
                  <span style={{ color: '#656b82' }}>{d.open_count} open</span>
                </span>
              </div>
            ))}
          </div>
        )}

        <div className="pm-list-sort">
          <span>
            {scopedConversations.length} conversation{scopedConversations.length === 1 ? '' : 's'}
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            Newest first <ArrowDown size={10} />
          </span>
        </div>

        <div className="pm-conversation-items">
          {scopedConversations.map((item) => {
            const isSelected = active?.id === item.id
            const cName = customerName(item)
            const avatarBg = getAvatarColor(cName)
            const deptName = item.department?.name || item.team_name || 'Support'
            const preview = item.last_message_preview_plain || item.last_message || item.message || 'No messages yet'
            return (
              <button
                key={item.id}
                type="button"
                className={`pm-conversation-item ${isSelected ? 'active' : ''}`}
                onClick={() => open(item)}
              >
                <div className="pm-avatar-wrap">
                  <span className="pm-avatar small" style={{ background: avatarBg }}>
                    {(cName[0] || 'C').toUpperCase()}
                  </span>
                  <span className="pm-whatsapp-mark">
                    <MessageCircle size={8} fill="currentColor" />
                  </span>
                </div>

                <div className="pm-conversation-content">
                  <div className="pm-conversation-top">
                    <strong>{cName}</strong>
                    <time>{formatTime(item.last_message_at)}</time>
                  </div>
                  <div className="pm-conversation-preview">
                    {preview}
                  </div>
                  <div className="pm-conversation-meta">
                    <span className="pm-dept-tag">
                      <i />
                      {deptName}
                    </span>
                    {item.unread_count > 0 && (
                      <span className="pm-unread-badge">{item.unread_count}</span>
                    )}
                    {convStatus(item) === 'RESOLVED' && <Check size={12} color="#52bb89" />}
                  </div>
                </div>
              </button>
            )
          })}

          {!scopedConversations.length && (
            <div className="pm-empty-view">
              <MessageSquareText size={28} />
              <strong>No conversations</strong>
              <p>
                {query ? 'No conversations match your search query.' : 'No conversations in this view.'}
              </p>
            </div>
          )}
        </div>

        <div className="pm-inbox-footer">
          <CheckCheck size={13} color="#6a7185" />
          <span>
            {unreadCount
              ? `${unreadCount} unread message${unreadCount === 1 ? '' : 's'} across your inbox`
              : 'You’re all caught up'}
          </span>
        </div>
      </section>

      {/* Pane 2: Chat Thread & Composer */}
      <section className="pm-chat">
        {active ? (
          <>
            <header className="pm-chat-header">
              <div className="pm-chat-person">
                <span
                  className="pm-avatar small"
                  style={{ background: getAvatarColor(customerName(active)) }}
                >
                  {(customerName(active)[0] || 'C').toUpperCase()}
                </span>
                <div>
                  <strong>{customerName(active)}</strong>
                  <span>
                    <i />
                    WhatsApp · {revealedPhones[active.id] || customerPhone(active)}
                  </span>
                </div>
              </div>

              <div className="pm-chat-header-actions">
                {/* Claim button — only shown when unassigned */}
                {!active.assigned_user && convStatus(active) === 'OPEN' && (
                  <button
                    type="button"
                    className="pm-tool-btn"
                    style={{ color: '#aaa4ff', fontSize: 11, padding: '3px 10px', gap: 4 }}
                    onClick={handleClaim}
                    disabled={actionBusy}
                    title="Claim this conversation"
                  >
                    <UserRound size={12} />
                    Claim
                  </button>
                )}
                {/* Resolve button — shown when OPEN or PENDING */}
                {['OPEN', 'PENDING'].includes(convStatus(active)) && (
                  <button
                    type="button"
                    className="pm-tool-btn"
                    style={{ color: '#52bb89', fontSize: 11, padding: '3px 10px', gap: 4 }}
                    onClick={handleResolve}
                    disabled={actionBusy}
                    title="Mark conversation as resolved"
                  >
                    <Check size={12} />
                    Resolve
                  </button>
                )}
                {/* Reopen button — shown when RESOLVED */}
                {convStatus(active) === 'RESOLVED' && (
                  <button
                    type="button"
                    className="pm-tool-btn"
                    style={{ color: '#aaa4ff', fontSize: 11, padding: '3px 10px', gap: 4 }}
                    onClick={handleReopen}
                    disabled={actionBusy}
                    title="Reopen this conversation"
                  >
                    <RotateCcw size={12} />
                    Reopen
                  </button>
                )}
                {/* Status badge */}
                <span
                  style={{
                    fontSize: 10,
                    padding: '2px 8px',
                    borderRadius: 10,
                    background: convStatus(active) === 'RESOLVED' ? 'rgba(82,187,137,0.15)' : convStatus(active) === 'OPEN' ? 'rgba(170,164,255,0.15)' : 'rgba(255,180,80,0.15)',
                    color: convStatus(active) === 'RESOLVED' ? '#52bb89' : convStatus(active) === 'OPEN' ? '#aaa4ff' : '#ffb450',
                    fontWeight: 600,
                    textTransform: 'capitalize',
                  }}
                >
                  {(active.status || 'open').toLowerCase()}
                </span>
                <button
                  className="pm-tool-btn"
                  onClick={close}
                  title="Close conversation"
                  aria-label="Close"
                >
                  <X size={15} />
                </button>
              </div>
            </header>

            <div className="pm-chat-thread" id="workspace-chat-thread">
              <div className="pm-day-divider">Today</div>

              {/* Department Routing Banner */}
              <div className="pm-routing-pill">
                <Workflow size={12} />
                <span>
                  Routed to <strong>{active.department?.name || active.team_name || 'Support'}</strong> department
                </span>
              </div>

              {/* Messages from inbox API */}
              {messages.map((msg) => {
                const isNote = msg.message_type === 'INTERNAL_NOTE' || msg.direction === 'INTERNAL'
                const isOutgoing = msg.direction === 'OUTBOUND'
                const senderName = msg.sender_user
                  ? `${msg.sender_user.first_name || ''} ${msg.sender_user.last_name || ''}`.trim() || msg.sender_user.email
                  : isOutgoing ? personName(user) : customerName(active)

                if (isNote) {
                  return (
                    <div key={msg.id} className="pm-local-note">
                      <span
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 5,
                          fontSize: 10,
                          color: '#dfbc74',
                          marginBottom: 4,
                        }}
                      >
                        <StickyNote size={12} />
                        Internal note · {senderName} · Only visible to your team
                      </span>
                      <div>{msg.content}</div>
                      <span style={{ fontSize: 9, color: '#9d8759', marginTop: 4, display: 'block' }}>
                        {formatTime(msg.timestamp)}
                      </span>
                    </div>
                  )
                }

                return (
                  <div
                    key={msg.id}
                    className={`pm-chat-bubble-row ${isOutgoing ? 'outgoing' : 'incoming'}`}
                  >
                    {isOutgoing && (
                      <div className="pm-agent-author">
                        {senderName} <span>Agent</span>
                      </div>
                    )}
                    <div
                      className={`pm-bubble ${isOutgoing ? 'pm-bubble-outgoing' : 'pm-bubble-incoming'}`}
                    >
                      <MessageAttachment message={msg} token={token} businessId={businessId} />
                      {msg.content && <p style={{ margin: 0 }}>{msg.content}</p>}
                    </div>
                    <span className="pm-bubble-meta">
                      {new Date(msg.timestamp).toLocaleTimeString('en-IN', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                      {isOutgoing && <CheckCheck size={12} color="#aaa4ff" />}
                    </span>
                  </div>
                )
              })}

              {messages.length === 0 && (
                <div className="pm-chat-bubble-row incoming">
                  <span
                    className="pm-avatar small"
                    style={{ background: getAvatarColor(customerName(active)), alignSelf: 'flex-end' }}
                  >
                    {(customerName(active)[0] || 'C').toUpperCase()}
                  </span>
                  <div>
                    <div className="pm-bubble pm-bubble-incoming">
                      Customer initiated WhatsApp conversation.
                    </div>
                    <span className="pm-bubble-meta">
                      {formatTime(active.created_at || active.last_message_at)}
                    </span>
                  </div>
                </div>
              )}

              {/* Assignment Banner */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  fontSize: 10,
                  color: '#767c92',
                  margin: '12px 0',
                }}
              >
                <span
                  style={{
                    width: 16,
                    height: 16,
                    borderRadius: '50%',
                    background: '#342f44',
                    color: '#c2b5eb',
                    display: 'grid',
                    placeItems: 'center',
                    fontSize: 8,
                    fontWeight: 700,
                  }}
                >
                  {ownerLabel === 'You' ? initials(user) : ownerLabel[0] || '?'}
                </span>
                <span>
                  {ownerLabel === 'Unassigned'
                    ? 'Waiting for an available teammate'
                    : `Currently assigned to ${ownerLabel === 'You' ? `${personName(user)} (you)` : ownerLabel}`}
                </span>
              </div>
            </div>

            {/* Composer */}
            <form className="pm-composer" onSubmit={handleSend}>
              <div className="pm-composer-tabs">
                <button
                  type="button"
                  className={!draft.isNote ? 'active' : ''}
                  onClick={() => updateDraft({ isNote: false })}
                >
                  <MessageCircle size={12} />
                  Reply
                </button>
                <button
                  type="button"
                  className={draft.isNote ? 'active' : ''}
                  onClick={() => updateDraft({ isNote: true })}
                >
                  <LockKeyhole size={11} />
                  Internal note
                </button>
              </div>

              {/* Attachments preview */}
              {draft.files?.length > 0 && (
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
                  {draft.files.map((file, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        padding: '3px 8px',
                        background: '#1f2334',
                        borderRadius: 6,
                        border: '1px solid var(--pm-border)',
                        fontSize: 10,
                      }}
                    >
                      <Paperclip size={11} color="#aaa4ff" />
                      <span>{file.name}</span>
                      <button
                        type="button"
                        onClick={() =>
                          updateDraft({
                            files: draft.files.filter((_, i) => i !== idx),
                          })
                        }
                        style={{ color: '#8c92a6', marginLeft: 4 }}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Emoji Picker */}
              {showEmoji && (
                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: 6,
                    padding: 8,
                    background: '#191c28',
                    border: '1px solid var(--pm-border)',
                    borderRadius: 8,
                    marginBottom: 8,
                  }}
                >
                  {emojis.map((emoji) => (
                    <button
                      key={emoji}
                      type="button"
                      onClick={() => {
                        updateDraft({ text: (draft.text || '') + emoji })
                        setShowEmoji(false)
                      }}
                      style={{ fontSize: 16, padding: '2px 4px' }}
                    >
                      {emoji}
                    </button>
                  ))}
                </div>
              )}

              <textarea
                placeholder={
                  draft.isNote
                    ? 'Add a note for your team...'
                    : `Reply to ${(active.customer_name || 'Customer').split(' ')[0]}...`
                }
                value={draft.text}
                onChange={(e) => updateDraft({ text: e.target.value })}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSend(e)
                  }
                }}
              />

              <div className="pm-composer-bottom">
                <div className="pm-composer-tools">
                  <input
                    ref={fileInput}
                    type="file"
                    multiple
                    style={{ display: 'none' }}
                    onChange={(e) => {
                      const selected = Array.from(e.target.files || [])
                      updateDraft({ files: [...(draft.files || []), ...selected].slice(0, 5) })
                    }}
                  />
                  <button
                    type="button"
                    className="pm-tool-btn"
                    onClick={() => fileInput.current?.click()}
                    title="Attach files"
                  >
                    <Paperclip size={14} />
                  </button>
                  <button
                    type="button"
                    className="pm-tool-btn"
                    onClick={() => setShowEmoji((v) => !v)}
                    title="Add emoji"
                  >
                    <Smile size={14} />
                  </button>
                  <span
                    style={{
                      fontSize: 10,
                      color: '#656b82',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      marginLeft: 8,
                    }}
                  >
                    <ShieldCheck size={12} color="#25d366" />
                    WhatsApp channel connected
                  </span>
                </div>

                <button
                  type="submit"
                  className="pm-send-btn"
                  disabled={busy || (!draft.text.trim() && !(draft.files || []).length)}
                >
                  {draft.isNote ? 'Add note' : 'Send'}
                  <Send size={12} />
                </button>
              </div>
            </form>

            <div className="pm-chat-footer">
              <Bot size={11} color="#aaa4ff" />
              <span>Powered by Convernix. Built for your team.</span>
            </div>
          </>
        ) : (
          <div className="pm-empty-view">
            <MessageSquareText size={38} />
            <strong style={{ fontSize: 16 }}>Select a conversation</strong>
            <p>Choose a customer from the left list to open their WhatsApp conversation history.</p>
          </div>
        )}
      </section>

      {/* Pane 3: Contact Details Sidebar */}
      <aside className="pm-customer-details">
        <div className="pm-details-heading">
          <span>Contact details</span>
          <ContactRound size={14} color="#757b91" />
        </div>

        {active ? (
          <>
            <div className="pm-details-profile">
              <span
                className="pm-avatar"
                style={{ background: getAvatarColor(customerName(active)) }}
              >
                {(customerName(active)[0] || 'C').toUpperCase()}
              </span>
              <strong>{customerName(active)}</strong>
              <span>{active.contact?.organization || active.organization_name || customerPhone(active)}</span>
              <span className="pm-customer-pill">Customer</span>
            </div>

            <div className="pm-details-section">
              <h4>Conversation details</h4>
              <dl style={{ margin: 0 }}>
                <div className="pm-detail-row">
                  <dt>Assigned to</dt>
                  <dd style={{ color: '#aaa4ff', fontWeight: 600 }}>{ownerLabel}</dd>
                </div>
                <div className="pm-detail-row">
                  <dt>Department</dt>
                  <dd>{active.department?.name || active.team_name || 'Support'}</dd>
                </div>
                <div className="pm-detail-row">
                  <dt>Status</dt>
                  <dd style={{ textTransform: 'capitalize' }}>{(active.status || 'open').toLowerCase()}</dd>
                </div>
                <div className="pm-detail-row">
                  <dt>Priority</dt>
                  <dd style={{ textTransform: 'capitalize' }}>{(active.priority || 'normal').toLowerCase()}</dd>
                </div>
                <div className="pm-detail-row">
                  <dt>Reference</dt>
                  <dd>
                    <code>{active.reference || '—'}</code>
                  </dd>
                </div>
              </dl>
            </div>

            <div className="pm-details-section">
              <h4>Contact information</h4>
              <dl style={{ margin: 0 }}>
                <div className="pm-detail-row">
                  <dt>Email</dt>
                  <dd>{active.contact?.email || active.customer_email || '—'}</dd>
                </div>
                <div className="pm-detail-row">
                  <dt>Phone</dt>
                  <dd style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
                    <span>{revealedPhones[active.id] || customerPhone(active)}</span>
                    {!revealedPhones[active.id] && customerPhone(active).includes('*') && (
                      <button
                        type="button"
                        onClick={handleRevealPhone}
                        disabled={revealingPhone}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4,
                          fontSize: 10,
                          padding: '2px 6px',
                          background: '#2b3046',
                          color: '#8280ff',
                          border: '1px solid #3d4463',
                          borderRadius: 4,
                          cursor: 'pointer',
                        }}
                        title="Authorized reveal (audited for compliance)"
                      >
                        <Eye size={10} />
                        {revealingPhone ? 'Revealing...' : 'Reveal'}
                      </button>
                    )}
                    {revealedPhones[active.id] && (
                      <span
                        style={{
                          fontSize: 9,
                          color: '#4ade80',
                          background: 'rgba(74, 222, 128, 0.1)',
                          padding: '1px 5px',
                          borderRadius: 3,
                          border: '1px solid rgba(74, 222, 128, 0.2)',
                        }}
                        title="Access recorded in immutable audit log"
                      >
                        Audited
                      </span>
                    )}
                  </dd>
                </div>
                <div className="pm-detail-row">
                  <dt>Organization</dt>
                  <dd>{active.contact?.organization || active.organization_name || 'Individual'}</dd>
                </div>
              </dl>
            </div>

            <div className="pm-details-section">
              <h4>Tags</h4>
              <div className="pm-tags-wrap">
                {(active.tags || []).map((t) => (
                  <span key={t.tag?.id || t.id} className="pm-tag">{t.tag?.name || t.name || 'Tag'}</span>
                ))}
                {(!active.tags || active.tags.length === 0) && (
                  <span style={{ fontSize: 11, color: '#656b82' }}>No tags assigned</span>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="pm-empty-view" style={{ height: 'auto', padding: '40px 16px' }}>
            <p style={{ fontSize: 11, color: '#767d94' }}>
              Select a conversation to view customer details.
            </p>
          </div>
        )}
      </aside>
    </div>
  )
}

/* ==========================================================
   DEPARTMENTS VIEW
   ========================================================== */
function DepartmentsView({ teams: _teams, conversations, enquiries, goInbox }) {
  const departments = [
    {
      name: 'Support',
      desc: 'Customer service, technical inquiries, troubleshooting, and ticket escalations.',
      lead: 'Support Team Lead',
    },
    {
      name: 'Sales',
      desc: 'New business opportunities, product demonstrations, pricing, and onboarding.',
      lead: 'Sales Director',
    },
    {
      name: 'HR',
      desc: 'Careers, recruitment inquiries, talent screening, and employment questions.',
      lead: 'People Operations',
    },
    {
      name: 'Billing',
      desc: 'Invoicing, payment processing, subscription management, and refunds.',
      lead: 'Finance Lead',
    },
  ]

  return (
    <div className="pm-table-container">
      <div className="pm-panel-header" style={{ marginBottom: 20 }}>
        <div>
          <h2>Departments & Routing Teams</h2>
          <p>Organize customer conversations and inbound WhatsApp enquiries by business unit</p>
        </div>
      </div>

      <div className="pm-dept-grid">
        {departments.map((dept) => {
          const count = conversations.filter(
            (c) => (c.team_name || '').toLowerCase() === dept.name.toLowerCase(),
          ).length
          const enqCount = enquiries.filter(
            (e) => (e.team_name || '').toLowerCase() === dept.name.toLowerCase(),
          ).length

          return (
            <div className="pm-dept-card" key={dept.name}>
              <div className="pm-dept-card-top">
                <div className="pm-dept-card-icon">
                  <LayoutGrid size={18} />
                </div>
                <div>
                  <strong>{dept.name}</strong>
                  <span>Active routing</span>
                </div>
              </div>

              <p>{dept.desc}</p>

              <div className="pm-dept-card-footer">
                <span>
                  <strong>{count}</strong> active chat{count === 1 ? '' : 's'} ·{' '}
                  <strong>{enqCount}</strong> enquiries
                </span>
                <button
                  className="pm-secondary-btn"
                  onClick={() => goInbox(dept.name)}
                  style={{ padding: '4px 8px', fontSize: 10 }}
                >
                  View queue →
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ==========================================================
   CONTACTS & ENQUIRIES VIEW
   ========================================================== */
function ContactsView({
  data,
  total,
  page,
  pageSize,
  setPage,
  setPageSize,
  exportCsv,
  openEnquiry,
  query,
  setQuery,
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  const first = total ? (page - 1) * pageSize + 1 : 0
  const last = Math.min(page * pageSize, total)

  return (
    <div className="pm-table-container">
      <div className="pm-panel-card">
        <div className="pm-panel-header">
          <div>
            <h2>WhatsApp Contacts & Enquiries</h2>
            <p>{total} customer enquiries routed across your channels · Select any row for details</p>
          </div>
          <button className="pm-secondary-btn" onClick={exportCsv}>
            ↓ Export CSV
          </button>
        </div>

        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--pm-border)' }}>
          <label className="pm-search" style={{ margin: 0 }}>
            <Search size={14} />
            <input
              placeholder="Search enquiries by customer, phone, email, or reference..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value)
                setPage(1)
              }}
            />
          </label>
        </div>

        {data.length ? (
          <table className="pm-dark-table">
            <thead>
              <tr>
                <th>S.No</th>
                <th>Customer</th>
                <th>Reference</th>
                <th>Department</th>
                <th>Message</th>
                <th>Status</th>
                <th>Received</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item, index) => {
                const customerName = item.customer_name || 'Customer'
                return (
                  <tr
                    key={item.id}
                    className="pm-clickable-row"
                    onClick={() => openEnquiry(item)}
                  >
                    <td style={{ color: '#71778c' }}>{(page - 1) * pageSize + index + 1}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span
                          className="pm-avatar small"
                          style={{ background: getAvatarColor(customerName) }}
                        >
                          {(customerName[0] || 'C').toUpperCase()}
                        </span>
                        <div>
                          <strong style={{ color: '#fff' }}>{customerName}</strong>
                          <div style={{ fontSize: 10, color: '#848a9e' }}>
                            {item.phone_number || item.customer_email || 'No phone'}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <code style={{ color: '#aaa4ff' }}>{item.reference}</code>
                    </td>
                    <td>{item.team_name || 'Support'}</td>
                    <td
                      style={{
                        maxWidth: 240,
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {item.message}
                    </td>
                    <td>
                      <span className={`pm-status-badge ${item.status}`}>{item.status}</span>
                    </td>
                    <td style={{ fontSize: 10, color: '#8c92a6' }}>
                      {item.created_at ? date.format(new Date(item.created_at)) : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        ) : (
          <div className="pm-empty-view">
            <MessageSquareText size={32} />
            <strong>No enquiries found</strong>
            <p>No customer enquiries match your current search.</p>
          </div>
        )}

        <footer className="pm-pagination">
          <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            Rows per page
            <select value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}>
              {[20, 50, 100, 200].map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </label>
          <span>
            {first}–{last} of {total}
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <button
              type="button"
              onClick={() => setPage(page - 1)}
              disabled={page <= 1}
              aria-label="Previous page"
            >
              ‹
            </button>
            <span>
              Page {page} of {pages}
            </span>
            <button
              type="button"
              onClick={() => setPage(page + 1)}
              disabled={page >= pages}
              aria-label="Next page"
            >
              ›
            </button>
          </div>
        </footer>
      </div>
    </div>
  )
}

/* ==========================================================
   TEMPLATES & CAMPAIGNS VIEW
   ========================================================== */
function TemplatesView({ data, canWrite, openCreate, remove }) {
  return (
    <div className="pm-table-container">
      <div className="pm-panel-card">
        <div className="pm-panel-header">
          <div>
            <h2>WhatsApp Message Templates & Campaigns</h2>
            <p>{data.length} campaigns and broadcast templates configured for your workspace</p>
          </div>
          {canWrite && (
            <button className="pm-primary-btn" onClick={openCreate}>
              <Plus size={14} /> New campaign
            </button>
          )}
        </div>

        {data.length ? (
          <table className="pm-dark-table">
            <thead>
              <tr>
                <th>Campaign</th>
                <th>Status</th>
                <th>Target audience</th>
                <th>Scheduled</th>
                <th>Sent</th>
                <th>Delivered</th>
                <th>Opened</th>
                {remove && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {data.map((c) => (
                <tr key={c.id}>
                  <td>
                    <strong style={{ color: '#fff' }}>{c.name}</strong>
                    <div
                      style={{
                        fontSize: 10,
                        color: '#848a9e',
                        maxWidth: 280,
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {c.message}
                    </div>
                  </td>
                  <td>
                    <span className={`pm-status-badge ${c.status}`}>{c.status}</span>
                  </td>
                  <td>{c.target_audience}</td>
                  <td>
                    {c.scheduled_at ? date.format(new Date(c.scheduled_at)) : 'Not scheduled'}
                  </td>
                  <td>{number.format(c.sent_count || 0)}</td>
                  <td>{number.format(c.delivered_count || 0)}</td>
                  <td>{number.format(c.opened_count || 0)}</td>
                  {remove && (
                    <td>
                      <button className="pm-danger-btn" onClick={() => remove(c.id)}>
                        Delete
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="pm-empty-view">
            <FileText size={32} />
            <strong>No campaigns yet</strong>
            <p>Create a WhatsApp template campaign to broadcast updates or engage your customers.</p>
          </div>
        )}
      </div>
    </div>
  )
}

/* ==========================================================
   AUTOMATION & WORKFLOWS VIEW
   ========================================================== */
const DEFAULT_RULES = [
  {
    rule_type: 'welcome',
    name: 'Incoming Welcome Auto-responder',
    trigger_desc: 'On first message from new customer',
    action_desc: 'Send warm greeting and request details',
    is_active: true,
    config: {
      message: 'Hello! Thanks for reaching out to us on WhatsApp. How can our team assist you today?',
    },
  },
  {
    rule_type: 'keyword_routing',
    name: 'Keyword-based Department Routing',
    trigger_desc: 'Message contains "demo", "pricing", or "quote"',
    action_desc: 'Instantly route to Sales department queue',
    is_active: true,
    config: {
      routes: [
        { keyword: 'demo', team: 'Sales' },
        { keyword: 'pricing', team: 'Sales' },
        { keyword: 'quote', team: 'Sales' },
        { keyword: 'help', team: 'Support' },
        { keyword: 'support', team: 'Support' },
        { keyword: 'billing', team: 'Billing' },
        { keyword: 'invoice', team: 'Billing' },
        { keyword: 'career', team: 'HR' },
        { keyword: 'job', team: 'HR' },
      ],
    },
  },
  {
    rule_type: 'out_of_hours',
    name: 'Out-of-hours Auto-reply',
    trigger_desc: 'Inbound message outside 9 AM – 6 PM',
    action_desc: 'Inform sender of business hours and expected SLA',
    is_active: true,
    config: {
      start_hour: 9,
      end_hour: 18,
      message: 'Thank you for your message! Our office hours are Monday to Friday, 9:00 AM – 6:00 PM. We have received your inquiry and our team will get back to you shortly.',
    },
  },
  {
    rule_type: 'escalation',
    name: 'Lead Escalation Trigger',
    trigger_desc: 'No agent response within 15 minutes',
    action_desc: 'Notify department supervisor and mark Priority',
    is_active: true,
    config: {
      timeout_minutes: 15,
    },
  },
]

const RULE_ICONS = {
  welcome: MessageCircle,
  keyword_routing: Workflow,
  out_of_hours: Bot,
  escalation: ShieldCheck,
}

function AutomationConfigModal({ rule, close, onSave, teams }) {
  const [config, setConfig] = useState(() => ({ ...(rule?.config || {}) }))
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await onSave(rule.id, config)
    } finally {
      setSaving(false)
    }
  }

  const existingTeams = (teams || []).map((t) => (typeof t === 'string' ? t : t.name)).filter(Boolean)
  const teamList = Array.from(new Set([...existingTeams, 'Sales', 'Support', 'Billing', 'HR']))

  return (
    <Modal title={`Configure: ${rule.name}`} close={close}>
      <form className="pm-form" onSubmit={handleSubmit}>
        <div className="full" style={{ marginBottom: 6 }}>
          <p style={{ margin: 0, fontSize: 12, color: '#8c92a6' }}>
            <strong style={{ color: '#fff' }}>Trigger:</strong> {rule.trigger_desc}
            <br />
            <strong style={{ color: '#fff' }}>Action:</strong> {rule.action_desc}
          </p>
        </div>

        {rule.rule_type === 'welcome' && (
          <label className="full">
            <span>Welcome Auto-reply Message</span>
            <textarea
              rows={4}
              value={config.message || ''}
              onChange={(e) => setConfig({ ...config, message: e.target.value })}
              placeholder="Enter welcome message sent to new customers on first contact..."
              required
            />
          </label>
        )}

        {rule.rule_type === 'out_of_hours' && (
          <>
            <label>
              <span>Business Day Start Hour (0–23)</span>
              <input
                type="number"
                min="0"
                max="23"
                value={config.start_hour ?? 9}
                onChange={(e) => setConfig({ ...config, start_hour: parseInt(e.target.value, 10) || 0 })}
                required
              />
            </label>
            <label>
              <span>Business Day End Hour (0–23)</span>
              <input
                type="number"
                min="0"
                max="23"
                value={config.end_hour ?? 18}
                onChange={(e) => setConfig({ ...config, end_hour: parseInt(e.target.value, 10) || 0 })}
                required
              />
            </label>
            <label className="full">
              <span>Out-of-Hours Auto-reply Message</span>
              <textarea
                rows={4}
                value={config.message || ''}
                onChange={(e) => setConfig({ ...config, message: e.target.value })}
                placeholder="Message sent when an inbound message arrives outside working hours or weekends..."
                required
              />
            </label>
          </>
        )}

        {rule.rule_type === 'escalation' && (
          <label className="full">
            <span>Unattended Timeout (minutes)</span>
            <input
              type="number"
              min="1"
              max="1440"
              value={config.timeout_minutes ?? 15}
              onChange={(e) => setConfig({ ...config, timeout_minutes: parseInt(e.target.value, 10) || 15 })}
              required
            />
            <span style={{ fontSize: 10, color: '#848a9e', marginTop: 4 }}>
              Enquiries waiting longer than this threshold without an agent response are automatically flagged [PRIORITY].
            </span>
          </label>
        )}

        {rule.rule_type === 'keyword_routing' && (
          <div className="full">
            <span style={{ fontSize: 11, fontWeight: 600, color: '#b0b4c7', display: 'block', marginBottom: 8 }}>
              Keyword & Department Routing Rules
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 220, overflowY: 'auto', paddingRight: 4 }}>
              {(config.routes || []).map((route, idx) => (
                <div key={idx} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <input
                    type="text"
                    placeholder="Keyword (e.g. demo)"
                    value={route.keyword}
                    onChange={(e) => {
                      const newRoutes = [...config.routes]
                      newRoutes[idx] = { ...newRoutes[idx], keyword: e.target.value.toLowerCase() }
                      setConfig({ ...config, routes: newRoutes })
                    }}
                    style={{ flex: 1 }}
                    required
                  />
                  <span style={{ color: '#848a9e', fontSize: 12 }}>&rarr;</span>
                  <select
                    value={route.team}
                    onChange={(e) => {
                      const newRoutes = [...config.routes]
                      newRoutes[idx] = { ...newRoutes[idx], team: e.target.value }
                      setConfig({ ...config, routes: newRoutes })
                    }}
                    style={{ flex: 1 }}
                  >
                    {teamList.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => {
                      const newRoutes = config.routes.filter((_, i) => i !== idx)
                      setConfig({ ...config, routes: newRoutes })
                    }}
                    style={{
                      background: 'rgba(239, 68, 68, 0.1)',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                      color: '#ef4444',
                      borderRadius: 6,
                      width: 32,
                      height: 32,
                      cursor: 'pointer',
                    }}
                    title="Remove keyword route"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
            <button
              type="button"
              className="pm-secondary-btn"
              onClick={() => {
                const newRoutes = [...(config.routes || []), { keyword: '', team: teamList[0] || 'Sales' }]
                setConfig({ ...config, routes: newRoutes })
              }}
              style={{ marginTop: 10, fontSize: 11, padding: '4px 10px' }}
            >
              + Add Keyword Route
            </button>
          </div>
        )}

        <footer>
          <button type="button" className="pm-secondary-btn" onClick={close} disabled={saving}>
            Cancel
          </button>
          <button type="submit" className="pm-primary-btn" disabled={saving}>
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </footer>
      </form>
    </Modal>
  )
}

function AutomationView({ teams, businessNumber, toast, api, canWrite }) {
  const [rules, setRules] = useState(DEFAULT_RULES)
  const [togglingId, setTogglingId] = useState(null)
  const [configureRule, setConfigureRule] = useState(null)

  const loadRules = useCallback(async () => {
    if (!api || !businessNumber) return
    try {
      const data = await api('/whatsapp/automations/')
      const items = Array.isArray(data) ? data : data?.results || []
      if (items.length > 0) {
        setRules(items)
      }
    } catch (err) {
      console.error('Failed to load automations:', err)
    }
  }, [api, businessNumber])

  useEffect(() => {
    loadRules()
  }, [loadRules])

  const handleToggle = async (rule) => {
    if (!canWrite) {
      toast('You need editor or admin permissions to modify automations.', 'error')
      return
    }
    const newActive = !rule.is_active
    setTogglingId(rule.id || rule.rule_type)

    // Optimistic state update
    setRules((prev) =>
      prev.map((r) =>
        (r.id && r.id === rule.id) || r.rule_type === rule.rule_type
          ? { ...r, is_active: newActive }
          : r
      )
    )

    try {
      if (rule.id && api) {
        const updated = await api(`/whatsapp/automations/${rule.id}/`, {
          method: 'PATCH',
          body: JSON.stringify({ is_active: newActive }),
        })
        setRules((prev) => prev.map((r) => (r.id === rule.id ? updated : r)))
      }
      toast(`Workflow "${rule.name}" ${newActive ? 'enabled' : 'disabled'}.`)
    } catch (err) {
      // Revert on error
      setRules((prev) =>
        prev.map((r) =>
          (r.id && r.id === rule.id) || r.rule_type === rule.rule_type
            ? { ...r, is_active: !newActive }
            : r
        )
      )
      toast(err.message || 'Failed to update workflow', 'error')
    } finally {
      setTogglingId(null)
    }
  }

  const handleSaveConfig = async (ruleId, newConfig) => {
    try {
      if (ruleId && api) {
        const updated = await api(`/whatsapp/automations/${ruleId}/`, {
          method: 'PATCH',
          body: JSON.stringify({ config: newConfig }),
        })
        setRules((prev) => prev.map((r) => (r.id === ruleId ? updated : r)))
      }
      setConfigureRule(null)
      toast('Workflow configuration saved successfully.')
    } catch (err) {
      toast(err.message || 'Failed to save configuration', 'error')
    }
  }

  return (
    <div className="pm-table-container">
      <div className="pm-panel-header" style={{ marginBottom: 20 }}>
        <div>
          <h2>Automation & Routing Workflows</h2>
          <p>
            Automated actions and intelligent routing triggers running on number{' '}
            <strong style={{ color: '#aaa4ff' }}>{businessNumber?.number}</strong>
          </p>
        </div>
      </div>

      <div className="pm-dept-grid">
        {rules.map((wf) => {
          const IconComponent = RULE_ICONS[wf.rule_type] || Workflow
          const isToggling = togglingId === wf.id || togglingId === wf.rule_type

          return (
            <div
              className="pm-dept-card"
              key={wf.id || wf.rule_type}
              style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
            >
              <div>
                <div
                  className="pm-dept-card-top"
                  style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, minWidth: 0 }}>
                    <div className="pm-dept-card-icon">
                      <IconComponent size={18} />
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <strong style={{ display: 'block', fontSize: 13, color: '#fff', lineHeight: 1.3 }}>
                        {wf.name}
                      </strong>
                      <span className={wf.is_active ? 'pm-status-active' : 'pm-status-inactive'}>
                        <span className="pm-status-dot" />
                        {wf.is_active ? 'Active' : 'Disabled'}
                      </span>
                    </div>
                  </div>

                  <label
                    className="pm-toggle-switch"
                    title={wf.is_active ? 'Click to disable' : 'Click to enable'}
                  >
                    <input
                      type="checkbox"
                      checked={!!wf.is_active}
                      onChange={() => handleToggle(wf)}
                      disabled={isToggling}
                    />
                    <span className="pm-toggle-slider" />
                  </label>
                </div>

                <p style={{ marginTop: 12, marginBottom: 16 }}>
                  <strong style={{ color: '#c3c7db' }}>Trigger:</strong> {wf.trigger_desc}
                  <br />
                  <strong style={{ color: '#c3c7db' }}>Action:</strong> {wf.action_desc}
                </p>
              </div>

              <div className="pm-dept-card-footer">
                <span>
                  {wf.last_triggered_at
                    ? `Last fired: ${formatTime(wf.last_triggered_at)}`
                    : wf.is_active
                    ? 'Rules active 24/7'
                    : 'Workflow paused'}
                </span>
                <button
                  type="button"
                  className="pm-secondary-btn"
                  onClick={() => setConfigureRule(wf)}
                  style={{ padding: '4px 10px', fontSize: 11, cursor: 'pointer' }}
                >
                  Configure →
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {configureRule && (
        <AutomationConfigModal
          rule={configureRule}
          close={() => setConfigureRule(null)}
          onSave={handleSaveConfig}
          teams={teams}
        />
      )}
    </div>
  )
}

/* ==========================================================
   REPORTS & ANALYTICS VIEW
   ========================================================== */
function ReportsView({ data, period, setPeriod, download }) {
  const years = Array.from({ length: 6 }, (_, i) => new Date().getFullYear() - i)
  const trends = mergeTrends(data.trend)
  const max = Math.max(1, ...trends.map((x) => Math.max(x.enquiries, x.campaigns)))

  return (
    <div className="pm-table-container">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 20,
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: 18, color: '#fff' }}>Analytics & Reports</h2>
          <p style={{ margin: '4px 0 0', fontSize: 11, color: '#848a9e' }}>
            Compare customer enquiries and campaign engagement over time
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <select
            value={period.year}
            onChange={(e) => setPeriod({ ...period, year: e.target.value })}
            style={{
              padding: '6px 10px',
              borderRadius: 6,
              background: '#1a1e2b',
              color: '#fff',
              border: '1px solid var(--pm-border)',
            }}
          >
            {years.map((y) => (
              <option key={y}>{y}</option>
            ))}
          </select>
          <select
            value={period.month}
            onChange={(e) => setPeriod({ ...period, month: e.target.value })}
            style={{
              padding: '6px 10px',
              borderRadius: 6,
              background: '#1a1e2b',
              color: '#fff',
              border: '1px solid var(--pm-border)',
            }}
          >
            <option value="">Full year</option>
            {Array.from({ length: 12 }, (_, i) => (
              <option value={i + 1} key={i}>
                {new Date(2020, i).toLocaleString('en', { month: 'long' })}
              </option>
            ))}
          </select>
          <button className="pm-secondary-btn" onClick={() => download('enquiries')}>
            ↓ Enquiry report
          </button>
          <button className="pm-secondary-btn" onClick={() => download('campaigns')}>
            ↓ Campaign report
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="pm-metrics-grid">
        <div className="pm-metric-card">
          <div className="pm-metric-icon">
            <ContactRound size={18} />
          </div>
          <div>
            <small>Enquiries</small>
            <strong>{number.format(data.totals?.enquiries || 0)}</strong>
            <p>Total conversations received</p>
          </div>
        </div>
        <div className="pm-metric-card">
          <div className="pm-metric-icon">
            <FileText size={18} />
          </div>
          <div>
            <small>Campaigns</small>
            <strong>{number.format(data.totals?.campaigns || 0)}</strong>
            <p>Workspace campaigns sent</p>
          </div>
        </div>
        <div className="pm-metric-card">
          <div className="pm-metric-icon">
            <Send size={18} />
          </div>
          <div>
            <small>Messages sent</small>
            <strong>{number.format(data.totals?.sent || 0)}</strong>
            <p>{data.totals?.delivered || 0} delivered</p>
          </div>
        </div>
        <div className="pm-metric-card">
          <div className="pm-metric-icon">
            <BarChart3 size={18} />
          </div>
          <div>
            <small>Messages opened</small>
            <strong>{number.format(data.totals?.opened || 0)}</strong>
            <p>{data.totals?.clicked || 0} clicked</p>
          </div>
        </div>
      </div>

      {/* Dual trend bar chart */}
      <div className="pm-panel-card" style={{ padding: 24 }}>
        <h3 style={{ margin: '0 0 4px', fontSize: 14, color: '#fff' }}>Activity trend</h3>
        <p style={{ margin: '0 0 20px', fontSize: 11, color: '#848a9e' }}>
          {period.month ? 'Daily breakdown for selected month' : 'Monthly breakdown for selected year'}
        </p>

        {trends.length ? (
          <div className="dual-chart">
            {trends.map((x) => (
              <div key={x.label}>
                <span>
                  <i
                    style={{ height: `${(x.enquiries / max) * 100}%` }}
                    title={`${x.enquiries} enquiries`}
                  />
                  <b
                    style={{ height: `${(x.campaigns / max) * 100}%` }}
                    title={`${x.campaigns} campaigns`}
                  />
                </span>
                <small>{formatPeriod(x.label, !!period.month)}</small>
              </div>
            ))}
          </div>
        ) : (
          <div className="pm-empty-view">
            <p>No activity recorded for this period.</p>
          </div>
        )}
        <div className="chart-key">
          <span className="enquiry-key" />
          Enquiries <span className="campaign-key" />
          Campaigns
        </div>
      </div>

      {/* Pie cards */}
      <div className="pie-grid">
        <PieCard
          title="Enquiry status"
          data={(data.enquiry_statuses || []).map((x) => ({
            label: x.status.replaceAll('_', ' '),
            value: x.value,
          }))}
        />
        <PieCard
          title="Campaign status"
          data={(data.campaign_statuses || []).map((x) => ({
            label: x.status,
            value: x.value,
          }))}
        />
        <PieCard title="Enquiries by team" data={data.enquiry_teams || []} />
      </div>
    </div>
  )
}

function mergeTrends(trend = {}) {
  const map = {}
  for (const item of trend.enquiries || [])
    map[item.label] = { label: item.label, enquiries: item.value, campaigns: 0 }
  for (const item of trend.campaigns || [])
    map[item.label] = { ...(map[item.label] || { label: item.label, enquiries: 0 }), campaigns: item.value }
  return Object.values(map).sort((a, b) => a.label.localeCompare(b.label))
}

function formatPeriod(value, daily) {
  return new Date(value + 'T00:00:00').toLocaleDateString('en-IN', daily ? { day: '2-digit' } : { month: 'short' })
}

function PieCard({ title, data }) {
  const colors = ['#9384f2', '#52bb89', '#5ea8df', '#dfbc74', '#ea7070']
  const total = data.reduce((sum, x) => sum + x.value, 0)
  let cursor = 0
  const gradient = data
    .map((x, i) => {
      const start = cursor
      cursor += total ? (x.value / total) * 360 : 0
      return `${colors[i % colors.length]} ${start}deg ${cursor}deg`
    })
    .join(',')

  return (
    <section className="pm-panel-card" style={{ padding: 20 }}>
      <h3 style={{ margin: '0 0 4px', fontSize: 13, color: '#fff' }}>{title}</h3>
      <p style={{ margin: '0 0 16px', fontSize: 10, color: '#848a9e' }}>{total} total records</p>
      {total ? (
        <div className="pie-content">
          <div className="pie" style={{ background: `conic-gradient(${gradient})` }}>
            <span>{total}</span>
          </div>
          <div className="pie-legend">
            {data.map((x, i) => (
              <div key={x.label}>
                <i style={{ background: colors[i % colors.length] }} />
                <span>{x.label}</span>
                <strong>{x.value}</strong>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p style={{ fontSize: 11, color: '#686e82' }}>No data for this breakdown</p>
      )}
    </section>
  )
}

/* ==========================================================
   SETTINGS & IAM VIEW
   ========================================================== */
function SettingsView({
  channel,
  setChannel,
  submit,
  busy,
  members,
  user,
  saveMember,
  deleteMember,
  openInvite,
}) {
  const f = (k) => ({
    value: channel[k] ?? '',
    onChange: (e) => setChannel({ ...channel, [k]: e.target.value }),
  })

  return (
    <div className="pm-table-container">
      {/* WhatsApp Channel Config */}
      <div className="pm-panel-card">
        <div className="pm-panel-header">
          <div>
            <h2>WhatsApp Business Channel Configuration</h2>
            <p>Configure public Meta channel details, numbers, and default routing logic</p>
          </div>
        </div>

        <div style={{ padding: 24 }}>
          <form className="pm-form" onSubmit={submit}>
            <label>
              Display label
              <input required {...f('label')} />
            </label>
            <label>
              Business WhatsApp number
              <input required {...f('number')} />
            </label>
            <label>
              Meta Phone Number ID
              <input {...f('phone_number_id')} />
            </label>
            <label>
              Forwarding phone number
              <input {...f('forwarding_number')} />
            </label>
            <label>
              Default routing department
              <select {...f('default_team')}>
                <option>Support</option>
                <option>Sales</option>
                <option>HR</option>
                <option>Billing</option>
              </select>
            </label>
            <label style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: 10 }}>
              <input
                type="checkbox"
                style={{ width: 'auto' }}
                checked={!!channel.is_active}
                onChange={(e) => setChannel({ ...channel, is_active: e.target.checked })}
              />
              <span>Channel active (Accept incoming WhatsApp messages)</span>
            </label>
            <footer>
              <button className="pm-primary-btn" disabled={busy}>
                Save channel settings
              </button>
            </footer>
          </form>
        </div>
      </div>

      {/* Webhook details */}
      <div className="pm-panel-card" style={{ padding: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <Settings2 size={18} color="#aaa4ff" />
          <h3 style={{ margin: 0, fontSize: 14, color: '#fff' }}>Webhook callback URL</h3>
        </div>
        <p style={{ margin: '0 0 10px', fontSize: 11, color: '#848a9e' }}>
          Register this callback endpoint in your Meta for Developers dashboard:
        </p>
        <code
          style={{
            display: 'block',
            padding: '10px 14px',
            background: '#10131d',
            border: '1px solid var(--pm-border)',
            borderRadius: 8,
            color: '#aaa4ff',
            fontSize: 12,
          }}
        >
          {window.location.origin}/api/whatsapp/webhook/
        </code>
      </div>

      {/* IAM Platform Identities */}
      <div className="pm-panel-card">
        <div className="pm-panel-header">
          <div>
            <h2>Identity & Access Management (IAM)</h2>
            <p>{members.length} team members and operational roles in this workspace</p>
          </div>
          <button className="pm-primary-btn" onClick={openInvite}>
            <Plus size={14} /> Invite member
          </button>
        </div>

        {members.length ? (
          <table className="pm-dark-table">
            <thead>
              <tr>
                <th>Identity</th>
                <th>Role</th>
                <th>Number access</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <IAMMemberRow
                  key={m.id}
                  member={m}
                  currentUser={user}
                  save={saveMember}
                  remove={deleteMember}
                />
              ))}
            </tbody>
          </table>
        ) : (
          <div className="pm-empty-view">
            <UsersRound size={32} />
            <strong>No members found</strong>
          </div>
        )}
      </div>
    </div>
  )
}

function IAMMemberRow({ member, currentUser, save, remove }) {
  const current = member.effective_role || member.role
  const [role, setRole] = useState(current)
  const [numberAccess, setNumberAccess] = useState(member.number_access || 'both')
  const [saving, setSaving] = useState(false)

  const isSelf = member.id === currentUser?.id
  const isOwner = currentUser?.role === 'owner'
  const canModify = !isSelf && (current !== 'owner' || isOwner)

  async function handleSave() {
    setSaving(true)
    try {
      await save(member.id, role, numberAccess)
    } finally {
      setSaving(false)
    }
  }

  return (
    <tr>
      <td>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span className="pm-avatar small" style={{ background: getAvatarColor(personName(member)) }}>
            {initials(member)}
          </span>
          <div>
            <strong style={{ color: '#fff' }}>{personName(member)}</strong>
            <div style={{ fontSize: 10, color: '#848a9e' }}>{member.email}</div>
          </div>
        </div>
      </td>
      <td>
        {canModify ? (
          <select
            value={role}
            disabled={saving}
            onChange={(e) => setRole(e.target.value)}
            style={{
              padding: '4px 8px',
              background: '#10131d',
              color: '#fff',
              border: '1px solid var(--pm-border)',
              borderRadius: 6,
            }}
          >
            <option value="viewer">Viewer</option>
            <option value="editor">Editor</option>
            <option value="admin">Administrator</option>
            {isOwner && <option value="owner">Owner</option>}
          </select>
        ) : (
          <span className="pm-tag">{roleName(current)}</span>
        )}
      </td>
      <td>
        {canModify ? (
          <select
            value={numberAccess}
            disabled={saving}
            onChange={(e) => setNumberAccess(e.target.value)}
            style={{
              padding: '4px 8px',
              background: '#10131d',
              color: '#fff',
              border: '1px solid var(--pm-border)',
              borderRadius: 6,
            }}
          >
            <option value="india">India only</option>
            <option value="us">US only</option>
            <option value="both">India and US</option>
          </select>
        ) : (
          <span>{numberAccessName(member.number_access)}</span>
        )}
      </td>
      <td>
        <span className={`pm-status-badge ${member.is_active === false ? 'inactive' : 'active'}`}>
          {member.is_active === false ? 'inactive' : 'active'}
        </span>
      </td>
      <td>
        {canModify && (
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className="pm-primary-btn"
              style={{ padding: '4px 8px', fontSize: 10 }}
              disabled={
                saving ||
                (role === current && numberAccess === (member.number_access || 'both'))
              }
              onClick={handleSave}
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
            <button
              className="pm-danger-btn"
              disabled={saving}
              onClick={() => remove(member.id)}
            >
              Delete
            </button>
          </div>
        )}
      </td>
    </tr>
  )
}

function AdministrationConsole({
  user,
  tenant,
  selectedBusiness,
  section,
  setSection,
  settingsTab,
  setSettingsTab,
  iamTab,
  setIamTab,
  accountTab,
  setAccountTab,
  toast,
}) {
  const setupSteps = [
    { name: 'Organization profile', status: 'completed', desc: 'Business identity and contact details' },
    { name: 'Connect WhatsApp Business', status: 'completed', desc: 'Meta account and phone number connection' },
    { name: 'Invite team members', status: 'pending', desc: 'Add owners, admins, and agents' },
    { name: 'Configure roles and permissions', status: 'pending', desc: 'Apply least-privilege access policy' },
    { name: 'Add billing information', status: 'pending', desc: 'Subscription and payment preferences' },
  ]

  const overviewCards = [
    {
      title: 'WhatsApp Connection',
      value: 'Connected',
      meta: 'Cloudtronix Support · +91 98765 43210',
      info: 'Business ID: 1234567890 · Last sync: 2 minutes ago',
      action: 'Manage Configuration',
      icon: MessageSquareText,
    },
    {
      title: 'Team Members',
      value: '12 Active Users',
      meta: '2 Pending Invitations',
      info: '4 Owners, 2 Managers, 7 Agents',
      action: 'Manage Users',
      icon: UsersRound,
    },
    {
      title: 'Subscription',
      value: 'Professional Plan',
      meta: 'Next billing date: 20 October 2026',
      info: '₹9,999 / month · 10 seats included',
      action: 'Manage Subscription',
      icon: CreditCard,
    },
    {
      title: 'Security',
      value: 'MFA enabled',
      meta: 'Password policy compliant',
      info: 'Last security review: 14 September 2026',
      action: 'Security Settings',
      icon: ShieldCheck,
    },
  ]

  const recentActivity = [
    { actor: 'Amit Sharma', action: 'Invited user', resource: 'Support User', date: 'Today · 09:42', status: 'Success' },
    { actor: 'Neha Patil', action: 'Role updated', resource: 'Operations Manager', date: 'Yesterday · 16:25', status: 'Success' },
    { actor: 'System', action: 'WhatsApp number connected', resource: '+91 98765 43210', date: '2 days ago · 10:18', status: 'Success' },
    { actor: 'Rahul Verma', action: 'Payment method updated', resource: 'Visa •••• 4242', date: '4 days ago · 11:09', status: 'Success' },
    { actor: 'System', action: 'Subscription changed', resource: 'Professional Plan', date: '7 days ago · 08:31', status: 'Success' },
  ]

  const adminNav = [
    { key: 'overview', label: 'Overview', icon: LayoutGrid },
    { key: 'settings', label: 'Settings', icon: Settings2 },
    { key: 'iam', label: 'IAM', icon: UserCog },
    { key: 'account', label: 'Account', icon: CreditCard },
    { key: 'audit', label: 'Audit Logs', icon: FileClock },
  ]

  const settingsTabs = [
    { key: 'organization', label: 'Organization Profile' },
    { key: 'whatsapp', label: 'WhatsApp Configuration' },
    { key: 'security', label: 'Security' },
    { key: 'notifications', label: 'Notifications' },
    { key: 'integrations', label: 'Integrations' },
  ]

  const iamTabs = [
    { key: 'users', label: 'Users' },
    { key: 'roles', label: 'Roles' },
    { key: 'teams', label: 'Teams' },
    { key: 'policies', label: 'Permission Policies' },
  ]

  const accountTabs = [
    { key: 'subscription', label: 'Subscription' },
    { key: 'billing', label: 'Billing Details' },
    { key: 'payment-methods', label: 'Payment Methods' },
    { key: 'invoices', label: 'Invoices' },
    { key: 'usage', label: 'Usage' },
  ]

  const completion = Math.round((setupSteps.filter((step) => step.status === 'completed').length / setupSteps.length) * 100)

  return (
    <div className="pm-admin-shell">
      <aside className="pm-admin-sidenav">
        <div className="pm-admin-sidenav-title">
          <span className="pm-admin-pill">Administration</span>
          <h3>{tenant?.name || 'Cloudtronix Demo Pvt Ltd'}</h3>
        </div>

        <nav className="pm-admin-nav">
          {adminNav.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              type="button"
              className={section === key ? 'active' : ''}
              onClick={() => setSection(key)}
            >
              <Icon size={15} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
      </aside>

      <section className="pm-admin-main">
        <header className="pm-admin-header">
          <div>
            <h1>Administration</h1>
            <p>Manage your organization, WhatsApp integration, users, security, permissions, and billing.</p>
          </div>
          <button className="pm-primary-btn" type="button" onClick={() => toast('Invite team member flow ready', 'success')}>
            <Plus size={14} /> Invite User
          </button>
        </header>

        {section === 'overview' && (
          <>
            <div className="pm-admin-setup-card">
              <div className="pm-admin-setup-top">
                <div>
                  <span className="pm-admin-subtitle">Account Setup</span>
                  <h2>Complete your account setup</h2>
                </div>
                <div className="pm-admin-progress-wrap">
                  <strong>{completion}% completed</strong>
                  <div className="pm-admin-progress-bar"><span style={{ width: `${completion}%` }} /></div>
                </div>
              </div>

              <div className="pm-admin-setup-list">
                {setupSteps.map((step) => (
                  <div key={step.name} className={`pm-admin-step ${step.status === 'completed' ? 'done' : ''}`}>
                    <span className="pm-admin-step-icon">{step.status === 'completed' ? <Check size={14} /> : <ChevronRight size={14} />}</span>
                    <div className="pm-admin-step-copy">
                      <div className="pm-admin-step-row">
                        <strong>{step.name}</strong>
                        <span className={`pm-status-badge ${step.status === 'completed' ? 'active' : 'pending'}`}>
                          {step.status === 'completed' ? 'Completed' : 'Pending'}
                        </span>
                      </div>
                      <p>{step.desc}</p>
                    </div>
                    <button type="button" className="pm-secondary-btn small">
                      {step.status === 'completed' ? 'Review' : 'Configure'}
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="pm-admin-grid">
              {overviewCards.map(({ title, value, meta, info, action, icon: Icon }) => (
                <div key={title} className="pm-admin-card">
                  <div className="pm-admin-card-head">
                    <div className="pm-admin-card-icon"><Icon size={18} /></div>
                    <span>{title}</span>
                  </div>
                  <div className="pm-admin-card-body">
                    <strong>{value}</strong>
                    <p>{meta}</p>
                    <small>{info}</small>
                  </div>
                  <button type="button" className="pm-secondary-btn small nowrap">{action}</button>
                </div>
              ))}
            </div>

            <div className="pm-admin-activity-card">
              <div className="pm-admin-section-title">
                <h3>Recent Administrative Activity</h3>
                <button type="button" className="pm-secondary-btn small">View All Audit Logs</button>
              </div>

              <table className="pm-dark-table compact">
                <thead>
                  <tr>
                    <th>Actor</th>
                    <th>Action</th>
                    <th>Resource</th>
                    <th>Date/Time</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {recentActivity.map((item, index) => (
                    <tr key={`${item.actor}-${index}`}>
                      <td>{item.actor}</td>
                      <td>{item.action}</td>
                      <td>{item.resource}</td>
                      <td>{item.date}</td>
                      <td><span className="pm-status-badge active">{item.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {section === 'settings' && (
          <div className="pm-admin-module">
            <div className="pm-admin-tab-bar">
              {settingsTabs.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  className={settingsTab === tab.key ? 'active' : ''}
                  onClick={() => setSettingsTab(tab.key)}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="pm-admin-panel">
              {settingsTab === 'organization' && (
                <form className="pm-admin-form">
                  <div className="pm-admin-form-grid">
                    <label>Organization Name<input defaultValue="Cloudtronix Demo Pvt Ltd" /></label>
                    <label>Legal Business Name<input defaultValue="Cloudtronix Solutions Pvt Ltd" /></label>
                    <label>Organization ID<input value="ORG-CLD-2048" readOnly /></label>
                    <label>Industry<select defaultValue="Technology"><option>Technology</option><option>Healthcare</option><option>Retail</option></select></label>
                    <label>Business Email<input type="email" defaultValue="hello@cloudtronix.io" /></label>
                    <label>Business Phone<input type="tel" defaultValue="+91 98765 43210" /></label>
                    <label>Website<input defaultValue="https://cloudtronix.io" /></label>
                    <label>Country<select defaultValue="India"><option>India</option><option>United States</option></select></label>
                    <label>State<input defaultValue="Maharashtra" /></label>
                    <label>City<input defaultValue="Pune" /></label>
                    <label>Postal Code<input defaultValue="411057" /></label>
                    <label>Timezone<select defaultValue="Asia/Kolkata"><option>Asia/Kolkata</option><option>UTC</option></select></label>
                    <label>Default Language<select defaultValue="English"><option>English</option><option>Hindi</option></select></label>
                    <label className="wide">Business Address<textarea rows="3" defaultValue="B-204, Blue Ridge Commerce Park, Pune, Maharashtra 411057" /></label>
                  </div>

                  <div className="pm-admin-upload-box">
                    <div>
                      <strong>Organization Logo</strong>
                      <p>Recommended: 512 × 512 PNG or JPG</p>
                    </div>
                    <button type="button" className="pm-secondary-btn small">Upload Logo</button>
                  </div>

                  <div className="pm-admin-form-actions">
                    <button type="button" className="pm-secondary-btn">Cancel</button>
                    <button type="submit" className="pm-primary-btn">Save Changes</button>
                  </div>
                </form>
              )}

              {settingsTab === 'whatsapp' && (
                <div className="pm-admin-vertical-panel">
                  <div className="pm-admin-status-banner success">
                    <div>
                      <strong>WhatsApp Business</strong>
                      <span>Connected</span>
                    </div>
                    <p>Your WhatsApp Business account is connected and ready to receive messages.</p>
                  </div>

                  <div className="pm-admin-info-columns">
                    <div>
                      <h4>Connection Details</h4>
                      <dl>
                        <div><dt>Meta Business Account</dt><dd>Cloudtronix</dd></div>
                        <div><dt>WhatsApp Business Account ID</dt><dd>WB-01-2048</dd></div>
                        <div><dt>Phone Number ID</dt><dd>PNID_987654321</dd></div>
                        <div><dt>Business Phone Number</dt><dd>+91 98765 43210</dd></div>
                        <div><dt>Webhook Status</dt><dd>Active</dd></div>
                        <div><dt>Last Synchronization</dt><dd>2 minutes ago</dd></div>
                      </dl>
                    </div>
                    <div>
                      <h4>Actions</h4>
                      <div className="pm-admin-button-stack">
                        <button type="button" className="pm-primary-btn">Connect WhatsApp Business</button>
                        <button type="button" className="pm-secondary-btn">Test Connection</button>
                        <button type="button" className="pm-secondary-btn">Refresh Status</button>
                        <button type="button" className="pm-secondary-btn danger">Disconnect</button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {settingsTab === 'security' && (
                <div className="pm-admin-form stacked">
                  <div className="pm-admin-form-group">
                    <h4>Password</h4>
                    <label>Current Password<input type="password" placeholder="Enter current password" /></label>
                    <label>New Password<input type="password" placeholder="Create a strong password" /></label>
                    <label>Confirm Password<input type="password" placeholder="Repeat new password" /></label>
                    <div className="pm-admin-password-meter"><span style={{ width: '80%' }} /></div>
                    <small>Minimum 8 characters, uppercase, lowercase, number, and special character.</small>
                    <button type="button" className="pm-primary-btn">Update Password</button>
                  </div>

                  <div className="pm-admin-form-group">
                    <h4>Multi-Factor Authentication</h4>
                    <div className="pm-admin-row-line">
                      <strong>Multi-Factor Authentication</strong>
                      <span className="pm-status-badge active">Enabled</span>
                    </div>
                    <div className="pm-admin-row-line">
                      <strong>Authenticator App</strong>
                      <span>Primary</span>
                    </div>
                    <div className="pm-admin-row-line">
                      <strong>Email OTP</strong>
                      <span>Backup</span>
                    </div>
                  </div>

                  <div className="pm-admin-form-group">
                    <h4>Sessions</h4>
                    <div className="pm-admin-session-list">
                      <div className="pm-admin-session-row">
                        <div><strong>Chrome on Mac</strong><small>22.12.11 • 10.0.2.15</small></div>
                        <span className="pm-status-badge active">Current</span>
                      </div>
                      <div className="pm-admin-session-row">
                        <div><strong>Safari on iPhone</strong><small>11:18 AM • Pune, India</small></div>
                        <button type="button" className="pm-secondary-btn small">Sign Out</button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {settingsTab === 'notifications' && (
                <div className="pm-admin-notification-grid">
                  {['Security Alerts','Billing Alerts','WhatsApp Connection Alerts','System Alerts','User Management Alerts','Campaign Alerts'].map((item) => (
                    <label key={item} className="pm-admin-toggle-row">
                      <span>{item}</span>
                      <div>
                        <input type="checkbox" defaultChecked />
                        <span>Email</span>
                        <input type="checkbox" defaultChecked />
                        <span>In-App</span>
                      </div>
                    </label>
                  ))}
                </div>
              )}

              {settingsTab === 'integrations' && (
                <div className="pm-admin-empty-state">
                  <BadgeCheck size={30} />
                  <h4>No third-party integrations configured yet</h4>
                  <p>Connect CRMs, support tools, or custom automation providers from this workspace.</p>
                  <button type="button" className="pm-primary-btn">Add Integration</button>
                </div>
              )}
            </div>
          </div>
        )}

        {section === 'iam' && (
          <div className="pm-admin-module">
            <div className="pm-admin-tab-bar">
              {iamTabs.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  className={iamTab === tab.key ? 'active' : ''}
                  onClick={() => setIamTab(tab.key)}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="pm-admin-panel">
              {iamTab === 'users' && (
                <>
                  <div className="pm-admin-section-title">
                    <h3>Users</h3>
                    <button type="button" className="pm-primary-btn small">Invite User</button>
                  </div>
                  <table className="pm-dark-table">
                    <thead>
                      <tr>
                        <th>User</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Team</th>
                        <th>Status</th>
                        <th>Last Login</th>
                        <th>MFA</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr><td>Amit Sharma</td><td>amit@cloudtronix.io</td><td>Owner</td><td>Operations</td><td><span className="pm-status-badge active">Active</span></td><td>Today</td><td>Enabled</td><td>View</td></tr>
                      <tr><td>Neha Patil</td><td>neha@cloudtronix.io</td><td>Administrator</td><td>Support</td><td><span className="pm-status-badge active">Active</span></td><td>Yesterday</td><td>Enabled</td><td>Edit</td></tr>
                      <tr><td>Rahul Verma</td><td>rahul@cloudtronix.io</td><td>Agent</td><td>Sales</td><td><span className="pm-status-badge active">Active</span></td><td>2 days ago</td><td>Enabled</td><td>View</td></tr>
                      <tr><td>Support User</td><td>support@cloudtronix.io</td><td>Agent</td><td>Support</td><td><span className="pm-status-badge pending">Invited</span></td><td>Never</td><td>Pending</td><td>Resend</td></tr>
                    </tbody>
                  </table>
                </>
              )}

              {iamTab === 'roles' && (
                <div className="pm-admin-role-grid">
                  {['Owner','Administrator','Manager','Agent','Billing Administrator','Read Only'].map((role) => (
                    <div key={role} className="pm-admin-role-card">
                      <div className="pm-admin-role-header">
                        <strong>{role}</strong>
                        <span>{role === 'Owner' ? 'System' : 'Custom'}</span>
                      </div>
                      <p>{role === 'Owner' ? 'Full administrative control across the tenant.' : 'Operational permissions tailored for this workspace.'}</p>
                      <small>Users: {role === 'Owner' ? 1 : role === 'Administrator' ? 2 : role === 'Manager' ? 3 : role === 'Agent' ? 7 : role === 'Billing Administrator' ? 1 : 4}</small>
                      <button type="button" className="pm-secondary-btn small">Manage</button>
                    </div>
                  ))}
                </div>
              )}

              {iamTab === 'teams' && (
                <div className="pm-admin-role-grid">
                  {['Sales','Support','Finance','Operations','Marketing'].map((team) => (
                    <div key={team} className="pm-admin-role-card">
                      <div className="pm-admin-role-header">
                        <strong>{team}</strong>
                        <span>Active</span>
                      </div>
                      <p>Department queue routing and operational ownership for {team.toLowerCase()} workflows.</p>
                      <small>Members: {team === 'Sales' ? 4 : team === 'Support' ? 6 : team === 'Finance' ? 2 : team === 'Operations' ? 3 : 2}</small>
                      <button type="button" className="pm-secondary-btn small">Manage Team</button>
                    </div>
                  ))}
                </div>
              )}

              {iamTab === 'policies' && (
                <div className="pm-admin-policy-panel">
                  <div className="pm-admin-policy-header">
                    <h4>Permission Matrix</h4>
                    <div><button type="button" className="pm-secondary-btn small">Select All</button><button type="button" className="pm-secondary-btn small">Clear All</button></div>
                  </div>
                  <table className="pm-dark-table compact">
                    <thead><tr><th>Module</th><th>View</th><th>Create</th><th>Edit</th><th>Delete</th></tr></thead>
                    <tbody>
                      <tr><td>Dashboard</td><td><input type="checkbox" defaultChecked /></td><td></td><td></td><td></td></tr>
                      <tr><td>Conversations</td><td><input type="checkbox" defaultChecked /></td><td><input type="checkbox" defaultChecked /></td><td><input type="checkbox" defaultChecked /></td><td><input type="checkbox" /></td></tr>
                      <tr><td>Campaigns</td><td><input type="checkbox" defaultChecked /></td><td><input type="checkbox" defaultChecked /></td><td><input type="checkbox" /></td><td><input type="checkbox" /></td></tr>
                      <tr><td>Administration</td><td><input type="checkbox" defaultChecked /></td><td><input type="checkbox" defaultChecked /></td><td><input type="checkbox" defaultChecked /></td><td><input type="checkbox" /></td></tr>
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {section === 'account' && (
          <div className="pm-admin-module">
            <div className="pm-admin-tab-bar">
              {accountTabs.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  className={accountTab === tab.key ? 'active' : ''}
                  onClick={() => setAccountTab(tab.key)}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="pm-admin-panel">
              {accountTab === 'subscription' && (
                <div className="pm-admin-account-card">
                  <div className="pm-admin-account-header">
                    <div>
                      <span className="pm-admin-subtitle">Current Plan</span>
                      <h3>Professional</h3>
                    </div>
                    <span className="pm-status-badge active">Active</span>
                  </div>
                  <div className="pm-admin-plan-grid">
                    <div><small>Billing Cycle</small><strong>Monthly</strong></div>
                    <div><small>Price</small><strong>₹9,999 / month</strong></div>
                    <div><small>Renewal Date</small><strong>20 October 2026</strong></div>
                    <div><small>Seats</small><strong>10 included</strong></div>
                    <div><small>WhatsApp Numbers</small><strong>3 included</strong></div>
                    <div><small>Allowance</small><strong>25,000 conversations</strong></div>
                  </div>
                  <div className="pm-admin-form-actions">
                    <button type="button" className="pm-secondary-btn">Change Plan</button>
                    <button type="button" className="pm-primary-btn">Upgrade Plan</button>
                    <button type="button" className="pm-secondary-btn danger">Cancel Subscription</button>
                  </div>
                </div>
              )}

              {accountTab === 'billing' && (
                <form className="pm-admin-form">
                  <div className="pm-admin-form-grid">
                    <label>Legal Company Name<input defaultValue="Cloudtronix Solutions Pvt Ltd" /></label>
                    <label>Billing Email<input type="email" defaultValue="billing@cloudtronix.io" /></label>
                    <label>Tax / GST Number<input defaultValue="27AABCC1234D1ZQ" /></label>
                    <label>Country<select defaultValue="India"><option>India</option></select></label>
                    <label>State<input defaultValue="Maharashtra" /></label>
                    <label>City<input defaultValue="Pune" /></label>
                    <label>Postal Code<input defaultValue="411057" /></label>
                    <label className="wide">Billing Address<textarea rows="3" defaultValue="B-204, Blue Ridge Commerce Park, Pune, Maharashtra 411057" /></label>
                  </div>
                  <div className="pm-admin-form-actions"><button type="button" className="pm-secondary-btn">Cancel</button><button type="submit" className="pm-primary-btn">Save Billing Information</button></div>
                </form>
              )}

              {accountTab === 'payment-methods' && (
                <div className="pm-admin-payment-grid">
                  <div className="pm-admin-payment-card">
                    <div className="pm-admin-payment-head"><strong>Visa</strong><span>Primary</span></div>
                    <p>•••• 4242</p>
                    <small>Expires 12/29</small>
                    <div className="pm-admin-payment-actions"><button type="button" className="pm-secondary-btn small">Update</button><button type="button" className="pm-secondary-btn small">Remove</button></div>
                  </div>
                  <div className="pm-admin-payment-card add"><button type="button" className="pm-primary-btn">Add Payment Method</button></div>
                </div>
              )}

              {accountTab === 'invoices' && (
                <table className="pm-dark-table">
                  <thead><tr><th>Invoice Number</th><th>Billing Period</th><th>Date</th><th>Amount</th><th>Status</th><th>Payment Method</th><th>Actions</th></tr></thead>
                  <tbody>
                    <tr><td>INV-2026-014</td><td>Sep 2026</td><td>15 Sep 2026</td><td>₹9,999</td><td><span className="pm-status-badge active">Paid</span></td><td>Visa ••••4242</td><td>View</td></tr>
                    <tr><td>INV-2026-013</td><td>Aug 2026</td><td>15 Aug 2026</td><td>₹9,999</td><td><span className="pm-status-badge active">Paid</span></td><td>Visa ••••4242</td><td>Download</td></tr>
                  </tbody>
                </table>
              )}

              {accountTab === 'usage' && (
                <div className="pm-admin-usage-list">
                  {[
                    ['Team Members', '8 / 10', 80],
                    ['WhatsApp Numbers', '2 / 3', 66],
                    ['Monthly Conversations', '14,250 / 25,000', 57],
                    ['Campaign Messages', '40,200 / 100,000', 40],
                    ['Storage', '2.4 GB / 10 GB', 24],
                  ].map(([label, value, percent]) => (
                    <div key={label} className="pm-admin-usage-row">
                      <div className="pm-admin-usage-head"><strong>{label}</strong><span>{value}</span></div>
                      <div className="pm-admin-progress-bar"><span style={{ width: `${percent}%` }} /></div>
                    </div>
                  ))}
                  <div className="pm-admin-usage-alert">You have used 82% of your monthly conversation allowance.</div>
                </div>
              )}
            </div>
          </div>
        )}

        {section === 'audit' && (
          <div className="pm-admin-module">
            <div className="pm-admin-panel">
              <div className="pm-admin-section-title">
                <h3>Audit Logs</h3>
                <button type="button" className="pm-secondary-btn small">Export CSV</button>
              </div>
              <table className="pm-dark-table">
                <thead><tr><th>Timestamp</th><th>User</th><th>Action</th><th>Module</th><th>Resource</th><th>IP Address</th><th>Status</th></tr></thead>
                <tbody>
                  <tr><td>2026-09-20 09:42</td><td>Amit Sharma</td><td>Invited user</td><td>IAM</td><td>Support User</td><td>10.0.10.42</td><td><span className="pm-status-badge active">Success</span></td></tr>
                  <tr><td>2026-09-19 16:25</td><td>Neha Patil</td><td>Updated WhatsApp configuration</td><td>Settings</td><td>WhatsApp Business</td><td>10.0.10.18</td><td><span className="pm-status-badge active">Success</span></td></tr>
                  <tr><td>2026-09-18 11:09</td><td>Rahul Verma</td><td>Changed role permissions</td><td>IAM</td><td>Manager</td><td>10.0.10.21</td><td><span className="pm-status-badge active">Success</span></td></tr>
                  <tr><td>2026-09-17 08:31</td><td>System</td><td>Subscription renewed</td><td>Account</td><td>Professional Plan</td><td>127.0.0.1</td><td><span className="pm-status-badge active">Success</span></td></tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  )
}

/* ==========================================================
   BUSINESS WORKSPACE SELECTOR
   ========================================================== */
function BusinessSelector({ access, numbers, select, logout, busy, tenant, openQuotaModal, isSuperuser, openTenants, openAdmin }) {
  return (
    <main className="pm-selector-screen">
      <header className="pm-selector-header">
        <div className="pm-app-brand">
          <span className="pm-brand-icon">
            <MessageSquareText size={15} strokeWidth={2.4} />
          </span>
          <strong>Convernix</strong>
          <span className="pm-app-divider">/</span>
          <span className="pm-workspace-name">{tenant?.name || 'Workspace Portal'}</span>
          {tenant && (
            <span
              className={`pm-tier-badge pm-tier-${tenant.tier}`}
              onClick={openQuotaModal}
              title="Click to view plan and quota details"
            >
              {tenant.tier_display || tenant.tier?.toUpperCase()}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {openAdmin && (
            <button className="pm-secondary-btn" onClick={openAdmin} title="Administration Console">
              Administration
            </button>
          )}
          {isSuperuser && (
            <button className="pm-secondary-btn" onClick={openTenants} title="Platform Tenant Administration">
              Manage Tenants
            </button>
          )}
          <button className="pm-secondary-btn" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>

      <section className="pm-selector-body">
        <span className="pm-nav-label" style={{ padding: 0 }}>
          BUSINESS WORKSPACES
        </span>
        <h1>Choose a WhatsApp number</h1>
        <p>
          Organization: <strong style={{ color: '#fff' }}>{tenant?.name || 'Convernix Workspace'}</strong> ·
          Plan: <strong style={{ color: '#aaa4ff' }}>{tenant?.tier_display || 'Growth'}</strong> ({tenant?.numbers_count ?? numbers.length} of {tenant?.max_numbers ?? 'unlimited'} numbers active).
        </p>

        <div className="pm-selector-grid">
          {numbers.map((item) => {
            const isUs = item.label.toLowerCase().includes('usa') || item.number.startsWith('+1')
            return (
              <button
                key={item.id}
                type="button"
                className="pm-number-card"
                onClick={() => select(item)}
              >
                <div className="pm-flag-box">{isUs ? '🇺🇸' : '🇮🇳'}</div>
                <div>
                  <small style={{ color: '#52bb89', fontWeight: 600, fontSize: 9 }}>
                    {isUs ? 'UNITED STATES · LIVE CHANNEL' : 'INDIA · LIVE CHANNEL'}
                  </small>
                  <strong>{item.label}</strong>
                  <span>{item.number}</span>
                </div>
                <b>Open workspace →</b>
              </button>
            )
          })}
          {!busy && !numbers.length && (
            <div className="pm-empty-view" style={{ gridColumn: '1 / -1', padding: '32px 20px', textAlign: 'center' }}>
              <p style={{ marginBottom: 16 }}>No WhatsApp business numbers are currently provisioned for this workspace.</p>
              {openAdmin && (
                <button
                  type="button"
                  className="pm-primary-btn"
                  onClick={openAdmin}
                  style={{ display: 'inline-flex', margin: '0 auto' }}
                >
                  Launch Onboarding & Setup Console →
                </button>
              )}
            </div>
          )}
        </div>
      </section>

      <footer className="pm-selector-footer">
        Convernix Enterprise Operations · Multi-Tenant Architecture & Data Security
      </footer>
    </main>
  )
}

/* ==========================================================
   LOGIN FORM (INJECTED INTO LANDING PAGE)
   ========================================================== */
function Login({
  login,
  setLogin,
  submit,
  registerTenant,
  busy,
  notice,
  providers,
  initialMode,
  initialTier,
  onSwitchMode,
}) {
  const [mode, setMode] = useState(initialMode || (initialTier ? 'register' : 'signin'))
  const [regForm, setRegForm] = useState({
    company_name: '',
    tier: ['small', 'mid', 'large'].includes(initialTier) ? initialTier : 'small',
    first_name: '',
    last_name: '',
    email: '',
    phone_number: '',
    password: '',
  })
  const [regError, setRegError] = useState('')

  useEffect(() => {
    if (initialMode) {
      setMode(initialMode)
    } else if (initialTier) {
      setMode('register')
    }
  }, [initialMode, initialTier])

  useEffect(() => {
    if (['small', 'mid', 'large'].includes(initialTier)) {
      setRegForm((prev) => ({ ...prev, tier: initialTier }))
    }
  }, [initialTier])

  async function handleRegister(e) {
    e.preventDefault()
    setRegError('')
    try {
      await registerTenant(regForm)
    } catch (err) {
      setRegError(err.message || 'Registration failed')
    }
  }

  return (
    <>
      {mode === 'signin' ? (
        <>
          <span className="eyebrow">
            <span />
            YOUR CONVERNIX WORKSPACE
          </span>
          <h2 id="modal-title">Welcome back.</h2>
          <p className="modal-description">
            Sign in with your invited business identity to continue to your workspace.
          </p>
          <form className="demo-form auth-form" onSubmit={submit}>
            <div className="auth-providers">
              {['google', 'microsoft'].map((provider) => (
                <button
                  className="button button-secondary"
                  key={provider}
                  type="button"
                  disabled
                  aria-describedby="provider-note"
                >
                  <span aria-hidden="true">{provider === 'google' ? 'G' : '▦'}</span>
                  Continue with {provider === 'google' ? 'Google' : 'Microsoft'}
                  <small>{providers[provider]?.enabled ? 'Coming soon' : 'Not configured'}</small>
                </button>
              ))}
            </div>
            <small id="provider-note" className="form-footnote">
              Social sign-in is not available yet. Use your email and password.
            </small>
            <div className="auth-divider">or sign in with email</div>
            {notice && (
              <p className="form-error" role="alert">
                {notice.text}
              </p>
            )}
            <label>
              Email address
              <input
                required
                type="email"
                autoComplete="email"
                value={login.email}
                onChange={(e) => setLogin({ ...login, email: e.target.value })}
                placeholder="you@company.com"
              />
            </label>
            <label>
              Password
              <input
                required
                type="password"
                autoComplete="current-password"
                value={login.password}
                onChange={(e) => setLogin({ ...login, password: e.target.value })}
                placeholder="Enter your password"
              />
            </label>
            <button className="button button-primary form-submit" type="submit" disabled={busy}>
              {busy ? 'Signing in…' : 'Sign in'}
            </button>
            <div className="auth-switch-prompt">
              <span>New client?</span>
              <button
                type="button"
                className="auth-switch-btn"
                onClick={() => {
                  if (onSwitchMode) onSwitchMode('register')
                  setMode('register')
                }}
              >
                Sign up to create company workspace
              </button>
            </div>
          </form>
        </>
      ) : (
        <>
          <span className="eyebrow">
            <span />
            MULTI-TENANT ONBOARDING
          </span>
          <h2 id="modal-title">Create Company Workspace</h2>
          <p className="modal-description">
            Choose your organization scale (Basic, Standard, or Premium) and provision your company workspace.
          </p>
          {regError && (
            <p className="form-error" role="alert">
              {regError}
            </p>
          )}
          <form className="demo-form auth-form" onSubmit={handleRegister}>
            <label>
              Company / Business Name
              <input
                required
                type="text"
                value={regForm.company_name}
                onChange={(e) => setRegForm({ ...regForm, company_name: e.target.value })}
                placeholder="Acme Enterprises"
              />
            </label>

            <label style={{ marginBottom: 6 }}>Select Business Plan Tier</label>
            <div className="pm-tier-options">
              <div
                className={`pm-tier-option-card ${regForm.tier === 'small' ? 'selected' : ''}`}
                onClick={() => setRegForm({ ...regForm, tier: 'small' })}
                role="button"
                tabIndex={0}
              >
                <strong style={{ color: '#38bdf8' }}>Basic · ₹2,499/mo</strong>
                <span>1 Number · 3 Seats · 5 GB Storage</span>
              </div>
              <div
                className={`pm-tier-option-card ${regForm.tier === 'mid' ? 'selected' : ''}`}
                onClick={() => setRegForm({ ...regForm, tier: 'mid' })}
                role="button"
                tabIndex={0}
              >
                <strong style={{ color: '#34d399' }}>Standard · ₹6,499/mo</strong>
                <span>5 Numbers · 15 Seats · 10 GB Storage</span>
              </div>
              <div
                className={`pm-tier-option-card ${regForm.tier === 'large' ? 'selected' : ''}`}
                onClick={() => setRegForm({ ...regForm, tier: 'large' })}
                role="button"
                tabIndex={0}
              >
                <strong style={{ color: '#c084fc' }}>Premium · ₹8,499/mo</strong>
                <span>25 Numbers · 100 Seats · 15 GB Storage</span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <label>
                First name
                <input
                  required
                  type="text"
                  value={regForm.first_name}
                  onChange={(e) => setRegForm({ ...regForm, first_name: e.target.value })}
                  placeholder="Jane"
                />
              </label>
              <label>
                Last name
                <input
                  type="text"
                  value={regForm.last_name}
                  onChange={(e) => setRegForm({ ...regForm, last_name: e.target.value })}
                  placeholder="Doe"
                />
              </label>
            </div>

            <label>
              Work Email
              <input
                required
                type="email"
                value={regForm.email}
                onChange={(e) => setRegForm({ ...regForm, email: e.target.value })}
                placeholder="admin@company.com"
              />
            </label>

            <label>
              Phone number
              <input
                type="tel"
                value={regForm.phone_number}
                onChange={(e) => setRegForm({ ...regForm, phone_number: e.target.value })}
                placeholder="+1 555 019 2831"
              />
            </label>

            <label>
              Workspace Password
              <input
                required
                type="password"
                minLength={8}
                value={regForm.password}
                onChange={(e) => setRegForm({ ...regForm, password: e.target.value })}
                placeholder="Create a strong password"
              />
            </label>

            <button className="button button-primary form-submit" type="submit" disabled={busy}>
              {busy ? 'Creating workspace…' : 'Create & Launch Workspace'}
            </button>
            <div className="auth-switch-prompt">
              <span>Already have an account?</span>
              <button
                type="button"
                className="auth-switch-btn"
                onClick={() => {
                  if (onSwitchMode) onSwitchMode('signin')
                  setMode('signin')
                }}
              >
                Sign in to existing workspace
              </button>
            </div>
          </form>
        </>
      )}
    </>
  )
}

/* ==========================================================
   TENANT MANAGEMENT VIEW (PLATFORM ADMIN ONLY)
   ========================================================== */
function TenantsView({ tenants, openCreate, onUpdateTier, onToggleStatus, onDelete, busy }) {
  const smallCount = tenants.filter((t) => t.tier === 'small').length
  const midCount = tenants.filter((t) => t.tier === 'mid').length
  const largeCount = tenants.filter((t) => t.tier === 'large').length
  const activeCount = tenants.filter((t) => t.status === 'active').length

  return (
    <div className="pm-settings-page">
      <div className="pm-panel-card" style={{ padding: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Building2 size={20} color="#a855f7" />
              <h2 style={{ margin: 0, fontSize: 18, color: '#fff' }}>Tenant & Organization Management</h2>
            </div>
            <p style={{ margin: '4px 0 0', fontSize: 12, color: '#848a9e' }}>
              Multi-tenant architecture · Manage workspace boundaries, tiers, user quotas, and phone number allocations
            </p>
          </div>
          <button className="pm-primary-btn" onClick={openCreate} disabled={busy}>
            <Plus size={14} /> Provision Tenant
          </button>
        </div>

        {/* Overview Stats */}
        <div className="pm-metrics-grid" style={{ marginBottom: 24 }}>
          <div className="pm-metric-box">
            <span>TOTAL TENANTS</span>
            <div className="pm-metric-value">{tenants.length}</div>
            <small style={{ color: '#25d366' }}>{activeCount} active</small>
          </div>
          <div className="pm-metric-box">
            <span>STARTER (SMALL)</span>
            <div className="pm-metric-value">{smallCount}</div>
            <small style={{ color: '#38bdf8' }}>1 number · 3 users</small>
          </div>
          <div className="pm-metric-box">
            <span>GROWTH (MID)</span>
            <div className="pm-metric-value">{midCount}</div>
            <small style={{ color: '#34d399' }}>5 numbers · 15 users</small>
          </div>
          <div className="pm-metric-box">
            <span>ENTERPRISE (LARGE)</span>
            <div className="pm-metric-value">{largeCount}</div>
            <small style={{ color: '#c084fc' }}>25 numbers · 100 users</small>
          </div>
        </div>

        {/* Tenant Table */}
        {tenants.length ? (
          <table className="pm-dark-table">
            <thead>
              <tr>
                <th>Workspace / Tenant</th>
                <th>Tier</th>
                <th>Numbers</th>
                <th>Users</th>
                <th>Campaigns / Mo</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {tenants.map((t) => (
                <tr key={t.id}>
                  <td>
                    <div>
                      <strong style={{ color: '#fff' }}>{t.name}</strong>
                      <div style={{ fontSize: 10, color: '#848a9e' }}>slug: {t.slug} · ID #{t.id}</div>
                    </div>
                  </td>
                  <td>
                    <select
                      value={t.tier}
                      onChange={(e) => onUpdateTier(t.id, e.target.value)}
                      disabled={busy}
                      style={{
                        padding: '4px 8px',
                        background: '#10131d',
                        color: '#fff',
                        border: '1px solid var(--pm-border)',
                        borderRadius: 6,
                        fontSize: 11,
                      }}
                    >
                      <option value="small">Basic (Small)</option>
                      <option value="mid">Standard (Mid)</option>
                      <option value="large">Premium (Large)</option>
                    </select>
                  </td>
                  <td>
                    <span style={{ fontSize: 11, color: '#e2e8f0' }}>
                      {t.numbers_count ?? 0} / <strong>{t.max_numbers}</strong>
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize: 11, color: '#e2e8f0' }}>
                      {t.users_count ?? 0} / <strong>{t.max_users}</strong>
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize: 11, color: '#e2e8f0' }}>
                      {t.campaigns_count ?? 0} / <strong>{t.max_campaigns_monthly}</strong>
                    </span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className={`pm-status-badge ${t.status === 'active' ? 'active' : 'inactive'}`}
                      style={{ border: 'none', cursor: 'pointer' }}
                      onClick={() => onToggleStatus(t.id, t.status)}
                      title={`Click to ${t.status === 'active' ? 'suspend' : 'activate'}`}
                      disabled={busy}
                    >
                      {t.status_display || t.status}
                    </button>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="pm-danger-btn"
                      style={{ padding: '4px 8px', fontSize: 10 }}
                      onClick={() => onDelete(t.id, t.name)}
                      disabled={busy}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="pm-empty-view">
            <Building2 size={32} />
            <strong>No tenants found</strong>
          </div>
        )}
      </div>
    </div>
  )
}

/* ==========================================================
   QUOTA MODAL CONTENT
   ========================================================== */
function QuotaModalContent({ tenant }) {
  if (!tenant) return null

  const numbersPercent = Math.min(100, Math.round(((tenant.numbers_count || 0) / (tenant.max_numbers || 1)) * 100))
  const usersPercent = Math.min(100, Math.round(((tenant.users_count || 0) / (tenant.max_users || 1)) * 100))
  const campaignsPercent = Math.min(100, Math.round(((tenant.campaigns_count || 0) / (tenant.max_campaigns_monthly || 1)) * 100))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h3 style={{ margin: 0, color: '#fff', fontSize: 16 }}>{tenant.name}</h3>
          <p style={{ margin: '2px 0 0', fontSize: 11, color: '#848a9e' }}>Workspace Tenant #{tenant.id} · {tenant.slug}</p>
        </div>
        <span className={`pm-tier-badge pm-tier-${tenant.tier}`} style={{ fontSize: 11, padding: '4px 10px' }}>
          {tenant.tier_display}
        </span>
      </div>

      <div className="pm-quota-grid">
        <div className="pm-quota-card">
          <div className="pm-quota-card-header">
            <span>WhatsApp Numbers</span>
            <strong>{tenant.numbers_count || 0} / {tenant.max_numbers}</strong>
          </div>
          <div className="pm-quota-bar">
            <div
              className={`pm-quota-bar-fill ${numbersPercent >= 100 ? 'danger' : numbersPercent >= 80 ? 'warning' : ''}`}
              style={{ width: `${numbersPercent}%` }}
            />
          </div>
          <span className="pm-quota-footer">{numbersPercent}% allocated</span>
        </div>

        <div className="pm-quota-card">
          <div className="pm-quota-card-header">
            <span>Team Members</span>
            <strong>{tenant.users_count || 0} / {tenant.max_users}</strong>
          </div>
          <div className="pm-quota-bar">
            <div
              className={`pm-quota-bar-fill ${usersPercent >= 100 ? 'danger' : usersPercent >= 80 ? 'warning' : ''}`}
              style={{ width: `${usersPercent}%` }}
            />
          </div>
          <span className="pm-quota-footer">{usersPercent}% seat limit</span>
        </div>

        <div className="pm-quota-card">
          <div className="pm-quota-card-header">
            <span>Monthly Campaigns</span>
            <strong>{tenant.campaigns_count || 0} / {tenant.max_campaigns_monthly}</strong>
          </div>
          <div className="pm-quota-bar">
            <div
              className={`pm-quota-bar-fill ${campaignsPercent >= 100 ? 'danger' : campaignsPercent >= 80 ? 'warning' : ''}`}
              style={{ width: `${campaignsPercent}%` }}
            />
          </div>
          <span className="pm-quota-footer">{campaignsPercent}% of quota</span>
        </div>
      </div>

      <div className="pm-plan-features">
        <h4>{tenant.tier_display} Features Included</h4>
        {tenant.tier === 'small' && (
          <ul>
            <li>1 WhatsApp Business Phone Number</li>
            <li>Up to 3 Team Member Seats</li>
            <li>5 Marketing Campaigns per Month</li>
            <li>Department-based Automated Message Routing</li>
            <li>Standard Meta Cloud API Integration</li>
          </ul>
        )}
        {tenant.tier === 'mid' && (
          <ul>
            <li>Up to 5 WhatsApp Business Phone Numbers</li>
            <li>Up to 15 Team Member Seats</li>
            <li>50 Marketing Campaigns per Month</li>
            <li>Advanced Keyword & Working-Hours Automations</li>
            <li>Rich Analytics & CSV / PDF Export Reports</li>
          </ul>
        )}
        {tenant.tier === 'large' && (
          <ul>
            <li>Up to 25 WhatsApp Business Phone Numbers</li>
            <li>Up to 100 Team Member Seats</li>
            <li>500 Marketing Campaigns per Month</li>
            <li>Priority Automated SLA Routing & Webhooks</li>
            <li>Dedicated Enterprise Support & Data Isolation</li>
          </ul>
        )}
      </div>
    </div>
  )
}

/* ==========================================================
   PLATFORM CREATE TENANT FORM
   ========================================================== */
function PlatformCreateTenantForm({ submit, busy, close }) {
  const [form, setForm] = useState({
    name: '',
    tier: 'mid',
  })

  function handleSubmit(e) {
    e.preventDefault()
    submit(form)
  }

  return (
    <form className="pm-form" onSubmit={handleSubmit}>
      <label>
        Company / Organization Name
        <input
          required
          placeholder="e.g. Nexus Logistics"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
      </label>
      <label>
        Plan Tier
        <select
          value={form.tier}
          onChange={(e) => setForm({ ...form, tier: e.target.value })}
        >
          <option value="small">Basic (Small) - 1 number, 3 users, 5 campaigns, 5 GB storage</option>
          <option value="mid">Standard (Mid) - 5 numbers, 15 users, 50 campaigns, 10 GB storage</option>
          <option value="large">Premium (Large) - 25 numbers, 100 users, 500 campaigns, 15 GB storage</option>
        </select>
      </label>
      <footer style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 14 }}>
        <button type="button" className="pm-secondary-btn" onClick={close} disabled={busy}>
          Cancel
        </button>
        <button type="submit" className="pm-primary-btn" disabled={busy}>
          {busy ? 'Provisioning...' : 'Provision Tenant'}
        </button>
      </footer>
    </form>
  )
}

/* ==========================================================
   ACCEPT INVITE SCREEN
   ========================================================== */
function AcceptInvite({ token }) {
  const [form, setForm] = useState({ first_name: '', last_name: '', password: '' })
  const [state, setState] = useState({ busy: false, message: '' })

  async function accept(event) {
    event.preventDefault()
    setState({ busy: true, message: '' })
    try {
      const response = await fetch(`${API}/auth/invitations/accept/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, token }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Unable to activate account')
      setState({ busy: false, message: data.message })
      setTimeout(() => {
        window.location.href = window.location.origin
      }, 1500)
    } catch (error) {
      setState({ busy: false, message: error.message })
    }
  }

  return (
    <main className="pm-selector-screen">
      <div className="pm-selector-body" style={{ maxWidth: 480 }}>
        <form className="pm-panel-card" style={{ padding: 32 }} onSubmit={accept}>
          <span className="pm-nav-label" style={{ padding: 0 }}>
            IAM INVITATION
          </span>
          <h2 style={{ color: '#fff', margin: '8px 0 6px' }}>Activate your account</h2>
          <p style={{ color: '#848a9e', fontSize: 12, marginBottom: 20 }}>
            Complete your profile to access your team workspace.
          </p>
          {state.message && (
            <div
              style={{
                padding: 10,
                background: 'rgba(37,211,102,0.1)',
                border: '1px solid #25d366',
                borderRadius: 6,
                color: '#25d366',
                fontSize: 11,
                marginBottom: 16,
              }}
            >
              {state.message}
            </div>
          )}
          <div className="pm-form">
            <label>
              First name
              <input
                required
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              />
            </label>
            <label>
              Last name
              <input
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
              />
            </label>
            <label className="full">
              Password
              <input
                required
                minLength="8"
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </label>
            <footer className="full">
              <button className="pm-primary-btn" disabled={state.busy}>
                {state.busy ? 'Activating…' : 'Activate account'}
              </button>
            </footer>
          </div>
        </form>
      </div>
    </main>
  )
}

/* ==========================================================
   MODAL COMPONENT
   ========================================================== */
function Modal({ title, close, children }) {
  return (
    <div className="pm-modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && close()}>
      <div className="pm-modal">
        <header className="pm-modal-header">
          <h3>{title}</h3>
          <button type="button" onClick={close} aria-label="Close modal">
            ×
          </button>
        </header>
        <div className="pm-modal-body">{children}</div>
      </div>
    </div>
  )
}

/* ==========================================================
   FORMS & DETAILS
   ========================================================== */
function CampaignForm({ data, setData, submit, busy }) {
  const f = (k) => ({ value: data[k], onChange: (e) => setData({ ...data, [k]: e.target.value }) })
  return (
    <form className="pm-form" onSubmit={submit}>
      <label className="full">
        Campaign name
        <input required {...f('name')} placeholder="e.g. New Feature Announcement" />
      </label>
      <label className="full">
        Message template
        <textarea required rows={4} {...f('message')} placeholder="Type your WhatsApp message..." />
      </label>
      <label>
        Target audience
        <input required {...f('target_audience')} placeholder="e.g. All active leads" />
      </label>
      <label>
        Initial status
        <select {...f('status')}>
          <option value="draft">Draft</option>
          <option value="scheduled">Scheduled</option>
          <option value="running">Running</option>
        </select>
      </label>
      <label className="full">
        Schedule send date & time
        <input type="datetime-local" {...f('scheduled_at')} />
      </label>
      <footer className="full">
        <button className="pm-primary-btn" disabled={busy}>
          Create campaign
        </button>
      </footer>
    </form>
  )
}

function MemberForm({ data, setData, submit, busy, owner }) {
  const f = (k) => ({ value: data[k], onChange: (e) => setData({ ...data, [k]: e.target.value }) })
  return (
    <form className="pm-form" onSubmit={submit}>
      <label className="full">
        Business email
        <input required type="email" {...f('email')} placeholder="teammate@company.com" />
      </label>
      <label>
        Platform role
        <select {...f('role')}>
          <option value="viewer">Viewer · read-only</option>
          <option value="editor">Editor · read and write</option>
          <option value="admin">Administrator · manage platform</option>
          {owner && <option value="owner">Owner · full control</option>}
        </select>
      </label>
      <label>
        WhatsApp number access
        <select {...f('number_access')}>
          <option value="india">India number only</option>
          <option value="us">US number only</option>
          <option value="both">India and US numbers</option>
        </select>
      </label>
      <div
        className="full"
        style={{
          fontSize: 10,
          color: '#848a9e',
          background: '#10131d',
          padding: 10,
          borderRadius: 6,
          border: '1px solid var(--pm-border)',
        }}
      >
        An invitation link will be sent to this email address for account setup.
      </div>
      <footer className="full">
        <button className="pm-primary-btn" disabled={busy}>
          {busy ? 'Sending…' : 'Send invitation'}
        </button>
      </footer>
    </form>
  )
}

function ExportForm({ data, setData, submit, busy }) {
  const today = new Date().toISOString().slice(0, 10)
  return (
    <form className="pm-form" onSubmit={submit}>
      <label className="full">
        Date range
        <select value={data.range} onChange={(e) => setData({ ...data, range: e.target.value })}>
          <option value="week">Last 7 days</option>
          <option value="month">Last 30 days</option>
          <option value="three_months">Last 90 days</option>
          <option value="custom">Custom date range</option>
        </select>
      </label>
      {data.range === 'custom' && (
        <>
          <label>
            Start date
            <input
              required
              type="date"
              max={data.end_date || today}
              value={data.start_date}
              onChange={(e) => setData({ ...data, start_date: e.target.value })}
            />
          </label>
          <label>
            End date
            <input
              required
              type="date"
              min={data.start_date}
              max={today}
              value={data.end_date}
              onChange={(e) => setData({ ...data, end_date: e.target.value })}
            />
          </label>
        </>
      )}
      <div
        className="full"
        style={{
          fontSize: 10,
          color: '#848a9e',
          background: '#10131d',
          padding: 10,
          borderRadius: 6,
          border: '1px solid var(--pm-border)',
        }}
      >
        The exported CSV includes reference ID, customer contact info, department, enquiry message,
        and timestamps.
      </div>
      <footer className="full">
        <button className="pm-primary-btn" disabled={busy}>
          {busy ? 'Exporting…' : 'Download CSV'}
        </button>
      </footer>
    </form>
  )
}

function EnquiryDetails({ enquiry }) {
  const notifications = enquiry.notifications || []
  return (
    <div>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          paddingBottom: 16,
          borderBottom: '1px solid var(--pm-border)',
          marginBottom: 16,
        }}
      >
        <span
          className="pm-avatar"
          style={{ background: getAvatarColor(enquiry.customer_name) }}
        >
          {(enquiry.customer_name?.[0] || 'C').toUpperCase()}
        </span>
        <div>
          <h3 style={{ margin: 0, color: '#fff', fontSize: 16 }}>
            {enquiry.customer_name || 'Customer'}
          </h3>
          <p style={{ margin: 0, color: '#848a9e', fontSize: 11 }}>
            {enquiry.organization_name || 'Individual'} · {enquiry.phone_number}
          </p>
        </div>
        <span
          className={`pm-status-badge ${enquiry.status}`}
          style={{ marginLeft: 'auto' }}
        >
          {enquiry.status}
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 16 }}>
        <div>
          <small style={{ color: '#71778c', display: 'block', fontSize: 10 }}>Phone</small>
          <strong style={{ color: '#fff', fontSize: 12 }}>{enquiry.phone_number || '—'}</strong>
        </div>
        <div>
          <small style={{ color: '#71778c', display: 'block', fontSize: 10 }}>Email</small>
          <strong style={{ color: '#fff', fontSize: 12 }}>{enquiry.customer_email || '—'}</strong>
        </div>
        <div>
          <small style={{ color: '#71778c', display: 'block', fontSize: 10 }}>Routing team</small>
          <strong style={{ color: '#aaa4ff', fontSize: 12 }}>{enquiry.team_name || 'Support'}</strong>
        </div>
        <div>
          <small style={{ color: '#71778c', display: 'block', fontSize: 10 }}>Reference</small>
          <code style={{ color: '#aaa4ff', fontSize: 12 }}>{enquiry.reference}</code>
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <small style={{ color: '#71778c', display: 'block', fontSize: 10, marginBottom: 4 }}>
          Customer message
        </small>
        <div
          style={{
            padding: 12,
            background: '#10131d',
            border: '1px solid var(--pm-border)',
            borderRadius: 8,
            fontSize: 12,
            lineHeight: 1.6,
            color: '#e2e4ef',
          }}
        >
          {enquiry.message}
        </div>
      </div>

      <div>
        <small style={{ color: '#71778c', display: 'block', fontSize: 10, marginBottom: 8 }}>
          Notifications ({notifications.length})
        </small>
        {notifications.length ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {notifications.map((n, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 10px',
                  background: '#10131d',
                  borderRadius: 6,
                  fontSize: 11,
                }}
              >
                <span>{n.recipient_name || 'Recipient'}</span>
                <span className={`pm-status-badge ${n.status}`}>{n.status}</span>
              </div>
            ))}
          </div>
        ) : (
          <span style={{ fontSize: 11, color: '#686e82' }}>No notifications generated</span>
        )}
      </div>
    </div>
  )
}

function MessageAttachment({ message, token, businessId }) {
  const [url, setUrl] = useState('')

  useEffect(() => {
    if (!message.attachment_url) return
    let live = true,
      objectUrl = ''
    let workspaceId = businessId
    try {
      workspaceId = workspaceId || JSON.parse(sessionStorage.getItem('crm_business_number'))?.id
    } catch {
      /* Session parse catch */
    }
    fetch(`${API}${message.attachment_url}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'X-Business-Number-ID': String(workspaceId),
      },
    })
      .then((response) => {
        if (!response.ok) throw new Error()
        return response.blob()
      })
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob)
        if (live) setUrl(objectUrl)
      })
      .catch(() => {})
    return () => {
      live = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [message.attachment_url, token, businessId])

  if (!message.attachment_url) return null
  if (!url) return <div style={{ fontSize: 10, color: '#aaa4ff' }}>Loading attachment…</div>

  const type = message.attachment_content_type || ''
  return (
    <div style={{ marginBottom: 6 }}>
      {type.startsWith('image/') && (
        <img
          src={url}
          alt={message.attachment_name}
          style={{ maxWidth: 220, maxHeight: 180, borderRadius: 8, display: 'block' }}
        />
      )}
      {type.startsWith('video/') && (
        <video src={url} controls style={{ maxWidth: 240, borderRadius: 8, display: 'block' }} />
      )}
      {type.startsWith('audio/') && <audio src={url} controls style={{ display: 'block' }} />}
      <a
        href={url}
        download={message.attachment_name}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 5,
          color: '#aaa4ff',
          fontSize: 10,
          marginTop: 4,
        }}
      >
        <Paperclip size={11} />
        {message.attachment_name || 'Download file'}
      </a>
    </div>
  )
}

export default App
