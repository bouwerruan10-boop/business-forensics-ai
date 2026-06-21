import { useEffect, useState } from 'react'
import InfoTip from './InfoTip'

const FIT = {
  good:     { c: 'text-emerald-400', b: 'bg-emerald-500/10 border-emerald-500/25', label: 'Good fit' },
  possible: { c: 'text-amber-400',   b: 'bg-amber-500/10 border-amber-500/25',     label: 'Possible' },
  unlikely: { c: 'text-slate-500',   b: 'bg-white/[0.03] border-white/10',         label: 'Unlikely' },
}

export default function FundingFit({ analysisId }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let on = true
    import('../api/client').then(({ getFundingFit }) => getFundingFit(analysisId)
      .then(d => { if (on) setData(d) }).catch(e => { if (on) setError(e.message) }))
    return () => { on = false }
  }, [analysisId])

  if (error) return <div className="text-slate-600 text-sm">Funding-fit unavailable: {error}</div>
  if (!data) return <div className="text-slate-500 text-sm">Working out which funding paths fit…</div>
  if (!data.available) return <div className="text-slate-500 text-sm">{data.reason || 'Not computed for this analysis.'}</div>

  const gate = data.gate || {}
  const strengthen = gate.status === 'strengthen-first'
  const el = data.eligibility || {}

  return (
    <div className="space-y-5">
      {/* Gate */}
      <div className={`rounded-2xl border p-5 ${strengthen ? 'bg-amber-500/5 border-amber-500/25' : 'bg-emerald-500/5 border-emerald-500/25'}`}>
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-slate-400 mb-1">
          {strengthen ? 'Strengthen first' : 'Application-ready'}
          <InfoTip label="Which path fits" text="Objective information about the TYPES of funding that commonly fit a profile like this, computed from your own figures and bank conduct. Not a recommendation of any specific product or provider, and not a credit decision." />
        </div>
        <p className={`text-sm leading-relaxed ${strengthen ? 'text-amber-200' : 'text-emerald-300'}`}>
          {strengthen
            ? 'A few things are holding the commercial paths back — address these first (the Bank-Ready Pack lists the fixes), then they open up.'
            : 'This profile meets the typical commercial-lender floors and is positioned to apply.'}
        </p>
        {strengthen && Array.isArray(gate.reasons) && gate.reasons.length > 0 && (
          <ul className="mt-2 space-y-1">
            {gate.reasons.map((r, i) => <li key={i} className="text-xs text-amber-200/90">• {r}</li>)}
          </ul>
        )}
        {/* eligibility ticks */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {[['Turnover ≥ R1m', el.turnover_ok], ['12+ months trading', el.trading_ok], ['CIPC registered', el.cipc_ok]].map(([t, ok], i) => (
            <span key={i} className={`text-[11px] rounded-full px-2.5 py-1 border ${ok ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-300' : 'bg-white/[0.04] border-white/10 text-slate-400'}`}>
              {ok ? '✓' : '○'} {t}
            </span>
          ))}
        </div>
      </div>

      {/* Primary paths */}
      {Array.isArray(data.primary_paths) && data.primary_paths.length > 0 && (
        <div>
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-2">Best-fit paths for this profile</div>
          <div className="flex flex-wrap gap-1.5">
            {data.primary_paths.map((p, i) => (
              <span key={i} className="text-xs bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 rounded-full px-3 py-1 font-medium">{p}</span>
            ))}
          </div>
        </div>
      )}

      {/* All options */}
      <div className="space-y-2">
        {(data.options || []).map((o, i) => {
          const f = FIT[o.fit] || FIT.unlikely
          return (
            <div key={i} className={`rounded-xl border p-3 ${f.b}`}>
              <div className="flex items-start justify-between gap-3">
                <span className="text-white text-sm font-medium">{o.label}</span>
                <span className={`shrink-0 text-[10px] uppercase font-bold ${f.c}`}>{f.label}</span>
              </div>
              <div className="text-slate-300 text-xs mt-1 leading-relaxed">{o.why}</div>
              {o.requirements && <div className="text-slate-400 text-[11px] mt-1.5"><span className="text-slate-500">Needs: </span>{o.requirements}</div>}
              {o.caveat && <div className="text-slate-500 text-[11px] mt-0.5 italic">{o.caveat}</div>}
            </div>
          )
        })}
      </div>

      <p className="text-slate-600 text-[11px] leading-relaxed italic">{data.note}</p>
    </div>
  )
}
