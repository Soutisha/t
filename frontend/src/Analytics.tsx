import { useEffect, useState } from 'react'
import { Download, RefreshCw, TrendingUp, Users, Wrench, GraduationCap, ShieldAlert, CheckCircle2 } from 'lucide-react'
import { apiRequest, downloadCsv } from './api'

type Executive = {
  data: {
    active_users: number; mechanics_registered: number; mechanics_verified: number
    verified_recommendations: number; verified_fitments: number; verified_units_sold: number
    tool_requests: number; course_completions: number; fraud_cases_pending_review: number
    period: { start: string | null; end_exclusive: string | null }
  }
  roi: { status: string; reason: string; roi_percentage: number | null }
}
type Funnel = {
  data: {
    verified_recommendations: number; verified_fitments: number
    verified_fitments_linked_to_recommendation: number; verified_sales_records: number
    verified_sales_linked_to_recommendation: number; verified_units_sold: number; note: string
  }
}
type Operations = {
  data: {
    tool_bank: { active_products: number; requests_by_status: Record<string, number> }
    rewards: { points_by_entry_type: Record<string, number>; redemptions: number }
    training: { enrollments: number; completions: number; certificates_issued: number; quiz_attempts: number; average_quiz_score: number; passed_attempts: number }
    trustvision: { evidence_submissions: number; fraud_cases_by_status: Record<string, number> }
  }
}
const fmt = (n: number) => Number(n || 0).toLocaleString('en-IN')

