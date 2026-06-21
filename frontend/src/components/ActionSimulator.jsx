import { useEffect, useState, useMemo } from 'react'
import { getActions, simulateActions, getLevers, monteCarlo, getOptimize } from '../api/client'
import InfoTip from './InfoTip'

const SCENARIOS = [
  { id: 'pessimistic', label: 'Cautious', hint: '30% of benefit realised' },
  { id: 'expected', label: 'Expected', hint: '60% realised' },
  { id: 'optimistic', label: 'Best case', hint: '100% realised' },
]
const BAND_LETTER = { 35: 'D', 50: 'C', 65: 'B', 80: 'A' }

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
  const [levers, setLevers] = useState([])
  const [picks, setPicks] = useState({})
  const [scenario, setScenario] = useState('expected')
  const [result, setResult] = useState(null)
  const [mc, setMc] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [optimal, setOptimal] = useState(null)

  useEffect(() => {
    let on = true
    Promise.all([getActions(analysisId), getLevers(analysisId, 'expected')])
      .then(([a, l]) => { if (on) { setActions(a.actions || []); setLevers(l.levers || []) } })
      .catch(e => { if (on) setError(e.message) })
    return () => { on = false }
  }, [analysisId])

  // Recommended bundle (Build 5 optimiser): best <=3 actions for Imara lift.
  useEffect(() => {
    let on = true
    getOptimize(analysisId, scenario, 3, 'imara')
      .then(o => { if (on) setOptimal(o) }).catch(() => { if (on) setOptimal(null) })
    return () => { on = false }
  }, [analysisId, scenario])

  const selected = useMemo(
    () => Object.entries(picks).filter(([, v]) => v > 0).map(([id, intensity]) => ({ id, intensity })),
    [picks]
  )

  useEffect(() => {
    if (!actions.length) return
    setLoading(true); setError(null)
    const a = simulateActions(analysisId, selected, scenario).then(setResult)
    const b = selected.length
      ? monteCarlo(analysisId, selected).then(setMc)
      : Promise.resolve(setMc(null))
    Promise.all([a, b]).catch(e => setError(e.message)).finally(() => setLoading(false))
  }, [analysisId, selected, scenario, actions.length])

  const toggle = (id) => setPicks(p => ({ ...p, [id]: p[id] ? 0 : 1 }))
  const setIntensity = (id, v) => setPicks(p => ({ ...p, [id]: v }))
  const applyBundle = (ids) => setPicks(Object.fromEntries((ids || []).map(id => [id, 1])))

  const b = result?.baseline, pj = result?.projected
  const scoreUp = result ? (pj.imara_score ?? 0) - (b.imara_score ?? 0) : 0
  const nextBand = mc?.next_band_threshold ? BAND_LETTER[mc.next_band_threshold] : null

  return (
    <div>
      <p className="text-slate-400 text-sm mb-4 flex items-center gap-1.5">
        Pick the actions you could take and see the projected effect — and how likely it is.
        <InfoTip label="Action Simulator" text="A deterministic projection from your own figures. Each action adjusts a driver (margin, overheads, collections, growth); we recompute the statements, ratios and Imara Score. Incremental profit is taxed; the Likelihood is a 1,000-run Monte Carlo where a shared execution-conditions factor correlates how fully the actions land together (so the downside isn't understated). It models execution variance, not external shocks. Indicative estimates, not guarantees." />
      </p>

      {/* Biggest levers (tornado / sensitivity) */}
      {levers.length > 0 && (
        <div className="mb-4 bg-navy-card border border-white/[0.08] rounded-xl p-3">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-2">Biggest levers — most Imara Score gain on their own</div>
          <div className="flex flex-wrap gap-2">
            {levers.filter(l => l.score_impact > 0 || l.profit_impact > 0).slice(0, 4).map(l => (
              <button key={l.id} type="button" onClick={() => setPicks(p => ({ ...p, [l.id]: p[l.id] ? 0 : 1 }))}
                className={`text-left text-xs px-3 py-1.5 rounded-lg border transition-colors ${picks[l.id] ? 'border-gold/40 bg-gold/10 text-gold' : 'border-white/10 text-slate-300 hover:border-white/20'}`}>
                <span className="font-medium">{l.label}</span>
                <span className="ml-2 text-emerald-400 font-semibold">{l.score_impact > 0 ? `+${l.score_impact} score` : money(l.profit_impact, currency)}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {optimal?.best_bundle && optimal.best_bundle.imara_score_delta > 0 && (
        <div className="mb-4 bg-emerald-500/[0.05] border border-emerald-500/20 rounded-xl p-3">
          <div className="text-[11px] uppercase tracking-wider text-emerald-300/80 mb-2 flex items-center gap-1.5">
            Recommended first moves
            <InfoTip label="Recommended bundle" text="The best combination of up to 3 actions for Imara Score lift, found by evaluating every bundle jointly because actions interact. Ties prefer fewer actions (less effort for the same gain)." />
          </div>
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="text-sm text-white">
              {optimal.best_bundle.labels.join(' + ')}
              <span className="ml-2 text-emerald-400 font-semibold">+{optimal.best_bundle.imara_score_delta} score</span>
            </div>
            <button type="button" onClick={() => applyBundle(optimal.best_bundle.ids)}
              className="text-xs px-3 py-1.5 rounded-lg border border-emerald-400/40 bg-emerald-400/10 text-emerald-300 hover:bg-emerald-400/20 transition-colors font-medium">
              Apply these
            </button>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2 mb-4">
        {SCENARIOS.map(s => (
          <button key={s.id} type="button" onClick={() => setScenario(s.id)} aria-pressed={scenario === s.id} title={s.hint}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${scenario === s.id ? 'border-gold/50 bg-gold/10 text-gold' : 'border-white/10 text-slate-400 hover:border-white/20 hover:text-white'}`}>
            {s.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="space-y-2">
          {error && <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-red-400 text-xs">{error}</div>}
          {!actions.length && !error && <div className="text-slate-600 text-sm">No actions available for this analysis.</div>}
          {actions.map(a => {
            const on = (picks[a.id] || 0) > 0
            return (
              <div key={a.id} className={`rounded-xl border p-3 transition-colors ${on ? 'border-gold/30 bg-gold/[0.04]' : 'border-white/[0.08] bg-navy-card'}`}>
                <label className="flex items-start gap-3 cursor-pointer">
                  <input type="checkbox" checked={on} onChange={() => toggle(a.id)} className="mt-0.5 accent-[#C9A84C] w-4 h-4" aria-label={a.label} />
                  <span className="flex-1 min-w-0">
                    <span className="text-white text-sm font-medium">{a.label}</span>
                    <span className="block text-slate-500 text-xs mt-0.5">{a.rationale}</span>
                  </span>
                </label>
                {on && (
                  <div className="mt-2 pl-7 flex items-center gap-2">
                    <input type="range" min="0.25" max="1" step="0.25" value={picks[a.id]} onChange={e => setIntensity(a.id, parseFloat(e.target.value))} className="flex-1 accent-[#C9A84C]" aria-label={`${a.label} intensity`} />
                    <span className="text-[11px] text-slate-400 w-28 text-right">{Math.round((a.default ?? a.max) * (picks[a.id] || 1) * 10) / 10}{a.unit} of {a.max}{a.unit}</span>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5">
          {result ? (
            <>
              <div className="flex items-end justify-between mb-3">
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

              {/* Likelihood (Monte Carlo) */}
              {mc && nextBand && (
                <div className="mb-3 bg-gold/[0.05] border border-gold/20 rounded-xl p-3">
                  <div className="text-sm text-white">
                    <span className="font-bold text-gold">≈{Math.round(mc.prob_reach_next_band * 100)}%</span> chance of reaching <span className="font-bold">Band {nextBand}</span>
                    <InfoTip label="Likelihood" text={`Across ${mc.iterations} simulations that vary how fully each action lands plus market noise. Score range p10–p90: ${mc.imara_score.p10}–${mc.imara_score.p90}.`} />
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">
                    Likely Imara Score {mc.imara_score.p10}–{mc.imara_score.p90} · net profit gain {money(mc.net_profit_delta.p10, currency)} to {money(mc.net_profit_delta.p90, currency)}
                  </div>
                </div>
              )}

              <MetricRow label="Net profit (after tax)" from={b.net_profit} to={pj.net_profit} fmt={v => money(v, currency)} />
              <MetricRow label="Operating profit" from={b.operating_profit} to={pj.operating_profit} fmt={v => money(v, currency)} />
              <MetricRow label="Revenue" from={b.revenue} to={pj.revenue} fmt={v => money(v, currency)} />
              <MetricRow label="Gross margin" from={b.gross_margin} to={pj.gross_margin} fmt={pct} />
              <MetricRow label="Net margin" from={b.net_margin} to={pj.net_margin} fmt={pct} />
              <MetricRow label="Debtor days" from={b.debtor_days} to={pj.debtor_days} fmt={v => `${Math.round(v)}d`} goodUp={false} />
              <MetricRow label="Fundamentals score" from={b.fundamentals_score} to={pj.fundamentals_score} fmt={v => `${Math.round(v)}`} />
              <p className="text-slate-600 text-[11px] mt-3 leading-relaxed italic">{result.disclaimer}</p>
              {result.assumptions && (
                <details className="mt-2">
                  <summary className="text-slate-500 text-[11px] cursor-pointer hover:text-slate-300">Model assumptions</summary>
                  <div className="text-slate-500 text-[11px] mt-1 leading-relaxed">
                    Realisation {result.assumptions.realisation_by_scenario?.expected} (expected) · price–volume elasticity {result.assumptions.price_volume_elasticity} · company tax {Math.round((result.assumptions.company_tax_rate || 0) * 100)}%. {result.assumptions.default_target}.
                    {mc?.assumptions?.monte_carlo && <> {' '}Monte&nbsp;Carlo: {mc.assumptions.monte_carlo.execution_factor}; it models {mc.assumptions.monte_carlo.models}.</>}
                  </div>
                </details>
              )}
            </>
          ) : (
            <div className="text-slate-500 text-sm text-center py-12">{loading ? 'Modelling…' : 'Select one or more actions to see the projected outcome.'}</div>
          )}
        </div>
      </div>
    </div>
  )
}
