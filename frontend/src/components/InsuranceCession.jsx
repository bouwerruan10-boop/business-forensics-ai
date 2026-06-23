import { useEffect, useState } from 'react'
import InfoTip from './InfoTip'
import Skeleton from './Skeleton'

const READY = {
  strong:  { c: 'text-emerald-400', b: 'bg-emerald-500/10 border-emerald-500/25', label: 'Strong' },
  partial: { c: 'text-amber-400',   b: 'bg-amber-500/10 border-amber-500/25',     label: 'Partial' },
  low:     { c: 'text-rose-400',    b: 'bg-rose-500/10 border-rose-500/25',       label: 'Low' },
}
const EV = {
  present: { i: '✓', c: 'text-emerald-400' },
  none:    { i: '✕', c: 'text-rose-400' },
  unknown: { i: '○', c: 'text-slate-500' },
}

export default function InsuranceCession({ analysisId }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [tries, setTries] = useState(0)

  useEffect(() => {
    let on = true
    setError(null); setData(null)
    import('../api/client').then(({ getInsuranceCession }) => getInsuranceCession(analysisId)
      .then(d => { if (on) setData(d) }).catch(e => { if (on) setError(e.message) }))
    return () => { on = false }
  }, [analysisId, tries])

  if (error) return (
    <div className="text-slate-500 text-sm">Insurance check unavailable: {error}{" "}
      <button type="button" onClick={() => setTries((t) => t + 1)} className="text-gold hover:underline">Try again</button>
    </div>
  )
  if (!data) return <Skeleton lines={4} />
  if (!data.available) return <div className="text-slate-500 text-sm">{data.reason || 'Not computed for this analysis.'}</div>

  const r = READY[data.readiness] || READY.low

  return (
    <div className="space-y-5">
      {/* Readiness header */}
      <div className={`rounded-2xl border p-5 ${r.b}`}>
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-slate-400 mb-1">
          Insurance & cession readiness
          <InfoTip label="Insurance & cession" text="In SA, security over a policy is taken by CESSION (you cede the policy to the lender). This shows which covers a lender expects to be in place and ceded, with any evidence in your documents. Not financial or insurance advice, not a product recommendation, and not an Imara Score input." />
        </div>
        <div className="flex items-baseline gap-3 flex-wrap">
          <span className={`text-2xl font-bold ${r.c}`}>{r.label}</span>
          <span className="text-xs text-slate-400">{data.evidenced_count}/{data.relevant_count} relevant covers evidenced · {data.ceded_observed ? 'cession referenced' : 'no cession detected'}</span>
        </div>
        {data.summary && <p className="text-slate-300 text-sm mt-2 leading-relaxed">{data.summary}</p>}
      </div>

      {/* Covers */}
      <div className="space-y-2">
        {(data.covers || []).map((c, i) => {
          const ev = EV[c.evidence] || EV.unknown
          const muted = !c.relevant
          return (
            <div key={i} className={`rounded-xl border p-3 ${muted ? 'bg-white/[0.02] border-white/5' : 'bg-white/[0.03] border-white/10'}`}>
              <div className="flex items-start justify-between gap-3">
                <span className={`text-sm font-medium ${muted ? 'text-slate-400' : 'text-white'}`}>{c.cover}</span>
                <span className="shrink-0 flex items-center gap-2">
                  {c.relevant
                    ? <span className="text-[10px] uppercase font-bold text-sky-400">Lender expects</span>
                    : <span className="text-[10px] uppercase text-slate-600">Less critical here</span>}
                  <span className={`${ev.c} font-bold text-sm`} title={`Evidence: ${c.evidence}`}>{ev.i}</span>
                </span>
              </div>
              <div className="text-slate-400 text-xs mt-1 leading-relaxed">{c.why_lender_wants_it}</div>
              <div className="flex items-center gap-2 mt-1.5">
                {c.cession_status !== 'n/a' && (
                  <span className={`text-[10px] rounded-full px-2 py-0.5 border ${c.cession_status === 'ceded' ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-300' : 'bg-white/[0.04] border-white/10 text-slate-400'}`}>
                    {c.cession_status === 'ceded' ? '✓ ceded to lender' : c.cession_status === 'not_ceded' ? 'not ceded' : 'cession unknown'}
                  </span>
                )}
              </div>
              {c.action && <div className="text-slate-400 text-[11px] mt-1.5"><span className="text-slate-500">Action: </span>{c.action}</div>}
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
