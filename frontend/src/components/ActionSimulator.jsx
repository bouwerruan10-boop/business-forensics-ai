import { useEffect, useState, useMemo } from 'react'
import { getActions, simulateActions } from '../api/client'
import InfoTip from './InfoTip'

const SCENARIOS = [
  { id: 'pessimistic', label: 'Cautious', hint: '30% of benefit realised' },
  { id: 'expected', label: 'Expected', hint: '60% realised' },
  { id: 'optimistic', label: 'Best case', hint: '100% realised' },
]

function money(n, cur) {
  if (n == null) return '—'
  const s = n < 0 ? '-' : ''
  const a = Math.abs(n)
  if (a >= 1_000_000) return `${s}${cur} ${(a / 1_000_000).toFixed(2)}M`
  if (a >= 1_000) return `${s}${cur} ${(a / 1_000).toFixed(0)}K`
  return `${s}${cur} ${a.toFixed(0)}`
}
const pct = v => (v == null ? '—' : `${v.toFixed(1)}%`)

function Delta({ from, to, fmt, goodUp = true }) {
  if (from == null || to == null) return null
  const d = to - from
  const better = goodUp ? d > 0 : d < 0
  const cls = d === 0 ? 'text-slate-500' : better ? 'text-emerald-400' : 'text-red-400'
  return <span className={`text-xs font-semibold ${cls}`}>{d > 0 ? '▲' : d < 0 ? '▼' : ''} {fmt(Math.abs(d))}</span>
}

function MetricRow({ label, from, to, fmt, goodUp = true }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-white/[0.05] last:border-0">
      <span className="text-slate-400 text-xs">{label}</span>
      <div className="flex items-center gap-3">
        <span className="text-slate-500 text-xs tabular-nums">{fmt(from)}</span>
        <span className="text-slate-600" aria-hidden="true">→</span>
        <span className="text-white text-sm font-semibold tabular-nums">{fmt(to)}</span>
        <span className="w-16 text-right"><Delta from={from} to={to} fmt={fmt} goodUp={goodUp} /></span>
      </div>
    </div>
  )
}

