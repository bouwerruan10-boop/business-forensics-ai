import { CheckCircle2, AlertTriangle, XCircle, Activity } from 'lucide-react'

// Status mapping: colour is ALWAYS paired with an icon + text label so meaning
// never depends on colour alone (WCAG 1.4.1).
function statusMeta(score, goodAt = 70, midAt = 40) {
  if (score >= goodAt) return { label: 'Good', Icon: CheckCircle2, text: 'text-emerald-400', badge: 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20', stroke: '#22c55e' }
  if (score >= midAt)  return { label: 'Needs Work', Icon: AlertTriangle, text: 'text-amber-400', badge: 'bg-amber-400/10 text-amber-400 border-amber-400/20', stroke: '#f59e0b' }
  return { label: 'Critical', Icon: XCircle, text: 'text-red-400', badge: 'bg-red-400/10 text-red-400 border-red-400/20', stroke: '#ef4444' }
}

function ScoreRing({ score, stroke, label, size = 80 }) {
  const r = (size / 2) - 6
  const circ = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(100, score)) / 100
  const offset = circ * (1 - pct)
  return (
    <svg width={size} height={size} className="transform -rotate-90" role="img" aria-label={label}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="5" aria-hidden="true" />
      <circle
        cx={size/2} cy={size/2} r={r} fill="none"
        stroke={stroke} strokeWidth="5"
        strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 1s ease' }}
        aria-hidden="true"
      />
    </svg>
  )
}

function StatusBadge({ meta }) {
  const { Icon, label, badge } = meta
  return (
    <span className={`inline-flex items-center gap-1 text-xs border rounded-full px-2 py-0.5 ${badge}`}>
      <Icon size={12} aria-hidden="true" /> {label}
    </span>
  )
}

function ScoreCard({ label, score, subtitle }) {
  const m = statusMeta(score)
  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 card-hover flex flex-col items-center text-center">
      <div className="relative mb-3">
        <ScoreRing score={score} stroke={m.stroke} label={`${label}: ${score} out of 100, ${m.label}`} />
        <div className="absolute inset-0 flex items-center justify-center" aria-hidden="true">
          <span className={`text-lg font-bold ${m.text}`}>{score}</span>
        </div>
      </div>
      <div className="text-white text-sm font-semibold mb-1">{label}</div>
      <StatusBadge meta={m} />
      {subtitle && <div className="text-slate-500 text-xs mt-2">{subtitle}</div>}
    </div>
  )
}

function CreditCard({ score, grade }) {
  if (!score && !grade) return null
  const m = statusMeta(score, 60, 40)
  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 card-hover flex flex-col items-center text-center">
      <div className="relative mb-3">
        <ScoreRing score={score} stroke={m.stroke} label={`Credit readiness: grade ${grade || score}, ${score} out of 100, ${m.label}`} />
        <div className="absolute inset-0 flex items-center justify-center" aria-hidden="true">
          <span className={`text-lg font-bold ${m.text}`}>{grade || score}</span>
        </div>
      </div>
      <div className="text-white text-sm font-semibold mb-1">Credit Readiness</div>
      <StatusBadge meta={{ ...m, label: `${score}/100` }} />
      <div className="text-slate-500 text-xs mt-2">Grade: {grade || '—'}</div>
    </div>
  )
}

function FraudCard({ level, score }) {
  if (!level || level === 'unknown') return null
  const metaMap = {
    low:      { Icon: CheckCircle2, text: 'text-emerald-400', badge: 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20', stroke: '#22c55e' },
    medium:   { Icon: AlertTriangle, text: 'text-amber-400', badge: 'bg-amber-400/10 text-amber-400 border-amber-400/20', stroke: '#f59e0b' },
    high:     { Icon: AlertTriangle, text: 'text-orange-400', badge: 'bg-orange-400/10 text-orange-400 border-orange-400/20', stroke: '#fb923c' },
    critical: { Icon: XCircle, text: 'text-red-400', badge: 'bg-red-400/10 text-red-400 border-red-400/20', stroke: '#ef4444' },
  }
  const m = metaMap[level] || { Icon: Activity, text: 'text-slate-300', badge: 'bg-slate-400/10 text-slate-300 border-slate-400/20', stroke: '#94a3b8' }
  const displayScore = 100 - (score || 0)
  const lvl = level.charAt(0).toUpperCase() + level.slice(1)
  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 card-hover flex flex-col items-center text-center">
      <div className="relative mb-3">
        <ScoreRing score={displayScore} stroke={m.stroke} label={`Fraud risk: ${lvl}. Risk score ${score} out of 100.`} />
        <div className="absolute inset-0 flex items-center justify-center" aria-hidden="true">
          <span className={`text-sm font-bold ${m.text}`}>{lvl}</span>
        </div>
      </div>
      <div className="text-white text-sm font-semibold mb-1">Fraud Risk</div>
      <span className={`inline-flex items-center gap-1 text-xs border rounded-full px-2 py-0.5 ${m.badge}`}>
        <m.Icon size={12} aria-hidden="true" /> {level.toUpperCase()}
      </span>
      <div className="text-slate-500 text-xs mt-2">Risk score: {score}/100</div>
    </div>
  )
}

