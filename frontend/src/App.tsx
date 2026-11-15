import { useEffect, useState } from 'react'
import {
  Award, Bell, BriefcaseBusiness,
  ChartNoAxesCombined, Check, ChevronDown, ChevronRight, FileCheck2,
  Gauge, Gift, GraduationCap, Handshake, LayoutDashboard, MapPinned, Menu,
  Moon, Package, Search, Settings, ShieldCheck, Sparkles, Sun, Users, Wrench, X, LogOut,
  type LucideIcon
} from 'lucide-react'
import type { Role } from './data'
import AuthScreen from './AuthScreen'
import Analytics from './Analytics'
import WorkspaceModules from './WorkspaceModules'
import { apiRequest, clearSession, readSession, type AuthSession } from './api'

type NavItem = { label: string; icon: LucideIcon; group: string }
const navItems: NavItem[] = [
  { label: 'Overview', icon: LayoutDashboard, group: 'WORKSPACE' },
  { label: 'Mechanic network', icon: Users, group: 'WORKSPACE' },
  { label: 'Mechanic Passport', icon: Award, group: 'WORKSPACE' },
  { label: 'Advocacy intelligence', icon: Handshake, group: 'ENGAGEMENT' },
  { label: 'Product catalogue', icon: Package, group: 'ENGAGEMENT' },
  { label: 'Smart Tool Bank', icon: Wrench, group: 'ENGAGEMENT' },
  { label: 'Rewards & recognition', icon: Gift, group: 'ENGAGEMENT' },
  { label: 'Training academy', icon: GraduationCap, group: 'GROWTH' },
  { label: 'Territory intelligence', icon: MapPinned, group: 'GROWTH' },
  { label: 'TrustVision review', icon: ShieldCheck, group: 'GOVERNANCE' },
  { label: 'AI Copilot', icon: Sparkles, group: 'GOVERNANCE' },
  { label: 'Reports & ROI', icon: ChartNoAxesCombined, group: 'GOVERNANCE' },
  { label: 'Privacy & data', icon: ShieldCheck, group: 'GOVERNANCE' },
]
const roleNav: Record<Role, string[]> = {
  Mechanic: ['Overview', 'Mechanic Passport', 'Advocacy intelligence', 'Product catalogue', 'Smart Tool Bank', 'Rewards & recognition', 'Training academy', 'TrustVision review', 'AI Copilot', 'Privacy & data'],
  'Field Representative': ['Overview', 'Mechanic network', 'Advocacy intelligence', 'Territory intelligence', 'Training academy', 'Privacy & data'],
  Dealer: ['Overview', 'Mechanic network', 'Product catalogue', 'Smart Tool Bank', 'Advocacy intelligence', 'Privacy & data'],
  Administrator: navItems.map(n => n.label),
}

