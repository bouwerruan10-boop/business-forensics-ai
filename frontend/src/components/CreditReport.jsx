// Credit Readiness Panel — credit score, grade, barriers/strengths, products

function GradeRing({ score, grade }) {
  const r = 52
  const circ = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(100, score)) / 100
  const offset = circ * (1 - pct)
  const color = score >= 70 ? '#22c55e' : score >= 50 ? '#f59e0b' : '#ef4444'
  const ringBg = score >= 70 ? 'rgba(34,197,94,0.08)' : score >= 50 ? 'rgba(245,158,11,0.08)' : 'rgba(239,68,68,0.08)'

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative">
        <svg width={128} height={128} className="-rotate-90">
          <circle cx={64} cy={64} r={r} fill={ringBg} stroke="rgba(255,255,255,0.06)" strokeWidth="7" />
          <circle
            cx={64} cy={64} r={r} fill="none"
            stroke={color} strokeWidth="7"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 1.2s ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-black" style={{ color }}>{grade || '—'}</span>
          <span className="text-slate-500 text-xs">{score}/100</span>
        </div>
      </div>
      <div className="text-white font-bold text-sm mt-2">Credit Readiness</div>
      <div className="text-slate-500 text-xs">SA Lender Assessment</div>
    </div>
  )
}

function FraudBadge({ level, score }) {
  if (!level || level === 'unknown') return null
  const styles = {
    low:      { bg: 'bg-emerald-500/10', border: 'border-emerald-500/25', text: 'text-emerald-400', label: 'LOW RISK' },
    medium:   { bg: 'bg-amber-500/10',   border: 'border-amber-500/25',   text: 'text-amber-400',   label: 'MEDIUM RISK' },
    high:     { bg: 'bg-orange-500/10',  border: 'border-orange-500/25',  text: 'text-orange-400',  label: 'HIGH RISK' },
    critical: { bg: 'bg-red-500/10',     border: 'border-red-500/25',     text: 'text-red-400',     label: 'CRITICAL' },
  }
  const s = styles[level] || styles.medium
  return (
    <div className={`rounded-xl border p-4 ${s.bg} ${s.border} text-center`}>
      <div className={`text-xs font-black uppercase tracking-widest ${s.text} mb-1`}>Fraud Risk</div>
      <div className={`text-xl font-bold ${s.text}`}>{s.label}</div>
      <div className="text-slate-500 text-xs mt-1">Score: {score}/100</div>
    </div>
  )
}

