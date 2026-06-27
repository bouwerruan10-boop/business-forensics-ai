import { useEffect, useState } from 'react'
import InfoTip from './InfoTip'

const STATUS_DOT = {
  good: 'bg-emerald-400',
  warning: 'bg-amber-400',
  critical: 'bg-red-400',
}
const fmt = (v, unit) => {
  if (v === null || v === undefined) return 'n/a'
  const u = (unit || '').trim()
  if (u === '%') return `${Number(v).toLocaleString('en-ZA', { maximumFractionDigits: 1 })}%`
  return u ? `${Number(v).toLocaleString('en-ZA', { maximumFractionDigits: 1 })} ${u}` : Number(v).toLocaleString('en-ZA')
}

export default function FinancialRatioDiagnostics({ analysisId }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    let on = true
    import('../api/client').then(({ getRatioDiagnostics }) => getRatioDiagnostics(analysisId))
      .then(d => { if (on) setData(d) }).catch(() => { if (on) setData(null) })
    return () => { on = false }
  }, [analysisId])

  if (!data || !data.diagnostics?.length) return null

  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 mb-4">
      <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
        What your ratios mean — and what to do
        <InfoTip label="Ratio diagnostics" text="Each computed ratio in plain language, joined to the findings that reference it and the action that closes its gap. Deterministic — derived from your figures and the sector benchmark, not generated text." />
      </div>

      <div className="space-y-3">
        {data.diagnostics.map((d, i) => (
          <div key={i} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <span className={`w-2 h-2 rounded-full shrink-0 ${STATUS_DOT[d.status] || 'bg-slate-500'}`} />
                <span className="text-white text-sm font-medium truncate">{d.label}</span>
              </div>
              <span className="text-slate-300 text-sm shrink-0">
                {fmt(d.value, d.unit)}
                {d.benchmark !== null && d.benchmark !== undefined && (
                  <span className="text-slate-500"> vs {fmt(d.benchmark, d.unit)}</span>
                )}
              </span>
            </div>

            <p className="text-slate-400 text-xs mt-2 leading-relaxed">{d.plain_meaning}</p>

            {d.recommendation && (
              <div className="mt-2 flex items-start gap-2">
                <span className="text-gold text-xs mt-0.5">→</span>
                <div className="text-xs">
                  <span className="text-gold font-medium">{d.recommendation.label}</span>
                  {d.recommendation.rationale && (
                    <span className="text-slate-500"> — {d.recommendation.rationale}</span>
                  )}
                </div>
              </div>
            )}

            {d.linked_findings?.length > 0 && (
              <div className="mt-2 text-[11px] text-slate-500">
                Related findings: {d.linked_findings.join(' · ')}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
