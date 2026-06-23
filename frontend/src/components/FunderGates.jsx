import { useEffect, useState } from 'react'
import InfoTip from './InfoTip'
import Skeleton from './Skeleton'

const FIT = {
  good:       { c: 'text-emerald-400', b: 'bg-emerald-500/10 border-emerald-500/25', label: 'Good fit' },
  possible:   { c: 'text-amber-400',   b: 'bg-amber-500/10 border-amber-500/25',     label: 'Possible' },
  unlikely:   { c: 'text-slate-500',   b: 'bg-white/[0.03] border-white/10',         label: 'Unlikely' },
  ineligible: { c: 'text-rose-400',    b: 'bg-rose-500/10 border-rose-500/20',       label: 'Ineligible' },
}
const STATUS = {
  pass:    { i: '✓', c: 'text-emerald-400' },
  fail:    { i: '✕', c: 'text-rose-400' },
  unknown: { i: '○', c: 'text-slate-500' },
  note:    { i: '•', c: 'text-slate-400' },
}

export default function FunderGates({ analysisId }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [tries, setTries] = useState(0)

  useEffect(() => {
    let on = true
    setError(null); setData(null)
    import('../api/client').then(({ getFunderGates }) => getFunderGates(analysisId)
      .then(d => { if (on) setData(d) }).catch(e => { if (on) setError(e.message) }))
    return () => { on = false }
  }, [analysisId, tries])

  if (error) return (
    <div className="text-slate-500 text-sm">Funder gates unavailable: {error}{" "}
      <button type="button" onClick={() => setTries((t) => t + 1)} className="text-gold hover:underline">Try again</button>
    </div>
  )
  if (!data) return <Skeleton lines={4} />
  if (!data.available) return <div className="text-slate-500 text-sm">{data.reason || 'Not computed for this analysis.'}</div>

  return (
    <div className="space-y-5">
      {/* Primary shortlist */}
      {Array.isArray(data.primary) && data.primary.length > 0 && (
        <div className="rounded-2xl border border-emerald-500/25 bg-emerald-500/5 p-5">
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-slate-400 mb-2">
            Funders worth approaching first
            <InfoTip label="Funder gates" text="Objective information about named SA funders whose PUBLISHED eligibility criteria a profile like this may meet — not a recommendation that any provider is suitable for you, and not a credit decision. Each funder makes its own decision; confirm current terms directly." />
          </div>
          <div className="flex flex-wrap gap-1.5">
            {data.primary.map((p, i) => (
              <span key={i} className="text-xs bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 rounded-full px-3 py-1 font-medium">{p}</span>
            ))}
          </div>
        </div>
      )}

      {/* Per-funder cards */}
      <div className="space-y-2">
        {(data.funders || []).map((fu, i) => {
          const f = FIT[fu.fit] || FIT.unlikely
          return (
            <div key={i} className={`rounded-xl border p-3.5 ${f.b}`}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <span className="text-white text-sm font-semibold">{fu.name}</span>
                  <span className="text-slate-500 text-[11px] ml-2">{fu.type} · {fu.ticket_range}</span>
                </div>
                <span className={`shrink-0 text-[10px] uppercase font-bold ${f.c}`}>{f.label}</span>
              </div>
              <div className="text-slate-300 text-xs mt-1.5 leading-relaxed">{fu.why}</div>
              {Array.isArray(fu.checks) && fu.checks.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {fu.checks.map((c, j) => {
                    const st = STATUS[c.status] || STATUS.unknown
                    return (
                      <li key={j} className="text-[11px] text-slate-400 flex gap-1.5">
                        <span className={`${st.c} font-bold`}>{st.i}</span>
                        <span><span className="text-slate-300">{c.gate}</span> — {c.note}</span>
                      </li>
                    )
                  })}
                </ul>
              )}
              {fu.requirements && <div className="text-slate-400 text-[11px] mt-2"><span className="text-slate-500">Needs: </span>{fu.requirements}</div>}
              {fu.caveat && <div className="text-slate-500 text-[11px] mt-0.5 italic">{fu.caveat}</div>}
              {fu.source && <div className="text-slate-600 text-[10px] mt-1">Source: {fu.source}</div>}
            </div>
          )
        })}
      </div>

      {/* Data gaps */}
      {Array.isArray(data.data_gaps) && data.data_gaps.length > 0 && (
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-2">To firm up the matches</div>
          <ul className="space-y-1">
            {data.data_gaps.map((g, i) => <li key={i} className="text-xs text-slate-400">• {g}</li>)}
          </ul>
        </div>
      )}

      <p className="text-slate-600 text-[11px] leading-relaxed italic">{data.disclaimer}</p>
    </div>
  )
}