export default function ActionSimulator({ analysisId, currency = 'ZAR' }) {
  const [actions, setActions] = useState([])
  const [picks, setPicks] = useState({})       // id -> intensity (0..1)
  const [scenario, setScenario] = useState('expected')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    let on = true
    getActions(analysisId)
      .then(d => { if (on) setActions(d.actions || []) })
      .catch(e => { if (on) setError(e.message) })
    return () => { on = false }
  }, [analysisId])

  const selected = useMemo(
    () => Object.entries(picks).filter(([, v]) => v > 0).map(([id, intensity]) => ({ id, intensity })),
    [picks]
  )

  useEffect(() => {
    if (!actions.length) return
    setLoading(true); setError(null)
    simulateActions(analysisId, selected, scenario)
      .then(setResult).catch(e => setError(e.message)).finally(() => setLoading(false))
  }, [analysisId, selected, scenario, actions.length])

  const toggle = (id) => setPicks(p => ({ ...p, [id]: p[id] ? 0 : 1 }))
  const setIntensity = (id, v) => setPicks(p => ({ ...p, [id]: v }))

  const b = result?.baseline, pj = result?.projected
  const scoreUp = result ? (pj.imara_score ?? 0) - (b.imara_score ?? 0) : 0

  return (
    <div>
      <p className="text-slate-400 text-sm mb-4 flex items-center gap-1.5">
        Pick the actions you could take and see the projected effect on your numbers and Imara Score.
        <InfoTip label="Action Simulator" text="A deterministic projection from your own figures: each action adjusts a driver (margin, overheads, collections, growth) and we recompute the statements, ratios and Imara Score. Outcomes are indicative estimates, scaled by how fully you expect to deliver them." />
      </p>

      {/* Scenario selector */}
      <div className="flex flex-wrap gap-2 mb-4">
        {SCENARIOS.map(s => (
          <button key={s.id} type="button" onClick={() => setScenario(s.id)}
            aria-pressed={scenario === s.id} title={s.hint}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
              scenario === s.id ? 'border-gold/50 bg-gold/10 text-gold' : 'border-white/10 text-slate-400 hover:border-white/20 hover:text-white'}`}>
            {s.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Actions */}
        <div className="space-y-2">
          {error && <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-red-400 text-xs">{error}</div>}
          {!actions.length && !error && <div className="text-slate-600 text-sm">No actions available for this analysis.</div>}
          {actions.map(a => {
            const on = (picks[a.id] || 0) > 0
            return (
              <div key={a.id} className={`rounded-xl border p-3 transition-colors ${on ? 'border-gold/30 bg-gold/[0.04]' : 'border-white/[0.08] bg-navy-card'}`}>
                <label className="flex items-start gap-3 cursor-pointer">
                  <input type="checkbox" checked={on} onChange={() => toggle(a.id)}
                    className="mt-0.5 accent-[#C9A84C] w-4 h-4" aria-label={a.label} />
                  <span className="flex-1 min-w-0">
                    <span className="text-white text-sm font-medium">{a.label}</span>
                    <span className="block text-slate-500 text-xs mt-0.5">{a.rationale}</span>
                  </span>
                </label>
                {on && (
                  <div className="mt-2 pl-7 flex items-center gap-2">
                    <input type="range" min="0.25" max="1" step="0.25" value={picks[a.id]}
                      onChange={e => setIntensity(a.id, parseFloat(e.target.value))}
                      className="flex-1 accent-[#C9A84C]" aria-label={`${a.label} intensity`} />
                    <span className="text-[11px] text-slate-400 w-28 text-right">
                      {Math.round((a.default ?? a.max) * (picks[a.id] || 1) * 10) / 10}{a.unit} of {a.max}{a.unit}
                    </span>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Outcome */}
        <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5">
          {result ? (
            <>
              <div className="flex items-end justify-between mb-4">
                <div>
                  <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Projected Imara Score</div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-slate-500 text-lg line-through">{b.imara_score}</span>
                    <span className="text-3xl font-bold text-gold">{pj.imara_score}</span>
                    {scoreUp !== 0 && <span className={`text-sm font-semibold ${scoreUp > 0 ? 'text-emerald-400' : 'text-red-400'}`}>{scoreUp > 0 ? '+' : ''}{scoreUp}</span>}
                  </div>
                </div>
                {result.cash_released > 0 && (
                  <div className="text-right">
                    <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Cash freed up</div>
                    <div className="text-xl font-bold text-emerald-400">{money(result.cash_released, currency)}</div>
                  </div>
                )}
              </div>
              <MetricRow label="Net profit" from={b.net_profit} to={pj.net_profit} fmt={v => money(v, currency)} />
              <MetricRow label="Operating profit" from={b.operating_profit} to={pj.operating_profit} fmt={v => money(v, currency)} />
              <MetricRow label="Revenue" from={b.revenue} to={pj.revenue} fmt={v => money(v, currency)} />
              <MetricRow label="Gross margin" from={b.gross_margin} to={pj.gross_margin} fmt={pct} />
              <MetricRow label="Net margin" from={b.net_margin} to={pj.net_margin} fmt={pct} />
              <MetricRow label="Debtor days" from={b.debtor_days} to={pj.debtor_days} fmt={v => `${Math.round(v)}d`} goodUp={false} />
              <MetricRow label="Fundamentals score" from={b.fundamentals_score} to={pj.fundamentals_score} fmt={v => `${Math.round(v)}`} />
              <p className="text-slate-600 text-[11px] mt-3 leading-relaxed italic">{result.disclaimer}</p>
            </>
          ) : (
            <div className="text-slate-500 text-sm text-center py-12">{loading ? 'Modelling…' : 'Select one or more actions to see the projected outcome.'}</div>
          )}
        </div>
      </div>
    </div>
  )
}
