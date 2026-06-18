// Valuation & Forecast Panel — three-point valuation bar + 12m forecast scenarios

function fmt(v, cur) {
  if (!v) return '—'
  if (v >= 1_000_000_000) return `${cur} ${(v / 1_000_000_000).toFixed(2)}B`
  if (v >= 1_000_000)     return `${cur} ${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000)         return `${cur} ${(v / 1_000).toFixed(0)}K`
  return `${cur} ${v.toFixed(0)}`
}

function ValuationBar({ low, mid, high, currency }) {
  if (!mid) return null
  // Percentages along bar: bear at 10%, base at 50%, bull at 90%
  const points = [
    { label: 'BEAR', val: low,  x: 10,  color: '#ef4444' },
    { label: 'BASE', val: mid,  x: 50,  color: '#C9A84C' },
    { label: 'BULL', val: high, x: 90,  color: '#22c55e' },
  ]
  return (
    <div className="py-2">
      <div className="relative h-2 rounded-full bg-white/[0.06] mb-8">
        {/* gradient fill */}
        <div className="absolute inset-0 rounded-full bg-gradient-to-r from-red-500/40 via-gold/40 to-emerald-500/40" />
        {points.map(p => (
          <div key={p.label} style={{ left: `${p.x}%` }} className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2">
            <div className="w-4 h-4 rounded-full border-2 border-[#0D1B2A]" style={{ background: p.color }} />
          </div>
        ))}
      </div>
      <div className="flex justify-between">
        {points.map(p => (
          <div key={p.label} className="text-center" style={{ width: '30%' }}>
            <div className="text-xs font-black uppercase tracking-widest mb-0.5" style={{ color: p.color }}>{p.label}</div>
            <div className="text-white font-bold text-sm">{fmt(p.val, currency)}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function MethodRow({ label, value }) {
  if (!value) return null
  return (
    <div className="flex justify-between items-center py-2 border-b border-white/[0.04] last:border-0">
      <span className="text-slate-500 text-xs">{label}</span>
      <span className="text-white text-xs font-medium">{value}</span>
    </div>
  )
}

function ForecastBars({ base, bull, bear, currency }) {
  if (!base && !bull && !bear) return null
  const maxVal = Math.max(base || 0, bull || 0, bear || 0)
  const bar = (val, color) => {
    if (!val || !maxVal) return null
    const pct = Math.round((val / maxVal) * 100)
    return (
      <div className="flex items-center gap-2">
        <div className="flex-1 h-5 rounded bg-white/[0.04] overflow-hidden">
          <div
            className="h-full rounded transition-all duration-700"
            style={{ width: `${pct}%`, background: color }}
          />
        </div>
        <span className="text-xs font-medium w-28 text-right" style={{ color }}>{fmt(val, currency)}</span>
      </div>
    )
  }
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-1">
        <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">12-Month Revenue Forecast</div>
      </div>
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-emerald-400 w-10">BULL</span>
          {bar(bull, '#22c55e')}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-gold w-10">BASE</span>
          {bar(base, '#C9A84C')}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-red-400 w-10">BEAR</span>
          {bar(bear, '#ef4444')}
        </div>
      </div>
    </div>
  )
}

function Assumptions({ assumptions }) {
  if (!assumptions?.length) return null
  return (
    <div>
      <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Forecast Assumptions</div>
      <ul className="space-y-1">
        {assumptions.map((a, i) => (
          <li key={i} className="text-xs text-slate-400 flex items-start gap-2">
            <span className="text-gold/60 mt-px flex-shrink-0">→</span>
            <span>{a}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function ValuationPanel({ report }) {
  const cur = report?.currency || 'ZAR'
  const val = {
    low:    report?.valuation_low    || 0,
    mid:    report?.valuation_mid    || 0,
    high:   report?.valuation_high   || 0,
    method: report?.valuation_method || '',
  }
  const forecast = {
    base:        report?.forecast_base_12m    || 0,
    bull:        report?.forecast_bull_12m    || 0,
    bear:        report?.forecast_bear_12m    || 0,
    assumptions: report?.forecast_assumptions || [],
  }

  if (!val.mid && !forecast.base) return null

  return (
    <div className="space-y-6">
      {/* Valuation card */}
      {val.mid > 0 && (
        <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-6">
          <div className="text-white font-bold text-sm mb-1">Business Valuation Range</div>
          <div className="text-slate-500 text-xs mb-5">
            Mid-point: <span className="text-gold font-bold">{fmt(val.mid, cur)}</span>
          </div>
          <ValuationBar low={val.low} mid={val.mid} high={val.high} currency={cur} />
          {val.method && (
            <div className="mt-4 pt-4 border-t border-white/[0.06] space-y-0.5">
              <MethodRow label="Valuation Method" value={val.method} />
            </div>
          )}
          <p className="text-slate-600 text-xs mt-4 leading-relaxed italic">
            Indicative only. Engage a registered Business Valuator (SAVCA/SAICA) for a formal opinion.
          </p>
        </div>
      )}

      {/* Forecast card */}
      {(forecast.base > 0 || forecast.bull > 0 || forecast.bear > 0) && (
        <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-6">
          <ForecastBars
            base={forecast.base}
            bull={forecast.bull}
            bear={forecast.bear}
            currency={cur}
          />
          {forecast.assumptions.length > 0 && (
            <div className="mt-4 pt-4 border-t border-white/[0.06]">
              <Assumptions assumptions={forecast.assumptions} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