export default function Analytics() {
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [executive, setExecutive] = useState<Executive | null>(null)
  const [funnel, setFunnel] = useState<Funnel | null>(null)
  const [operations, setOperations] = useState<Operations | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [exporting, setExporting] = useState(false)

  function params() {
    const query = new URLSearchParams()
    if (start) query.set('start', new Date(`${start}T00:00:00`).toISOString())
    if (end) {
      const exclusive = new Date(`${end}T00:00:00`)
      exclusive.setDate(exclusive.getDate() + 1)
      query.set('end', exclusive.toISOString())
    }
    return query.toString() ? `?${query.toString()}` : ''
  }
  async function load() {
    setLoading(true); setError('')
    try {
      const q = params()
      const [e, f, o] = await Promise.all([
        apiRequest<Executive>(`/admin/analytics/executive${q}`),
        apiRequest<Funnel>(`/admin/analytics/advocacy-funnel${q}`),
        apiRequest<Operations>(`/admin/analytics/operations${q}`),
      ])
      setExecutive(e); setFunnel(f); setOperations(o)
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to load analytics.') }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [])
  async function exportReport() {
    setExporting(true); setError('')
    try { await downloadCsv(`/admin/analytics/report.csv${params()}`, 'eurogrip-analytics.csv') }
    catch (e) { setError(e instanceof Error ? e.message : 'CSV export failed.') }
    finally { setExporting(false) }
  }

  const d = executive?.data
  const o = operations?.data
  const f = funnel?.data
  const metrics = [
    ['Active user accounts', d?.active_users, Users, 'Account status is active'],
    ['Registered mechanics', d?.mechanics_registered, Wrench, `${fmt(d?.mechanics_verified || 0)} verified`],
    ['Verified recommendations', d?.verified_recommendations, TrendingUp, 'Verified records only'],
    ['Verified fitments', d?.verified_fitments, CheckCircle2, 'Separate from recommendations'],
    ['Verified sales units', d?.verified_units_sold, TrendingUp, 'Units, not revenue'],
    ['Tool requests', d?.tool_requests, Wrench, 'Requests in selected period'],
    ['Course completions', d?.course_completions, GraduationCap, 'Completed enrolments'],
    ['Fraud cases pending', d?.fraud_cases_pending_review, ShieldAlert, 'Awaiting human review'],
  ] as const

  return <div className="analytics-page">
    <section className="panel analytics-controls">
      <div><h2>Live platform analytics</h2><p>Figures are queried from the authenticated Pitstop OS backend.</p></div>
      <div className="analytics-filters">
        <label>From <input type="date" value={start} onChange={e => setStart(e.target.value)}/></label>
        <label>To <input type="date" value={end} onChange={e => setEnd(e.target.value)}/></label>
        <button className="button secondary compact" onClick={() => void load()} disabled={loading}><RefreshCw size={14}/> Apply</button>
        <button className="button primary compact" onClick={exportReport} disabled={exporting}><Download size={14}/> CSV</button>
      </div>
    </section>
    {error && <div className="analytics-error">{error}</div>}
    {loading ? <section className="panel analytics-loading">Loading verified platform metrics…</section> : d && o && f ? <>
      <div className="analytics-metrics">{metrics.map(([label,value,Icon,note])=><article className="metric-card" key={label}><div className="metric-top"><span>{label}</span><div className="metric-icon"><Icon size={17}/></div></div><div className="metric-value">{fmt(value || 0)}</div><div className="metric-foot">{note}</div></article>)}</div>
      <div className="dashboard-grid">
        <section className="panel"><div className="panel-head"><div><h2>Advocacy outcome records</h2><p>Verified stage totals, not a cohort conversion rate</p></div></div>
          <div className="analytics-bars">
            {[['Recommendations',f.verified_recommendations],['Fitments',f.verified_fitments],['Sales records',f.verified_sales_records],['Sales units',f.verified_units_sold]].map(([label,value])=><div className="analytics-bar-row" key={label}><span>{label}</span><div><i style={{width:`${Math.min(100,Number(value)/(Math.max(1,f.verified_recommendations,f.verified_fitments,f.verified_units_sold))*100)}%`}}/></div><b>{fmt(Number(value))}</b></div>)}
          </div>
          <p className="analytics-note">{f.note}</p>
        </section>
        <section className="panel"><div className="panel-head"><div><h2>Training performance</h2><p>Recorded enrolments and assessments</p></div></div>
          <div className="analytics-stat-list">
            <div><span>Enrolments</span><b>{fmt(o.training.enrollments)}</b></div>
            <div><span>Completions</span><b>{fmt(o.training.completions)}</b></div>
            <div><span>Certificates issued</span><b>{fmt(o.training.certificates_issued)}</b></div>
            <div><span>Quiz attempts</span><b>{fmt(o.training.quiz_attempts)}</b></div>
            <div><span>Average quiz score</span><b>{o.training.average_quiz_score.toFixed(1)}%</b></div>
          </div>
        </section>
      </div>
      <div className="dashboard-grid">
        <section className="panel"><div className="panel-head"><div><h2>Tool Bank and rewards</h2><p>Operational records in selected period</p></div></div>
          <div className="analytics-stat-list"><div><span>Active catalogue products</span><b>{fmt(o.tool_bank.active_products)}</b></div>{(Object.entries(o.tool_bank.requests_by_status) as [string, number][]).map(([k,v])=><div key={k}><span>Requests · {k}</span><b>{fmt(v)}</b></div>)}<div><span>Reward redemptions</span><b>{fmt(o.rewards.redemptions)}</b></div>{(Object.entries(o.rewards.points_by_entry_type) as [string, number][]).map(([k,v])=><div key={k}><span>Points · {k}</span><b>{fmt(v)}</b></div>)}</div>
        </section>
        <section className="panel"><div className="panel-head"><div><h2>TrustVision operations</h2><p>Evidence and review workload</p></div></div>
          <div className="analytics-stat-list"><div><span>Evidence submissions</span><b>{fmt(o.trustvision.evidence_submissions)}</b></div>{(Object.entries(o.trustvision.fraud_cases_by_status) as [string, number][]).map(([k,v])=><div key={k}><span>Cases · {k}</span><b>{fmt(v)}</b></div>)}</div>
        </section>
      </div>
      <section className="panel roi-panel"><div><h2>Programme ROI</h2><p>ROI is not calculated until finance-approved costs and monetary benefits are configured.</p></div><span className="status pending">Not configured</span><small>{executive?.roi.reason}</small></section>
    </> : <section className="panel analytics-loading">No analytics response is available.</section>}
  </div>
}