function ValuationCard({ low, mid, high, currency }) {
  if (!mid) return null
  const fmt = v => {
    if (!v) return '—'
    if (v >= 1000000000) return currency + ' ' + (v / 1000000000).toFixed(2) + 'B'
    if (v >= 1000000)    return currency + ' ' + (v / 1000000).toFixed(1) + 'M'
    if (v >= 1000)       return currency + ' ' + (v / 1000).toFixed(0) + 'K'
    return currency + ' ' + v.toFixed(0)
  }
  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 card-hover flex flex-col items-center text-center"
         role="img" aria-label={`Estimated valuation midpoint ${fmt(mid)}, range ${fmt(low)} to ${fmt(high)}.`}>
      <div className="mb-3 flex flex-col items-center justify-center h-[80px]" aria-hidden="true">
        <span className="text-gold font-bold text-xl leading-tight">{fmt(mid)}</span>
        <span className="text-slate-500 text-xs mt-1">mid-point</span>
      </div>
      <div className="text-white text-sm font-semibold mb-1" aria-hidden="true">Est. Valuation</div>
      <div className="text-xs border border-gold/20 rounded-full px-2 py-0.5 text-gold/90 bg-gold/5" aria-hidden="true">
        {fmt(low)} — {fmt(high)}
      </div>
      <div className="text-slate-500 text-xs mt-2" aria-hidden="true">Bear / Bull range</div>
    </div>
  )
}

function MarketCard({ score, sentiment }) {
  if (!score && score !== 0) return null
  const m = statusMeta(score)
  const sentimentLabel = sentiment ? sentiment.charAt(0).toUpperCase() + sentiment.slice(1) : '—'
  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 card-hover flex flex-col items-center text-center">
      <div className="relative mb-3">
        <ScoreRing score={score} stroke={m.stroke} label={`Market visibility: ${score} out of 100, ${m.label}. Sentiment ${sentimentLabel}.`} />
        <div className="absolute inset-0 flex items-center justify-center" aria-hidden="true">
          <span className={`text-lg font-bold ${m.text}`}>{score}</span>
        </div>
      </div>
      <div className="text-white text-sm font-semibold mb-1">Market Visibility</div>
      <StatusBadge meta={{ ...m, label: `${score}/100` }} />
      <div className="text-slate-500 text-xs mt-2">Sentiment: {sentimentLabel}</div>
    </div>
  )
}

export default function ScoreCards({ scores, report }) {
  const cards = [
    { label: 'Business Health', key: 'business_health', subtitle: 'Overall' },
    { label: 'Profitability',   key: 'profitability',   subtitle: 'Financial' },
    { label: 'Efficiency',      key: 'efficiency',      subtitle: 'Operations' },
    { label: 'Risk',            key: 'risk',            subtitle: 'Compliance' },
  ]
  const cur           = report && report.currency ? report.currency : 'ZAR'
  const showCredit    = report && report.credit_score > 0
  const showFraud     = report && report.fraud_risk_level && report.fraud_risk_level !== 'unknown'
  const showValuation = report && report.valuation_mid > 0
  const showMarket    = report && report.market_search_performed

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      {cards.map(c => (
        <ScoreCard key={c.key} label={c.label} score={scores[c.key] || 0} subtitle={c.subtitle} />
      ))}
      {showMarket && <MarketCard score={report.market_visibility_score ?? 0} sentiment={report.market_sentiment} />}
      {showCredit && <CreditCard score={report.credit_score} grade={report.credit_grade} />}
      {showFraud && <FraudCard level={report.fraud_risk_level} score={report.fraud_risk_score} />}
      {showValuation && <ValuationCard low={report.valuation_low} mid={report.valuation_mid} high={report.valuation_high} currency={cur} />}
    </div>
  )
}
