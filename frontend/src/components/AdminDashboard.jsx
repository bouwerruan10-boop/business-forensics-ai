import { useEffect, useState } from 'react'
import { getToken } from '../api/client'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const KEY_STORE = 'imara_admin_key'

function fmt(n, cur = '') {
  if (!n) return '—'
  if (n >= 1_000_000) return `${cur} ${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${cur} ${(n / 1_000).toFixed(0)}K`
  return `${cur} ${n}`
}

function statusBadge(status) {
  const map = {
    complete: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    processing: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    error: 'bg-red-500/10 text-red-400 border-red-500/20',
  }
  return (
    <span className={`text-xs border rounded-full px-2 py-0.5 font-medium ${map[status] || 'bg-white/5 text-slate-400 border-white/10'}`}>
      {status}
    </span>
  )
}

function Metric({ label, value, tone = 'slate' }) {
  const t = { slate: 'text-slate-200', emerald: 'text-emerald-400', amber: 'text-amber-400', red: 'text-red-400' }[tone] || 'text-slate-200'
  return (
    <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3">
      <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1">{label}</div>
      <div className={`text-sm font-bold ${t}`}>{value}</div>
    </div>
  )
}

function FleetPanel({ fleet }) {
  if (!fleet || !fleet.overall || !fleet.overall.runs) return null
  const o = fleet.overall
  const alerts = fleet.drift_alerts || []
  const healthy = fleet.healthy
  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 mb-6">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h3 className="text-white font-bold text-base">Fleet Quality <span className="text-slate-500 font-normal text-sm">· online quality monitor ({o.runs} runs)</span></h3>
        <span className={`text-xs font-bold border rounded-full px-3 py-1 ${healthy ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25' : 'bg-amber-500/10 text-amber-300 border-amber-500/30'}`}>
          {healthy ? '✓ Stable' : `⚠ ${alerts.length} drift alert${alerts.length > 1 ? 's' : ''}`}
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-3">
        <Metric label="Avg Imara Score" value={o.avg_imara_score ?? '—'} />
        <Metric label="Strong findings" value={o.avg_strong_pct != null ? `${o.avg_strong_pct}%` : '—'} tone={o.avg_strong_pct >= 60 ? 'emerald' : 'amber'} />
        <Metric label="Conflict rate" value={`${o.conflict_rate_pct ?? 0}%`} tone={(o.conflict_rate_pct || 0) > 20 ? 'red' : (o.conflict_rate_pct || 0) > 0 ? 'amber' : 'emerald'} />
        <Metric label="AI-extracted" value={`${o.ai_extraction_rate_pct ?? 0}%`} tone={(o.ai_extraction_rate_pct || 0) > 40 ? 'amber' : 'slate'} />
        <Metric label="Avg cost / run" value={o.avg_cost_usd != null ? `$${o.avg_cost_usd}` : '—'} />
        <Metric label="Avg runtime" value={o.avg_runtime_s != null ? `${Math.round(o.avg_runtime_s / 60)}m` : '—'} />
      </div>
      {alerts.length > 0 && (
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-3">
          <div className="text-amber-300 text-xs font-medium mb-1">Drift vs baseline (recent {fleet.window} runs)</div>
          <ul className="text-slate-300 text-xs space-y-0.5 list-disc list-inside">
            {alerts.map((a, i) => <li key={i}>{a.label}: <span className="text-white font-semibold">{a.recent}</span> vs baseline {a.baseline} ({a.delta > 0 ? '+' : ''}{a.delta})</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}

function ScoreValidationPanel({ headers, analyses }) {
  const [val, setVal] = useState(null)
  const [cal, setCal] = useState(null)
  const [outcomes, setOutcomes] = useState([])
  const [form, setForm] = useState({ analysis_id: '', outcome_type: 'funded', label: '', value: '', note: '', source: '' })
  const [msg, setMsg] = useState(null)
  const [busy, setBusy] = useState(false)

  const reload = async () => {
    try {
      const [v, c, o] = await Promise.all([
        fetch(`${API_BASE}/api/admin/validation`, { headers: headers() }).then(r => r.ok ? r.json() : null),
        fetch(`${API_BASE}/api/admin/calibration`, { headers: headers() }).then(r => r.ok ? r.json() : null),
        fetch(`${API_BASE}/api/admin/outcomes?limit=100`, { headers: headers() }).then(r => r.ok ? r.json() : null),
      ])
      setVal(v); setCal(c); setOutcomes((o && o.outcomes) || [])
    } catch { /* best-effort */ }
  }
  useEffect(() => { reload() }, [])

  const submit = async (e) => {
    e.preventDefault()
    if (!form.analysis_id) { setMsg('Pick an analysis first.'); return }
    setBusy(true); setMsg(null)
    try {
      const body = { analysis_id: form.analysis_id, outcome_type: form.outcome_type, note: form.note, source: form.source }
      if (form.label !== '') body.label = Number(form.label)
      if (form.value !== '') body.value = Number(form.value)
      const r = await fetch(`${API_BASE}/api/admin/outcomes`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...headers() }, body: JSON.stringify(body),
      })
      if (!r.ok) throw new Error(((await r.json().catch(() => ({}))).detail) || 'Record failed')
      setMsg('Recorded ✓'); setForm({ ...form, label: '', value: '', note: '', source: '' })
      reload()
    } catch (err) { setMsg(err.message) } finally { setBusy(false) }
  }

  const real = (val && val.real_outcomes) || {}
  const proxy = (val && val.zscore_proxy) || {}
  const calm = (cal && cal.calibration) || null

  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 mb-6">
      <h3 className="text-white font-bold text-base mb-1">Score validation <span className="text-slate-500 font-normal text-sm">· calibration evidence ({outcomes.length} outcomes recorded)</span></h3>
      <p className="text-slate-400 text-xs mb-3">Record real funding / repayment outcomes to calibrate the Imara Score. Discrimination on REAL outcomes is the goal; the Z&#39;&#39; proxy is interim convergent-validity evidence until the pilot accrues data.</p>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
        {real.available ? (
          <>
            <Metric label="Real-outcome AUC" value={real.auc ?? '—'} tone={real.auc >= 0.7 ? 'emerald' : 'amber'} />
            <Metric label="Gini" value={real.gini ?? '—'} />
            <Metric label="KS" value={real.ks ?? '—'} />
            <Metric label="Labelled n" value={`${real.n} (${real.n_bad} bad)`} />
          </>
        ) : (
          <div className="col-span-2 sm:col-span-4 text-amber-300 text-xs bg-amber-500/5 border border-amber-500/20 rounded-xl p-3">{real.reason || 'Not enough labelled outcomes yet — record some below.'}</div>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <Metric label="Z'' proxy AUC" value={proxy.auc ?? '—'} tone={proxy.auc >= 0.7 ? 'emerald' : 'slate'} />
        <Metric label="Proxy n" value={proxy.n ?? proxy.analyses_with_zscore ?? '—'} />
        <Metric label="PD calibration" value={calm ? `slope ${calm.calibration_slope}` : (cal && cal.calibrated === false ? 'need ≥ 50' : '—')} />
        <Metric label="Outcomes recorded" value={outcomes.length} />
      </div>

      <form onSubmit={submit} className="grid sm:grid-cols-7 gap-2 items-end bg-white/[0.02] border border-white/[0.06] rounded-xl p-3">
        <label className="text-[11px] text-slate-400 sm:col-span-2">Analysis
          <select value={form.analysis_id} onChange={e => setForm({ ...form, analysis_id: e.target.value })} className="mt-1 w-full bg-navy border border-white/10 rounded-lg px-2 py-1.5 text-sm text-white">
            <option value="">Select…</option>
            {analyses.filter(a => a.status === 'complete').map(a => <option key={a.id} value={a.id}>{a.company_name || a.id.slice(0, 8)}</option>)}
          </select>
        </label>
        <label className="text-[11px] text-slate-400">Outcome
          <select value={form.outcome_type} onChange={e => setForm({ ...form, outcome_type: e.target.value })} className="mt-1 w-full bg-navy border border-white/10 rounded-lg px-2 py-1.5 text-sm text-white">
            {['funded', 'declined', 'repaid', 'default', 'external_score'].map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        <label className="text-[11px] text-slate-400">Label
          <select value={form.label} onChange={e => setForm({ ...form, label: e.target.value })} className="mt-1 w-full bg-navy border border-white/10 rounded-lg px-2 py-1.5 text-sm text-white">
            <option value="">—</option><option value="0">0 good</option><option value="1">1 bad/default</option>
          </select>
        </label>
        <label className="text-[11px] text-slate-400">Value
          <input type="number" value={form.value} onChange={e => setForm({ ...form, value: e.target.value })} placeholder="bureau score" className="mt-1 w-full bg-navy border border-white/10 rounded-lg px-2 py-1.5 text-sm text-white" />
        </label>
        <label className="text-[11px] text-slate-400">Source
          <input type="text" value={form.source} onChange={e => setForm({ ...form, source: e.target.value })} placeholder="e.g. bank" className="mt-1 w-full bg-navy border border-white/10 rounded-lg px-2 py-1.5 text-sm text-white" />
        </label>
        <button type="submit" disabled={busy} className="bg-gold text-navy font-bold text-sm px-3 py-1.5 rounded-lg hover:bg-amber-400 disabled:opacity-50 transition-colors">{busy ? '…' : 'Record'}</button>
      </form>
      {msg && <div className="text-xs text-slate-300 mt-2">{msg}</div>}
    </div>
  )
}

export default function AdminDashboard({ onViewReport }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [needsKey, setNeedsKey] = useState(false)
  const [keyInput, setKeyInput] = useState('')
  const [fleet, setFleet] = useState(null)

  const adminHeaders = () => {
    const h = {}
    const k = sessionStorage.getItem(KEY_STORE)
    if (k) h['X-Admin-Key'] = k
    const t = getToken()              // operator bearer token (admin is behind the operator gate)
    if (t) h['Authorization'] = 'Bearer ' + t
    return h
  }

  const load = async () => {
    setLoading(true); setError(null)
    try {
      const headers = adminHeaders()
      const res = await fetch(`${API_BASE}/api/admin/analyses?limit=50`, { headers })
      if (res.status === 401) {
        setNeedsKey(true)
        sessionStorage.removeItem(KEY_STORE)
        throw new Error('This admin area is protected. Enter the admin key to continue.')
      }
      if (!res.ok) throw new Error('Could not load analysis history')
      const d = await res.json()
      setNeedsKey(false)
      setData(d)
      try {
        const fres = await fetch(`${API_BASE}/api/admin/fleet-quality?limit=50`, { headers })
        if (fres.ok) setFleet(await fres.json())
      } catch { /* fleet panel is best-effort */ }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const unlock = (e) => {
    e.preventDefault()
    if (!keyInput.trim()) return
    sessionStorage.setItem(KEY_STORE, keyInput.trim())
    setKeyInput('')
    load()
  }

  const totals = data?.totals || {}
  const analyses = data?.analyses || []

  if (needsKey) {
    return (
      <div className="max-w-sm mx-auto mt-16 bg-navy-card border border-white/[0.08] rounded-2xl p-6">
        <h2 className="text-white font-bold text-lg mb-1">Admin access</h2>
        <p className="text-slate-400 text-sm mb-4">This area lists all stored analyses. Enter the admin key to continue.</p>
        <form onSubmit={unlock} className="flex flex-col gap-3">
          <label htmlFor="admin-key" className="sr-only">Admin key</label>
          <input
            id="admin-key" type="password" autoFocus
            value={keyInput} onChange={e => setKeyInput(e.target.value)}
            placeholder="Admin key"
            className="w-full bg-[#0f1117] border border-white/10 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-gold/40"
          />
          {error && <p className="text-red-400 text-xs">{error}</p>}
          <button type="submit"
            className="bg-gold text-navy font-bold text-sm px-4 py-2 rounded-lg hover:bg-amber-400 transition-colors">
            Unlock
          </button>
        </form>
      </div>
    )
  }

  return (
    <div>
      <FleetPanel fleet={fleet} />
      {!needsKey && <ScoreValidationPanel headers={adminHeaders} analyses={analyses} />}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-white font-bold text-lg">Analysis History</h2>
          <p className="text-slate-400 text-sm">All past analyses stored in local database</p>
        </div>
        <button type="button" onClick={load}
          className="text-xs border border-white/10 text-slate-300 hover:text-white hover:border-white/20 px-3 py-1.5 rounded-lg transition-colors">
          ↻ Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {[
          { label: 'Total', value: totals.total ?? '—' },
          { label: 'Complete', value: totals.complete ?? '—', color: 'text-emerald-400' },
          { label: 'Processing', value: totals.processing ?? '—', color: 'text-amber-400' },
          { label: 'Errors', value: totals.error ?? '—', color: 'text-red-400' },
        ].map(t => (
          <div key={t.label} className="bg-navy-card border border-white/[0.08] rounded-xl p-4 text-center">
            <div className={`text-2xl font-bold ${t.color || 'text-white'}`}>{t.value}</div>
            <div className="text-slate-400 text-xs mt-0.5">{t.label}</div>
          </div>
        ))}
      </div>

      {loading && (
        <div className="text-center py-12">
          <div className="flex justify-center gap-1 mb-2">
            <span className="pulse-dot w-2 h-2 rounded-full bg-gold inline-block" />
            <span className="pulse-dot pulse-dot-2 w-2 h-2 rounded-full bg-gold inline-block" />
            <span className="pulse-dot pulse-dot-3 w-2 h-2 rounded-full bg-gold inline-block" />
          </div>
          <p className="text-slate-400 text-sm">Loading...</p>
        </div>
      )}

      {error && !needsKey && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">{error}</div>
      )}

      {!loading && !error && analyses.length === 0 && (
        <div className="text-center py-12 text-slate-500">
          No analyses yet — run your first analysis to see it here.
        </div>
      )}

      {analyses.length > 0 && (
        <div className="bg-navy-card border border-white/[0.08] rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="text-left text-xs text-slate-400 font-medium px-5 py-3">Company</th>
                  <th className="text-left text-xs text-slate-400 font-medium px-5 py-3 hidden sm:table-cell">Industry</th>
                  <th className="text-left text-xs text-slate-400 font-medium px-5 py-3 hidden md:table-cell">Revenue</th>
                  <th className="text-left text-xs text-slate-400 font-medium px-5 py-3">Status</th>
                  <th className="text-left text-xs text-slate-400 font-medium px-5 py-3 hidden lg:table-cell">Date</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {analyses.map(a => (
                  <tr key={a.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-5 py-3">
                      <div className="text-white font-medium">{a.company_name || '—'}</div>
                      <div className="text-slate-500 text-xs">{a.id.slice(0, 8)}...</div>
                    </td>
                    <td className="px-5 py-3 text-slate-300 hidden sm:table-cell">{a.industry_key}</td>
                    <td className="px-5 py-3 text-slate-300 hidden md:table-cell">{fmt(a.annual_revenue, a.currency)}</td>
                    <td className="px-5 py-3">{statusBadge(a.status)}</td>
                    <td className="px-5 py-3 text-slate-500 text-xs hidden lg:table-cell">
                      {new Date(a.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-5 py-3 text-right">
                      {a.status === 'complete' && (
                        <button type="button" onClick={() => onViewReport(a.id)}
                          className="text-xs text-gold hover:text-gold-light transition-colors font-medium">
                          View →
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
