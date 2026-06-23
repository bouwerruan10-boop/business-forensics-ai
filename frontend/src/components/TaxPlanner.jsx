import { useState } from 'react'
import { getTaxRelocation } from '../api/client'

// Income types + destination corridors mirror the backend engine exactly
// (services/relocation_tax.py: INCOME_TYPES + DESTINATIONS).
const INCOME_TYPES = [
  ['employment', 'Salary / employment'],
  ['business', 'Business / active income'],
  ['dividends', 'Dividends'],
  ['interest', 'Interest'],
  ['rental', 'Rental'],
  ['capital_gains', 'Capital gains'],
  ['pension', 'Pension / annuity'],
]
const DESTS = [
  ['AE', 'United Arab Emirates'], ['CY', 'Cyprus (non-dom)'], ['PT', 'Portugal (IFICI)'],
  ['MU', 'Mauritius'], ['MT', 'Malta (non-dom)'], ['GR', 'Greece (flat / 7%)'],
  ['IT', 'Italy (flat / 7%)'], ['CH', 'Switzerland (forfait)'],
]
const FIT = {
  strong: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10',
  possible: 'text-gold border-gold/30 bg-gold/10',
  weak: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
  unknown: 'text-slate-400 border-white/10 bg-white/5',
}
const rand = (n) => 'R ' + Math.round(Number(n) || 0).toLocaleString('en-ZA')

function Chip({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`text-xs rounded-lg px-3 py-1.5 border transition-colors ${
        active ? 'border-gold/50 text-gold bg-gold/10' : 'border-white/10 text-slate-400 hover:border-white/25 hover:text-white'
      }`}
    >
      {children}
    </button>
  )
}

