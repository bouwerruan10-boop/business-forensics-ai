// Imara Score™ — branded composite bankability / investability hero metric.
// Blends the specialist agent outputs into a single 0–100 rating with a band
// (A–E) and a transparent component breakdown. Rendered above the score cards.

function bandColor(score) {
  if (score >= 80) return { ring: '#C9A84C', text: 'text-gold', soft: 'bg-gold/10 border-gold/30 text-gold' }       // Investment Ready
  if (score >= 65) return { ring: '#34d399', text: 'text-emerald-400', soft: 'bg-emerald-400/10 border-emerald-400/30 text-emerald-400' } // Bankable
  if (score >= 50) return { ring: '#fbbf24', text: 'text-amber-400', soft: 'bg-amber-400/10 border-amber-400/30 text-amber-400' }   // Developing
  if (score >= 35) return { ring: '#fb923c', text: 'text-orange-400', soft: 'bg-orange-400/10 border-orange-400/30 text-orange-400' } // At Risk
  return { ring: '#ef4444', text: 'text-red-400', soft: 'bg-red-400/10 border-red-400/30 text-red-400' }              // Distressed
}

function HeroRing({ score, color, size = 168 }) {
  const stroke = 11
  const r = (size / 2) - stroke
  const circ = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(100, score)) / 100
  const offset = circ * (1 - pct)
  return (
    <svg width={size} height={size} className="transform -rotate-90">
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={stroke} />
      <circle
        cx={size/2} cy={size/2} r={r} fill="none"
        stroke={color} strokeWidth={stroke}
        strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 1.1s ease' }}
      />
    </svg>
  )
}

function ComponentBar({ label, value, weight }) {
  const v = Math.max(0, Math.min(100, value))
  const barColor = v >= 70 ? 'bg-emerald-400' : v >= 40 ? 'bg-amber-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-3">
      <div className="w-40 shrink-0 text-slate-300 text-xs font-medium truncate">{label}</div>
      <div className="flex-1 h-2 rounded-full bg-white/[0.06] overflow-hidden">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${v}%`, transition: 'width 1s ease' }} />
      </div>
      <div className="w-9 shrink-0 text-right text-white text-xs font-semibold tabular-nums">{v}</div>
      <div className="w-12 shrink-0 text-right text-slate-500 text-[11px] tabular-nums">
        {Math.round((weight || 0) * 100)}%
      </div>
    </div>
  )
}

export default function ImaraScoreHero({ report }) {
  if (!report || report.imara_score == null) return null
  const score = report.imara_score || 0
  const band = report.imara_band || ''
  const label = report.imara_label || ''
  const components = Array.isArray(report.imara_components) ? report.imara_components : []
  const c = bandColor(score)

  return (
    <div className="relative overflow-hidden bg-navy-card border border-gold/20 rounded-2xl p-6 sm:p-8 mb-6">
      <div className="absolute -top-24 -right-24 w-64 h-64 rounded-full bg-gold/5 blur-3xl pointer-events-none" />
      <div className="relative flex flex-col lg:flex-row gap-8 items-center lg:items-stretch">

        {/* Score ring + band */}
        <div className="flex flex-col items-center justify-center text-center lg:w-64 shrink-0">
          <div className="text-gold text-xs font-semibold tracking-[0.2em] uppercase mb-3">Imara Score™</div>
          <div className="relative">
            <HeroRing score={score} color={c.ring} />
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={`text-5xl font-bold leading-none ${c.text}`}>{score}</span>
              <span className="text-slate-500 text-xs mt-1">out of 100</span>
            </div>
          </div>
          <div className={`mt-4 inline-flex items-center gap-2 border rounded-full px-3 py-1 text-sm font-semibold ${c.soft}`}>
            <span>Band {band}</span>
            <span className="opacity-50">·</span>
            <span>{label}</span>
          </div>
        </div>

        {/* Breakdown */}
        <div className="flex-1 w-full">
          <div className="flex items-baseline justify-between mb-1">
            <h3 className="text-white font-bold text-lg">Bankability &amp; Investability</h3>
            <span className="text-slate-500 text-[11px] uppercase tracking-wider hidden sm:block">Component · Score · Weight</span>
          </div>
          <p className="text-slate-400 text-sm leading-relaxed mb-4">
            A single composite rating synthesising every specialist analysis, weighted toward what a
            lender or investor assesses. Only the components scored in this analysis are included; their
            weights are re-normalised so the score is always out of 100.
          </p>
          <div className="space-y-2.5">
            {components.length > 0 ? (
              components.map((comp, i) => (
                <ComponentBar key={i} label={comp.label} value={comp.value} weight={comp.weight} />
              ))
            ) : (
              <p className="text-slate-500 text-xs">Component breakdown unavailable for this analysis.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
