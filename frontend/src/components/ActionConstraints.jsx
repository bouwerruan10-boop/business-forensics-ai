import { useEffect, useState } from 'react'
import InfoTip from './InfoTip'

export default function ActionConstraints({ analysisId }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    let on = true
    import('../api/client').then(({ getActionConstraints }) => getActionConstraints(analysisId))
      .then(d => { if (on) setData(d) }).catch(() => { if (on) setData(null) })
    return () => { on = false }
  }, [analysisId])

  if (!data || !data.actions?.length) return null

  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 mb-4">
      <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
        What you can change — and what's fixed
        <InfoTip label="Changeable vs fixed" text="For each lever: a realistic ceiling (most of the gap isn't reachable), what's typically fixed, and grounded do's and don'ts. Decision-support — it does not change the Imara Score." />
      </div>

      <div className="space-y-3">
        {data.actions.map((a, i) => (
          <div key={i} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5">
            <div className="flex items-center justify-between gap-2">
              <span className="text-white text-sm font-medium truncate">{a.label}</span>
              {a.realistic_ceiling !== null && a.realistic_ceiling !== undefined && (
                <span className="text-xs text-slate-400 shrink-0">
                  realistic ≈ {a.realistic_ceiling}{a.unit === '%' ? '%' : ` ${a.unit || ''}`}
                  {typeof a.max === 'number' && <span className="text-slate-600"> / {a.max} max</span>}
                </span>
              )}
            </div>

            {a.fixed && (
              <p className="text-[11px] text-slate-500 mt-1.5">
                <span className="text-slate-400">Fixed:</span> {a.fixed}
                {a.timeline && <span className="text-slate-600"> · {a.timeline}</span>}
              </p>
            )}

            <div className="grid sm:grid-cols-2 gap-3 mt-2.5">
              <div>
                <div className="text-[11px] text-emerald-300/90 font-medium mb-1">✓ Do</div>
                <ul className="space-y-0.5">
                  {a.dos?.map((d, j) => <li key={j} className="text-[11px] text-slate-400 leading-relaxed">• {d}</li>)}
                </ul>
              </div>
              <div>
                <div className="text-[11px] text-red-300/90 font-medium mb-1">✗ Don't</div>
                <ul className="space-y-0.5">
                  {a.donts?.map((d, j) => <li key={j} className="text-[11px] text-slate-400 leading-relaxed">• {d}</li>)}
                </ul>
              </div>
            </div>
          </div>
        ))}
      </div>
      {data.note && <p className="text-[11px] text-slate-600 mt-3">{data.note}</p>}
    </div>
  )
}