function App() {
  const [session, setSession] = useState(() => readSession())
  const [active, setActive] = useState('Overview')
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('All statuses')
  const [dark, setDark] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [toast, setToast] = useState('')
  const [showNotifications, setShowNotifications] = useState(false)
  useEffect(() => {
    const expired = () => setSession(null)
    window.addEventListener('pitstop:session-expired', expired)
    return () => window.removeEventListener('pitstop:session-expired', expired)
  }, [])
  function authenticated(next: AuthSession) {
    setSession({ token: next.access_token, user: next.user })
    setActive('Overview')
  }
  function signOut() {
    clearSession()
    setSession(null)
    setActive('Overview')
  }
  const roles = session?.user.roles || []
  const role: Role = roles.some(r => ['administrator', 'eurogrip_admin'].includes(r))
    ? 'Administrator'
    : (roles.includes('field_representative') || roles.includes('field_rep')) ? 'Field Representative'
    : roles.includes('dealer') ? 'Dealer' : 'Mechanic'
  const visibleNav = navItems.filter(item => roleNav[role].includes(item.label))
  function notify(message: string) {
    setToast(message)
    window.setTimeout(() => setToast(''), 2600)
  }
  function navigate(label: string) { setActive(label); setMobileOpen(false) }

  if (!session) return <AuthScreen onAuthenticated={authenticated} />

  return (
    <div className={dark ? 'app dark' : 'app'}>
      <aside className={`sidebar ${mobileOpen ? 'open' : ''}`}>
        <div className="brand">
          <div className="brand-mark"><span>e</span></div>
          <div><div className="brand-name">EUROGRIP</div><div className="brand-sub">PITSTOP OS <span>2.0</span></div></div>
          <button className="icon-button close-menu" onClick={() => setMobileOpen(false)} aria-label="Close menu"><X size={18}/></button>
        </div>
        <div className="workspace-switch"><div className="workspace-icon"><Gauge size={17}/></div><div className="workspace-copy"><strong>National workspace</strong><small>India operations</small></div><ChevronDown size={15}/></div>
        <nav className="navigation">
          {['WORKSPACE','ENGAGEMENT','GROWTH','GOVERNANCE'].map(group => (
            <div className="nav-group" key={group}>
              <div className="nav-heading">{group}</div>
              {visibleNav.filter(n => n.group === group).map(item => {
                const Icon = item.icon
                return <button key={item.label} className={`nav-link ${active === item.label ? 'selected' : ''}`} onClick={() => navigate(item.label)}>
                  <Icon size={17}/><span>{item.label}</span>
                </button>
              })}
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          
          <div className="profile-mini"><div className="avatar">AD</div><div className="profile-copy"><strong>{session.user.display_name}</strong><small>{session.user.roles.join(", ")}</small></div><button className="icon-button" onClick={() => notify('Profile and privacy settings are available through the account APIs.')} aria-label="Profile settings"><Settings size={17}/></button></div>
        </div>
      </aside>

      {mobileOpen && <button className="scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
      <main className="main">
        <header className="topbar">
          <div className="top-left"><button className="icon-button mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open menu"><Menu size={20}/></button><div className="crumb">Platform <ChevronRight size={14}/> <strong>{active}</strong></div></div>
          <div className="top-actions">
            <div className="role-picker"><span>Signed in as</span><strong>{session.user.display_name}</strong><small>{session.user.roles.join(', ')}</small></div>
            <button className="icon-button theme-toggle" onClick={() => setDark(!dark)} aria-label="Toggle theme">{dark ? <Sun size={18}/> : <Moon size={18}/>}</button>
            <div className="notification-wrap"><button className="icon-button notification-button" onClick={() => setShowNotifications(!showNotifications)} aria-label="Notifications"><Bell size={18}/></button>
              {showNotifications && <div className="notification-pop"><strong>Notifications</strong><p>Notifications are not configured for this workspace yet.</p><button onClick={() => { setShowNotifications(false); navigate('TrustVision review') }}>Review pending items</button></div>}
            </div>
            <button className="icon-button" onClick={signOut} aria-label="Sign out" title="Sign out"><LogOut size={17}/></button>
            <div className="top-avatar">{session.user.display_name.split(' ').map(x => x[0]).join('').slice(0,2).toUpperCase()}</div>
          </div>
        </header>

        <div className="content">
          <div className="page-intro">
            <div><div className="eyebrow"><span className="live-dot"/> NATIONAL OPERATIONS </div>
              <h1>{active === 'Overview' ? role === 'Mechanic' ? 'Your Pitstop' : 'Operations overview' : active}</h1>
              <p>{pageDescription(active, role)}</p></div>
            <div className="intro-actions">{role === 'Administrator' && <button className="button secondary" onClick={() => navigate('Reports & ROI')}><FileCheck2 size={16}/> View reports</button>}</div>
          </div>

          {active === 'Overview' ? (role === 'Administrator' ? <Analytics/> : <WorkspaceModules title='My Dashboard' role={role} notify={notify}/>) :
            active === 'Mechanic network' ? <Network role={role} query={query} setQuery={setQuery} status={statusFilter} setStatus={setStatusFilter}/> :
            active === 'Reports & ROI' ? <Analytics/> :
            ['Mechanic Passport','Smart Tool Bank','Rewards & recognition','Advocacy intelligence','Product catalogue','Training academy','Territory intelligence','TrustVision review','AI Copilot'].includes(active)
              ? <WorkspaceModules title={active} role={role} notify={notify}/> :
            <ModulePlaceholder title={active} onAction={() => notify(`${active} module is not available for this account role.`)}/>}
          <footer className="footer"><span>EUROGRIP PITSTOP OS <b>•</b> Platform preview</span><span>Authenticated workspace · API-backed modules</span></footer>
        </div>
      </main>
      {toast && <div className="toast"><Check size={16}/>{toast}</div>}
    </div>
  )
}

function pageDescription(active: string, role: Role) {
  if (active === 'Reports & ROI') return 'Verified operational metrics and exportable management reports from the live backend.'
  if (active === 'Overview') return role === 'Mechanic' ? 'Your professional journey, rewards and learning activity in one place.' : 'Your authenticated workspace, with records loaded from the platform APIs.'
  const descriptions: Record<string,string> = {
    'Mechanic network':'Discover, support and manage the professional mechanic community.',
    'Smart Tool Bank':'Make high-value workshop equipment more accessible to eligible mechanics.',
    'Advocacy intelligence':'Understand recommendations, verified fitments and stocking as distinct outcomes.',
    'Territory intelligence':'Manage consent-aware location records and search for opted-in nearby locations.',
    'Training academy':'Build practical skills through product knowledge and safety learning.',
    'TrustVision review':'Submit evidence and review human-verified integrity cases.',
  }
  return descriptions[active] || 'A dedicated workspace for the EUROGRIP mechanic advocacy ecosystem.'
}
function Network({role,query,setQuery,status,setStatus}:{role:Role;query:string;setQuery:(s:string)=>void;status:string;setStatus:(s:string)=>void}) {
  const [rows,setRows] = useState<any[]>([])
  const [loading,setLoading] = useState(false)
  const [error,setError] = useState('')
  async function load() {
    setLoading(true);setError('')
    try {
      const params=new URLSearchParams({limit:'50',offset:'0'})
      if(query.trim())params.set('q',query.trim())
      if(status!=='All statuses')params.set('verification_status',status.toLowerCase().replace(' ','_'))
      const result=await apiRequest<{data:any[];meta:any}>(`/admin/mechanics?${params}`)
      setRows(result.data)
    } catch(e){setError(e instanceof Error?e.message:'Could not load mechanic directory.')}
    finally{setLoading(false)}
  }
  useEffect(()=>{void load()},[query,status])
  async function verify(id:string,approved:boolean) {
    try {await apiRequest(`/admin/onboarding/mechanics/${id}/verification`,{method:'PATCH',body:JSON.stringify({approved})});await load()}
    catch(e){setError(e instanceof Error?e.message:'Review failed.')}
  }
  return <section className="panel table-panel"><div className="panel-head"><div><h2>Mechanic directory</h2><p>Live mechanic records from the authenticated platform API</p></div><span className="table-count">{rows.length} loaded</span></div>
    <div className="table-tools"><div className="search-box"><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search name, shop, code or city..."/></div><select className="small-select" value={status} onChange={e=>setStatus(e.target.value)}><option>All statuses</option><option>Pending</option><option>Verified</option><option>Rejected</option><option>Unverified</option></select><button className="button secondary compact" onClick={()=>void load()} disabled={loading}>Refresh</button></div>
    {error&&<div className="analytics-error">{error}</div>}
    <div className="table-scroll"><table><thead><tr><th>MECHANIC</th><th>LOCATION</th><th>SHOP</th><th>EXPERIENCE</th><th>PARTICIPATION</th><th>VERIFICATION</th><th>REVIEW</th></tr></thead><tbody>{rows.map(m=><tr key={m.mechanic_id}><td><div className="person-cell"><div className="person-avatar">{m.display_name.split(' ').map((n:string)=>n[0]).join('').slice(0,2)}</div><div><b>{m.display_name}</b><small>{m.mechanic_code}</small></div></div></td><td>{[m.city,m.state].filter(Boolean).join(', ')||'—'}</td><td>{m.shop_name||'—'}</td><td>{m.experience_years} yrs</td><td>{m.participation_type}</td><td><Status value={m.verification_status}/></td><td>{role==='Administrator'&&m.verification_status==='pending'?<div className="module-inline-actions"><button className="button primary compact" onClick={()=>void verify(m.mechanic_id,true)}>Verify</button><button className="button secondary compact" onClick={()=>void verify(m.mechanic_id,false)}>Reject</button></div>:<span className="muted">—</span>}</td></tr>)}</tbody></table>{!rows.length&&!loading&&<div className="empty-state">No mechanic records found.</div>}{loading&&<div className="empty-state">Loading mechanic records…</div>}</div>
  </section>
}
function Status({value}:{value:string}) { const cls=value.toLowerCase().includes('active')?'good':value.toLowerCase().includes('approved')?'good':value.toLowerCase().includes('pending')||value.toLowerCase().includes('review')?'pending':'muted'; return <span className={`status ${cls}`}><i/>{value}</span> }
function ModulePlaceholder({title,onAction}:{title:string;onAction:()=>void}) {
  const icons:Record<string,LucideIcon>={'Mechanic Passport':Award,'Product catalogue':Package,'Rewards & recognition':Gift,'AI Copilot':Sparkles,'Reports & ROI':ChartNoAxesCombined}
  const Icon=icons[title]||BriefcaseBusiness
  return <section className="panel placeholder-panel"><div className="placeholder-icon"><Icon size={28}/></div><span className="eyebrow">MODULE WORKSPACE</span><h2>{title}</h2><p>This workspace is not available to the role assigned to your account. Contact a platform administrator if you believe you need access.</p><div className="placeholder-points"><span><Check size={15}/> Navigation and responsive shell available</span><span><Check size={15}/> Live module access is role controlled</span><span><ShieldCheck size={15}/> Access is controlled by your assigned platform role</span></div><button className="button primary" onClick={onAction}>View implementation status <ChevronRight size={15}/></button></section>
}

export default App