export default function TaxPlanner() {
  const [types, setTypes] = useState(() => new Set())
  const [amounts, setAmounts] = useState({})
  const [dests, setDests] = useState(() => new Set())
  const [assets, setAssets] = useState({ worldwide_market_value: '', base_cost: '' })
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const toggle = (set, setter, k) => {
    const n = new Set(set)
    n.has(k) ? n.delete(k) : n.add(k)
    setter(n)
  }

  const run = async () => {
    setError(null); setLoading(true); setData(null)
    const payload = { origin: 'ZA' }
    if (types.size) payload.income_types = [...types]
    const inc = {}
    for (const t of types) {
      const v = parseFloat(amounts[t])
      if (!isNaN(v) && v > 0) inc[t] = v
    }
    if (Object.keys(inc).length) payload.income = inc
    if (dests.size) payload.destinations = [...dests]
    const wmv = parseFloat(assets.worldwide_market_value)
    const bc = parseFloat(assets.base_cost)
    if (!isNaN(wmv) && wmv > 0) payload.assets = { worldwide_market_value: wmv, base_cost: isNaN(bc) ? 0 : bc }
    try {
      setData(await getTaxRelocation(payload))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl font-bold text-white">Tax Me If You Can</h1>
        <p className="text-sm text-slate-400 mt-1">
          A factual first pass on SA tax-residency relocation corridors and legal stay-and-optimise levers.
          Decision-support, not advice.
        </p>
      </header>

      {/* ── Inputs ─────────────────────────────────────────── */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-5">
        <div>
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wide mb-2">Income types</div>
          <div className="flex flex-wrap gap-2">
            {INCOME_TYPES.map(([k, label]) => (
              <Chip key={k} active={types.has(k)} onClick={() => toggle(types, setTypes, k)}>{label}</Chip>
            ))}
          </div>
        </div>

        {types.size > 0 && (
          <div>
            <div className="text-xs font-semibold text-slate-300 uppercase tracking-wide mb-2">
              Annual amounts (optional — ZAR, enables quantified saving)
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {[...types].map((t) => (
                <label key={t} className="text-xs text-slate-400">
                  {INCOME_TYPES.find(([k]) => k === t)?.[1] || t}
                  <input
                    type="number" min="0" inputMode="numeric"
                    value={amounts[t] || ''}
                    onChange={(e) => setAmounts({ ...amounts, [t]: e.target.value })}
                    className="mt-1 w-full rounded-lg bg-navy border border-white/10 px-2.5 py-1.5 text-sm text-white focus:border-gold/40 outline-none"
                    placeholder="e.g. 1000000"
                  />
                </label>
              ))}
            </div>
          </div>
        )}

        <div>
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wide mb-2">
            Destinations <span className="text-slate-500 normal-case">(none = all corridors)</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {DESTS.map(([k, label]) => (
              <Chip key={k} active={dests.has(k)} onClick={() => toggle(dests, setDests, k)}>{label}</Chip>
            ))}
          </div>
        </div>

        <div>
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wide mb-2">
            Worldwide assets (optional — estimates SA exit CGT, s9H)
          </div>
          <div className="grid grid-cols-2 gap-3 max-w-md">
            <label className="text-xs text-slate-400">
              Market value
              <input type="number" min="0" value={assets.worldwide_market_value}
                onChange={(e) => setAssets({ ...assets, worldwide_market_value: e.target.value })}
                className="mt-1 w-full rounded-lg bg-navy border border-white/10 px-2.5 py-1.5 text-sm text-white focus:border-gold/40 outline-none"
                placeholder="ZAR" />
            </label>
            <label className="text-xs text-slate-400">
              Base cost
              <input type="number" min="0" value={assets.base_cost}
                onChange={(e) => setAssets({ ...assets, base_cost: e.target.value })}
                className="mt-1 w-full rounded-lg bg-navy border border-white/10 px-2.5 py-1.5 text-sm text-white focus:border-gold/40 outline-none"
                placeholder="ZAR" />
            </label>
          </div>
        </div>

        <button type="button" onClick={run} disabled={loading}
          className="rounded-lg px-4 py-2 text-sm font-semibold bg-gold text-navy hover:bg-gold/90 disabled:opacity-50 transition-colors">
          {loading ? 'Working…' : 'Run tax planner'}
        </button>
        {error && <div className="text-sm text-rose-400">Could not run: {error}</div>}
      </div>

      {/* ── Results ────────────────────────────────────────── */}
      {data && data.available && (
        <div className="space-y-6">
          <div className="text-xs text-slate-500">
            As of {data.as_of} · {data.classification}
            {data.quantified && data.indicative_current_sa_tax != null && (
              <span> · Indicative current SA tax: <span className="text-slate-300">{rand(data.indicative_current_sa_tax)}/yr</span></span>
            )}
          </div>

          {data.origin_exit && data.origin_exit.indicative_exit_cgt != null && (
            <div className="rounded-xl border border-amber-500/25 bg-amber-500/[0.06] p-3.5 text-sm">
              <span className="text-amber-300 font-semibold">SA exit charge (s9H): </span>
              <span className="text-slate-300">indicative CGT ≈ {rand(data.origin_exit.indicative_exit_cgt)} on ceasing tax residency.</span>
            </div>
          )}

          {/* Destination cards */}
          <div className="grid gap-3 md:grid-cols-2">
            {data.destinations.map((d) => (
              <div key={d.code} className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 space-y-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-sm font-semibold text-white">{d.name}</div>
                    <div className="text-[11px] text-slate-500 uppercase tracking-wide">{d.regime === 'flat_fee' ? 'Flat-fee regime' : 'Rate-based'}</div>
                  </div>
                  {d.fit && (
                    <span className={`text-[10px] rounded-full px-2 py-0.5 border ${FIT[d.fit.level] || FIT.unknown}`}>
                      {d.fit.level}
                    </span>
                  )}
                </div>
                {d.headline && <div className="text-xs text-slate-300">{d.headline}</div>}
                {d.flat_fee && (
                  <div className="text-xs text-gold">Fixed fee: {d.flat_fee.local} ({rand(d.flat_fee.amount_zar)}/yr)</div>
                )}
                {d.quantified !== undefined && d.indicative_annual_saving != null && (
                  <div className="text-xs text-emerald-400">
                    Indicative saving ≈ {rand(d.indicative_annual_saving)}/yr
                    {d.saving_pct != null && <span className="text-slate-500"> ({d.saving_pct}%)</span>}
                  </div>
                )}
                {d.fit && d.fit.reason && <div className="text-[11px] text-slate-500">{d.fit.reason}</div>}
                {d.residency_test && <div className="text-[11px] text-slate-500"><span className="text-slate-400">Residency:</span> {d.residency_test}</div>}
                {d.substance && <div className="text-[11px] text-slate-500"><span className="text-slate-400">Substance:</span> {d.substance}</div>}
                {Array.isArray(d.gotchas) && d.gotchas.length > 0 && (
                  <ul className="text-[11px] text-amber-300/80 list-disc ml-4 space-y-0.5">
                    {d.gotchas.map((g, i) => <li key={i}>{g}</li>)}
                  </ul>
                )}
                {Array.isArray(d.sources) && d.sources.length > 0 && (
                  <div className="text-[10px] text-slate-600">Sources: {d.sources.join('; ')}</div>
                )}
              </div>
            ))}
          </div>

          {/* Stay & optimise */}
          {Array.isArray(data.stay_and_optimise) && data.stay_and_optimise.length > 0 && (
            <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.04] p-5 space-y-3">
              <div className="text-sm font-semibold text-emerald-300">Stay &amp; optimise — legal SA tax-efficiency levers</div>
              <div className="grid gap-2.5 sm:grid-cols-2">
                {data.stay_and_optimise.map((lv, i) => (
                  <div key={i} className="rounded-xl border border-white/10 p-3">
                    <div className="text-xs font-semibold text-white">{lv.lever} <span className="text-slate-500">({lv.section})</span></div>
                    <div className="text-[11px] text-slate-400 mt-1">{lv.what}</div>
                    {lv.indicative && <div className="text-[11px] text-emerald-400/80 mt-1">{lv.indicative}</div>}
                  </div>
                ))}
              </div>
              {data.stay_and_optimise_note && <div className="text-[11px] text-slate-500">{data.stay_and_optimise_note}</div>}
            </div>
          )}

          {/* Sequencing */}
          {Array.isArray(data.sequencing) && data.sequencing.length > 0 && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
              <div className="text-sm font-semibold text-white mb-2">Compliant sequencing</div>
              <ol className="text-xs text-slate-400 list-decimal ml-4 space-y-1">
                {data.sequencing.map((s, i) => <li key={i}>{s}</li>)}
              </ol>
            </div>
          )}

          {/* Guardrails + costs */}
          <div className="grid gap-3 md:grid-cols-2">
            {Array.isArray(data.guardrails) && data.guardrails.length > 0 && (
              <div className="rounded-2xl border border-rose-500/20 bg-rose-500/[0.04] p-5">
                <div className="text-sm font-semibold text-rose-300 mb-2">Guardrails</div>
                <ul className="text-[11px] text-slate-400 list-disc ml-4 space-y-1">
                  {data.guardrails.map((g, i) => <li key={i}>{typeof g === 'string' ? g : (g.rule || g.note || JSON.stringify(g))}</li>)}
                </ul>
              </div>
            )}
            {Array.isArray(data.cost_considerations) && data.cost_considerations.length > 0 && (
              <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
                <div className="text-sm font-semibold text-white mb-2">Cost considerations</div>
                <ul className="text-[11px] text-slate-400 list-disc ml-4 space-y-1">
                  {data.cost_considerations.map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              </div>
            )}
          </div>

          {/* Disclaimers — verbatim from the engine */}
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-1.5 text-[11px] text-slate-500">
            {data.is_not && <div><span className="text-slate-400 font-semibold">Not: </span>{data.is_not}</div>}
            {data.estimates_disclaimer && <div>{data.estimates_disclaimer}</div>}
            {data.fx_assumption && <div>{data.fx_assumption}</div>}
            {data.disclaimer && <div>{data.disclaimer}</div>}
          </div>
        </div>
      )}

      {data && !data.available && (
        <div className="text-sm text-slate-500">{data.reason || 'No result.'}</div>
      )}
    </div>
  )
}
