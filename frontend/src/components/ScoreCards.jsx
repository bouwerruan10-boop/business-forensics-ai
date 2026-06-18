function ScoreRing({ score, size = 80 }) {
  const r = (size / 2) - 6
  const circ = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(100, score)) / 100
  const offset = circ * (1 - pct)
  const color = score >= 70 ? '#22c55e' : score >= 40 ? '#f59e0b' : '#ef4444'
  return (
    <svg width={size} height={size} className="transform -rotate-90">
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="5" />
      <circle
        cx={size/2} cy={size/2} r={r} fill="none"
        stroke={color} strokeWidth="5"
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 1s ease' }}
      />
    </svg>
  )
}

function ScoreCard({ label, score, subtitle }) {
  const color = score >= 70 ? 'text-emerald-400' : score >= 40 ? 'text-amber-400' : 'text-red-400'
  const badge = score >= 70 ? 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20'
    : score >= 40 ? 'bg-amber-400/10 text-amber-400 border-amber-400/20'
    : 'bg-red-400/10 text-red-400 border-red-400/20'
  const status = score >= 70 ? 'Good' : score >= 40 ? 'Needs Work' : 'Critical'
  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 card-hover flex flex-col items-center text-center">
      <div className="relative mb-3">
        <ScoreRing score={score} size={80} />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-lg font-bold ${color}`}>{score}</span>
        </div>
      </div>
      <div className="text-white text-sm font-semibold mb-1">{label}</div>
      <div className={`text-xs border rounded-full px-2 py-0.5 ${badge}`}>{status}</div>
      {subtitle && <div className="text-slate-600 text-xs mt-2">{subtitle}</div>}
    </div>
  )
}

function CreditCard({ score, grade }) {
  const color = score >= 60 ? 'text-emerald-400' : score >= 40 ? 'text-amber-400' : 'text-red-400'
  const badge = score >= 60
    ? 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20'
    : score >= 40
    ? 'bg-amber-400/10 text-amber-400 border-amber-400/20'
    : 'bg-red-400/10 text-red-400 border-red-400/20'
  if (!score && !grade) return null
  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 card-hover flex flex-col items-center text-center">
      <div className="relative mb-3">
        <ScoreRing score={score} size={80} />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-lg font-bold ${color}`}>{grade || score}</span>
        </div>
      </div>
      <div className="text-white text-sm font-semibold mb-1">Credit Readiness</div>
      <div className={`text-xs border rounded-full px-2 py-0.5 ${badge}`}>{score}/100</div>
      <div className="text-slate-600 text-xs mt-2">Grade: {grade || '—'}</div>
    </div>
  )
}

function FraudCard({ level, score }) {
  if (!level || level === 'unknown') return null
  const colorMap = { low: 'text-emerald-400', medium: 'text-amber-400', high: 'text-orange-400', critical: 'text-red-400' }
  const badgeMap = {
    low:      'bg-emerald-400/10 text-emerald-400 border-emerald-400/20',
    medium:   'bg-amber-400/10 text-amber-400 border-amber-400/20',
    high:     'bg-orange-400/10 text-orange-400 border-orange-400/20',
    critical: 'bg-red-400/10 text-red-400 border-red-400/20',
  }
  const col   = colorMap[level] || 'text-slate-400'
  const badge = badgeMap[level] || 'bg-slate-400/10 text-slate-400 border-slate-400/20'
  const displayScore = 100 - (score || 0)
  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 card-hover flex flex-col items-center text-center">
      <div className="relative mb-3">
        <ScoreRing score={displayScore} size={80} />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-sm font-bold ${col}`}>{level.charAt(0).toUpperCase() + level.slice(1)}</span>
        </div>
      </div>
      <div className="text-white text-sm font-semibold mb-1">Fraud Risk</div>
      <div className={`text-xs border rounded-full px-2 py-0.5 ${badge}`}>{level.toUpperCase()}</div>
      <div className="text-slate-600 text-xs mt-2">Risk score: {score}/100</div>
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
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 card-hover flex flex-col items-center text-center">
      <div className="mb-3 flex flex-col items-center justify-center h-[80px]">
        <span className="text-gold font-bold text-xl leading-tight">{fmt(mid)}</span>
        <span className="text-slate-600 text-xs mt-1">mid-point</span>
      </div>
      <div className="text-white text-sm font-semibold mb-1">Est. Valuation</div>
      <div className="text-xs border border-gold/20 rounded-full px-2 py-0.5 text-gold/80 bg-gold/5">
        {fmt(low)} — {fmt(high)}
      </div>
      <div className="text-slate-600 text-xs mt-2">Bear / Bull range</div>
    </div>
  )
}

function MarketCard({ score, sentiment }) {
  if (!score && score !== 0) return null
  const color = score >= 70 ? 'text-emerald-400' : score >= 40 ? 'text-amber-400' : 'text-red-400'
  const badge = score >= 70 ? 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20'
    : score >= 40 ? 'bg-amber-400/10 text-amber-400 border-amber-400/20'
    : 'bg-red-400/10 text-red-400 border-red-400/20'
  const sentimentLabel = sentiment
    ? sentiment.charAt(0).toUpperCase() + sentiment.slice(1)
    : '—'
  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 card-hover flex flex-col items-center text-center">
      <div className="relative mb-3">
        <ScoreRing score={score} size={80} />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-lg font-bold ${color}`}>{score}</span>
        </div>
      </div>
      <div className="text-white text-sm font-semibold mb-1">Market Visibility</div>
      <div className={`text-xs border rounded-full px-2 py-0.5 ${badge}`}>{score}/100</div>
      <div className="text-slate-600 text-xs mt-2">Sentiment: {sentimentLabel}</div>
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
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-4 xl:grid-cols-8 gap-4">
      {cards.map(function(c) {
        return <ScoreCard key={c.key} label={c.label} score={scores[c.key] || 0} subtitle={c.subtitle} />
      })}
      {showMarket && (
        <MarketCard score={report.market_visibility_score ?? 0} sentiment={report.market_sentiment} />
      )}
      {showCredit && (
        <CreditCard score={report.credit_score} grade={report.credit_grade} />
      )}
      {showFraud && (
        <FraudCard level={report.fraud_risk_level} score={report.fraud_risk_score} />
      )}
      {showValuation && (
        <ValuationCard
          low={report.valuation_low}
          mid={report.valuation_mid}
          high={report.valuation_high}
          currency={cur}
        />
      )}
    </div>
  )
}
