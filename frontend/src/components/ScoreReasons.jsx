import { useEffect, useState } from 'react'
import InfoTip from './InfoTip'

export default function ScoreReasons({ analysisId }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    let on = true
    import('../api/client').then(({ getReasons }) => getReasons(analysisId))
      .then(d => { if (on) setData(d) }).catch(() => { if (on) setData(null) })
    return () => { on = false }
  }, [analysisId])

  if (!data || !data.available || !data.reasons?.length) return null
  const maxImpact = Math.max(...data.reasons.map(r => r.impact), 1)

  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 mb-4">
      <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
        Why this score — principal factors
        <InfoTip label="Score drivers" text="The factors holding the Imara Score back, ordered by impact, derived directly from the score's own weighted components and tied to the underlying numbers. Decision-support — not a credit decision or adverse-action notice under the NCA." />
      </div>

      <div className="space-y-2.5">
        {data.reasons.map((r, i) => (
          <div key={i} className="flex items-start gap-3">
            <span className="text-slate-600 text-xs font-bold w-4 mt-0.5">{i + 1}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="text-white text-sm font-medium">{r.factor}</span>
                <span className="text-slate-500 text-xs tabular-nums">{r.score}/100</span>
              </div>
              <div className="text-slate-400 text-xs mt-0.5">{r.detail}</div>
              <div className="mt-1 h-1 rounded-full bg-white/[0.06] overflow-hidden">
                <div className="h-full bg-gold/70 rounded-full" style={{ width: `${Math.round((r.impact / maxImpact) * 100)}%` }} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {data.strengths?.length > 0 && (
        <div className="mt-4">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1.5">Strengths</div>
          <div className="flex flex-wrap gap-1.5">
            {data.strengths.map((s, i) => (
              <span key={i} className="text-[11px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full px-2.5 py-1">
                {s.factor} <span className="text-emerald-300/70">{s.score}</span>
              </span>
            ))}
          </div>
        </div>
      )}
      <p className="text-slate-600 text-[11px] mt-3 leading-relaxed italic">{data.disclaimer}</p>
    </div>
  )
}
