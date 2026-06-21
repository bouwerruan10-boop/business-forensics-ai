import { useEffect, useState } from 'react'

const BAND = {
  A: { c: '#C9A84C', verdict: 'Investment-ready — the fundamentals support funding now.' },
  B: { c: '#34d399', verdict: 'Bankable — lenders should view this favourably.' },
  C: { c: '#fbbf24', verdict: 'Developing — bankable with conditions; close the gaps below.' },
  D: { c: '#fb923c', verdict: 'At risk — fundability is limited until the critical issues are fixed.' },
  E: { c: '#ef4444', verdict: 'Distressed — urgent action is needed before seeking finance.' },
}

function money(n, cur = 'ZAR') {
  if (n == null) return null
  const a = Math.abs(n)
  if (a >= 1e6) return `${cur} ${(a / 1e6).toFixed(1)}M`
  if (a >= 1e3) return `${cur} ${(a / 1e3).toFixed(0)}K`
  return `${cur} ${a.toFixed(0)}`
}

function useCountUp(target, ms = 1100) {
  const [v, setV] = useState(0)
  useEffect(() => {
    let raf
    const t0 = performance.now()
    const tick = (t) => {
      const p = Math.min(1, (t - t0) / ms)
      setV(Math.round((target || 0) * (1 - Math.pow(1 - p, 3))))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, ms])
  return v
}

function Ring({ score, color, size = 128 }) {
  const stroke = 10
  const r = size / 2 - stroke
  const circ = 2 * Math.PI * r
  const off = circ * (1 - Math.max(0, Math.min(100, score)) / 100)
  return (
    <svg width={size} height={size} className="-rotate-90" role="img" aria-label={`Imara Score ${score} of 100`}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={stroke} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
        strokeDasharray={circ} strokeDashoffset={off} strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 1.1s ease' }} />
    </svg>
  )
}

export default function VerdictHero({ report }) {
  if (!report || report.imara_score == null) return null
  const score = report.imara_score || 0
  const band = (report.imara_band || 'C').toUpperCase()
  const meta = BAND[band] || BAND.C
  const color = report.imara_color || meta.c
  const animated = useCountUp(score)
  const cur = report.currency || 'ZAR'
  const fix = (report.top_priority_issues || [])[0]
  const qw = (report.quick_wins || []).length
  const sav = report.supplier_benchmark?.available ? money(report.supplier_benchmark.total_est_saving_high, cur) : null
  const z = report.distress_score?.available ? report.distress_score : null

  const chips = []
  if (qw) chips.push(`${qw} quick wins`)
  if (sav) chips.push(`Save up to ${sav}/yr`)
  if (report.credit_grade) chips.push(`Credit ${report.credit_grade}`)
  if (z) chips.push(`Z″ ${z.z_score} (${z.zone})`)

  return (
    <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-navy-card p-6 sm:p-8 mb-8">
      <div className="absolute -top-24 -right-24 w-72 h-72 rounded-full blur-3xl opacity-20" style={{ background: color }} aria-hidden="true" />
      <div className="relative flex flex-col md:flex-row md:items-center gap-6">
        <div className="relative shrink-0 grid place-items-center" style={{ width: 128, height: 128 }}>
          <Ring score={score} color={color} />
          <div className="absolute text-center">
            <div className="text-4xl font-bold tabular-nums" style={{ color }}>{animated}</div>
            <div className="text-[10px] text-slate-500 -mt-1">/ 100</div>
          </div>
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className="text-xs font-bold uppercase tracking-widest px-2.5 py-1 rounded-full border"
              style={{ color, borderColor: color + '55', background: color + '14' }}>
              Band {band} &middot; {report.imara_label || ''}
            </span>
            <span className="text-slate-500 text-xs">{report.business_name}</span>
          </div>
          <p className="text-white text-lg sm:text-xl font-medium leading-snug">{meta.verdict}</p>
          {fix && (
            <p className="text-slate-400 text-sm mt-2">
              <span className="text-orange-300 font-semibold">Fix first:</span> {fix.title}
              {fix.estimated_total_impact ? ` — ${fix.estimated_total_impact}` : ''}
            </p>
          )}
          {chips.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {chips.map((c, i) => (
                <span key={i} className="text-[11px] text-slate-300 bg-white/[0.05] border border-white/10 rounded-full px-2.5 py-1">{c}</span>
              ))}
            </div>
          )}
          <div className="mt-4 flex flex-wrap gap-3">
            <a href="#simulator" className="text-xs font-semibold text-[#0D1B2A] bg-gold rounded-lg px-3 py-2 hover:brightness-110 transition">Model what-if scenarios &rarr;</a>
            <a href="#evidence" className="text-xs font-semibold text-slate-200 border border-white/15 rounded-lg px-3 py-2 hover:bg-white/5 transition">See the evidence</a>
          </div>
        </div>
      </div>
    </div>
  )
}
