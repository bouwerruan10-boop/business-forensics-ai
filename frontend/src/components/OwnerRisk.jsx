import { useEffect, useState } from 'react'
import InfoTip from './InfoTip'
import Skeleton from './Skeleton'

const LEVEL = {
  high:     { c: 'text-rose-400',    b: 'bg-rose-500/10 border-rose-500/25',    label: 'High' },
  elevated: { c: 'text-orange-400',  b: 'bg-orange-500/10 border-orange-500/25', label: 'Elevated' },
  moderate: { c: 'text-amber-400',   b: 'bg-amber-500/10 border-amber-500/25',  label: 'Moderate' },
  low:      { c: 'text-emerald-400', b: 'bg-emerald-500/10 border-emerald-500/25', label: 'Low' },
}
const SEV = {
  high:   { c: 'text-rose-400',  b: 'bg-rose-500/10 border-rose-500/25' },
  medium: { c: 'text-amber-400', b: 'bg-amber-500/10 border-amber-500/25' },
  low:    { c: 'text-slate-400', b: 'bg-white/[0.03] border-white/10' },
}

export default function OwnerRisk({ analysisId }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [tries, setTries] = useState(0)

  useEffect(() => {
    let on = true
    setError(null); setData(null)
    import('../api/client').then(({ getOwnerRisk }) => getOwnerRisk(analysisId)
      .then(d => { if (on) setData(d) }).catch(e => { if (on) setError(e.message) }))
    return () => { on = false }
  }, [analysisId, tries])

  if (error) return (
    <div className="text-slate-500 text-sm">Owner-risk unavailable: {error}{" "}
      <button type="button" onClick={() => setTries((t) => t + 1)} className="text-gold hover:underline">Try again</button>
    </div>
  )
  if (!data) return <Skeleton lines={4} />
  if (!data.available) return <div className="text-slate-500 text-sm">{data.reason || 'Not computed for this analysis.'}</div>

  const lvl = LEVEL[data.owner_risk_level] || LEVEL.moderate

  return (
    <div className="space-y-5">
      {/* Level header */}
      <div className={`rounded-2xl border p-5 ${lvl.b}`}>
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-slate-400 mb-1">
          Owner-level (personal) risk
          <InfoTip label="Owner risk" text="SA SME lending is blended: the owner usually signs a personal surety and lenders pull the owner's personal credit too. This is an indicative view from your own records — higher score = more owner exposure. Not an NCA credit decision, not a personal credit-bureau assessment, and not advice." />
        </div>
        <div className="flex items-baseline gap-3">
          <span className={`text-3xl font-bold ${lvl.c}`}>{data.owner_risk_score}<span className="text-base text-slate-500">/100</span></span>
          <span className={`text-xs uppercase font-bold ${lvl.c}`}>{lvl.label} exposure</span>
        </div>
        {data.summary && <p className="text-slate-300 text-sm mt-2 leading-relaxed">{data.summary}</p>}
      </div>

      {/* Factors */}
      <div className="space-y-2">
        {(data.factors || []).map((f, i) => {
          const s = SEV[f.severity] || SEV.low
          return (
            <div key={i} className={`rounded-xl border p-3 ${s.b}`}>
              <div className="flex items-start justify-between gap-3">
                <span className="text-white text-sm font-medium">{f.title}</span>
                <span className={`shrink-0 text-[10px] uppercase font-bold ${s.c}`}>{f.severity}</span>
              </div>
              <div className="text-slate-300 text-xs mt-1 leading-relaxed">{f.detail}</div>
              {f.what_to_fix && <div className="text-slate-400 text-[11px] mt-1.5"><span className="text-slate-500">Fix: </span>{f.what_to_fix}</div>}
            </div>
          )
        })}
      </div>

      {/* Data gaps */}
      {Array.isArray(data.data_gaps) && data.data_gaps.length > 0 && (
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-2">What a lender still needs (not in your data)</div>
          <ul className="space-y-1">
            {data.data_gaps.map((g, i) => <li key={i} className="text-xs text-slate-400">• {g}</li>)}
          </ul>
        </div>
      )}

      <p className="text-slate-600 text-[11px] leading-relaxed italic">{data.disclaimer}</p>
    </div>
  )
}