function BarrierStrengths({ strengths, barriers }) {
  if (!strengths?.length && !barriers?.length) return null
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {strengths?.length > 0 && (
        <div>
          <div className="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-2">✓ Strengths</div>
          <ul className="space-y-2">
            {strengths.map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-300 bg-emerald-500/5 border border-emerald-500/10 rounded-lg px-3 py-2">
                <span className="text-emerald-400 mt-0.5 flex-shrink-0">✓</span>
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {barriers?.length > 0 && (
        <div>
          <div className="text-xs font-bold text-red-400 uppercase tracking-wider mb-2">✕ Barriers</div>
          <ul className="space-y-2">
            {barriers.map((b, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-300 bg-red-500/5 border border-red-500/10 rounded-lg px-3 py-2">
                <span className="text-red-400 mt-0.5 flex-shrink-0">✕</span>
                <span>{b}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function ProductBadges({ products }) {
  if (!products?.length) return null
  return (
    <div>
      <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Funding options for this profile</div>
      <p className="text-slate-600 text-[11px] mb-2 italic">Illustrative examples of product types this profile typically qualifies for — objective information, not a recommendation that any product is suitable for you, and not financial advice.</p>
      <div className="flex flex-wrap gap-2">
        {products.map((p, i) => (
          <span key={i} className="text-xs bg-[#0D2540] border border-gold/20 text-gold/80 rounded-full px-3 py-1">
            {p}
          </span>
        ))}
      </div>
    </div>
  )
}

function FraudFlags({ indicators }) {
  if (!indicators?.length) return null
  return (
    <div>
      <div className="text-xs font-bold text-red-400 uppercase tracking-wider mb-2">Fraud Indicators Detected</div>
      <ul className="space-y-1">
        {indicators.map((flag, i) => (
          <li key={i} className="flex items-start gap-2 text-xs text-slate-400">
            <span className="text-red-500 font-bold mt-px flex-shrink-0">{i + 1}.</span>
            <span>{flag}</span>
          </li>
        ))}
      </ul>
      <p className="text-slate-600 text-xs mt-2 italic">
        Findings are indicative. Engage a Certified Fraud Examiner (CFE) for formal investigation.
      </p>
    </div>
  )
}

export default function CreditReport({ report }) {
  const credit = {
    score:     report?.credit_score     || 0,
    grade:     report?.credit_grade     || '',
    barriers:  report?.credit_barriers  || [],
    strengths: report?.credit_strengths || [],
    products:  report?.credit_products  || [],
  }
  const fraud = {
    level:      report?.fraud_risk_level  || 'unknown',
    score:      report?.fraud_risk_score  || 0,
    indicators: report?.fraud_indicators  || [],
  }
  const integrity = report?.bank_statement_integrity || null

  if (!credit.score && !credit.grade && fraud.level === 'unknown' && !integrity) return null

  return (
    <div className="space-y-6">
      {/* Score + fraud badge row */}
      <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-6">
        <div className="flex flex-col sm:flex-row gap-6 items-center sm:items-start">
          {credit.score > 0 && (
            <div className="flex-shrink-0">
              <GradeRing score={credit.score} grade={credit.grade} />
            </div>
          )}
          <div className="flex-1 space-y-4 w-full">
            {fraud.level !== 'unknown' && (
              <FraudBadge level={fraud.level} score={fraud.score} />
            )}
            {fraud.indicators.length > 0 && (
              <FraudFlags indicators={fraud.indicators} />
            )}
          </div>
        </div>
      </div>

      {/* Strengths & barriers */}
      {(credit.strengths.length > 0 || credit.barriers.length > 0) && (
        <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-6">
          <div className="text-white font-bold text-sm mb-4">Credit Assessment Detail</div>
          <BarrierStrengths strengths={credit.strengths} barriers={credit.barriers} />
        </div>
      )}

      {/* Recommended products */}
      {credit.products.length > 0 && (
        <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-6">
          <ProductBadges products={credit.products} />
        </div>
      )}

      {/* Bank-statement integrity (deterministic: reconciliation + PDF tamper signals) */}
      {integrity?.statements?.length > 0 && (() => {
        const c = integrity.overall === 'elevated' ? '#ef4444' : integrity.overall === 'review' ? '#f59e0b' : '#22c55e'
        const reconLabel = { reconciled: '✓ balances tie out', discrepancy: '✗ does not reconcile', insufficient_data: '? not enough data' }
        const metaLabel = { clean: '✓ no tamper signal', review: '? review metadata', likely_tampered: '✗ likely tampered', unknown: '— no metadata' }
        return (
          <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="text-white font-bold text-sm">Bank-statement integrity</div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded border" style={{ color: c, borderColor: c + '55', background: c + '15' }}>
                {integrity.overall.toUpperCase()}
              </span>
            </div>
            <div className="space-y-3">
              {integrity.statements.map((s, i) => (
                <div key={i} className="bg-[#0f1117] border border-white/8 rounded-xl p-3">
                  <div className="text-[11px] text-slate-300 font-medium mb-1 truncate">{s.filename}</div>
                  <div className="flex flex-wrap gap-2 text-[10px] text-slate-400">
                    <span>{reconLabel[s.reconciliation?.status] || s.reconciliation?.status}</span>
                    <span className="text-slate-600">·</span>
                    <span>{metaLabel[s.metadata?.status] || s.metadata?.status}</span>
                  </div>
                  {(s.metadata?.flags || []).map((f, j) => (
                    <div key={j} className="text-[10px] text-amber-300/90 mt-1">⚠ {f}</div>
                  ))}
                  {s.reconciliation?.status === 'discrepancy' && (
                    <div className="text-[10px] text-red-300 mt-1">⚠ {s.reconciliation.note}</div>
                  )}
                </div>
              ))}
            </div>
            <p className="text-[9px] text-slate-600 mt-3">Risk-awareness only — a flag means “verify the original statement”, not “fraud”. Deterministic check; confirm anything material with the bank.</p>
          </div>
        )
      })()}
    </div>
  )
}
