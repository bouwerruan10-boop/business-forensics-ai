// Valuation & Forecast Panel — three-point valuation bar + 12m forecast chart
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import InfoTip from './InfoTip'

function fmt(v, cur) {
  if (!v) return '—'
  if (v >= 1_000_000_000) return `${cur} ${(v / 1_000_000_000).toFixed(2)}B`
  if (v >= 1_000_000)     return `${cur} ${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000)         return `${cur} ${(v / 1_000).toFixed(0)}K`
  return `${cur} ${v.toFixed(0)}`
}

function ValuationBar({ low, mid, high, currency }) {
  if (!mid) return null
  const points = [
    { label: 'BEAR', val: low,  x: 10,  color: '#ef4444' },
    { label: 'BASE', val: mid,  x: 50,  color: '#C9A84C' },
    { label: 'BULL', val: high, x: 90,  color: '#22c55e' },
  ]
  return (
    <div className="py-2" role="img" aria-label={`Valuation range: bear ${fmt(low, currency)}, base ${fmt(mid, currency)}, bull ${fmt(high, currency)}.`}>
      <div className="relative h-2 rounded-full bg-white/[0.06] mb-8" aria-hidden="true">
        <div className="absolute inset-0 rounded-full bg-gradient-to-r from-red-500/40 via-gold/40 to-emerald-500/40" />
        {points.map(p => (
          <div key={p.label} style={{ left: `${p.x}%` }} className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2">
            <div className="w-4 h-4 rounded-full border-2 border-[#0D1B2A]" style={{ background: p.color }} />
          </div>
        ))}
      </div>
      <div className="flex justify-between" aria-hidden="true">
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
      <span className="text-slate-400 text-xs">{label}</span>
      <span className="text-white text-xs font-medium">{value}</span>
    </div>
  )
}

// 12-month revenue trajectory: linear path from today's revenue to each scenario.
function buildSeries(start, base, bull, bear) {
  const data = []
  for (let m = 0; m <= 12; m++) {
    const t = m / 12
    data.push({
      month: m,
      Bull: bull ? Math.round(start + (bull - start) * t) : null,
      Base: base ? Math.round(start + (base - start) * t) : null,
      Bear: bear ? Math.round(start + (bear - start) * t) : null,
    })
  }
  return data
}

function ForecastChart({ start, base, bull, bear, currency }) {
  if (!base && !bull && !bear) return null
  const data = buildSeries(start, base, bull, bear)
  const compact = v => {
    if (v == null) return ''
    if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
    if (Math.abs(v) >= 1_000) return `${Math.round(v / 1_000)}K`
    return `${v}`
  }
  const summary = `12-month revenue forecast from ${fmt(start, currency)} today to: bull ${fmt(bull, currency)}, base ${fmt(base, currency)}, bear ${fmt(bear, currency)}.`
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
          12-Month Revenue Forecast
          <InfoTip label="Forecast" text="Projected revenue path from today to month 12 under three scenarios. Bull = optimistic, Base = expected, Bear = pessimistic. Lines interpolate from your current revenue to each scenario's 12-month target." />
        </div>
      </div>

      {/* Chart is decorative-for-AT; the labelled summary + legend carry the data. */}
      <p className="sr-only">{summary}</p>
      <div className="h-44 -ml-2" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 6, right: 10, bottom: 0, left: 0 }}>
            <XAxis dataKey="month" tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                   ticks={[0, 3, 6, 9, 12]} tickFormatter={m => `M${m}`} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} axisLine={false} width={44} tickFormatter={compact} />
            <Tooltip
              contentStyle={{ background: '#111827', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: '#94a3b8' }} labelFormatter={m => `Month ${m}`}
              formatter={(v, n) => [fmt(v, currency), n]} />
            <ReferenceLine y={start} stroke="rgba(255,255,255,0.18)" strokeDasharray="3 3" />
            <Line type="monotone" dataKey="Bull" stroke="#22c55e" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="Base" stroke="#C9A84C" strokeWidth={2.5} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="Bear" stroke="#ef4444" strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Legend doubles as the accessible value readout */}
      <div className="grid grid-cols-3 gap-2">
        {[['BULL', bull, '#22c55e'], ['BASE', base, '#C9A84C'], ['BEAR', bear, '#ef4444']].map(([k, v, col]) => (
          <div key={k} className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-2 py-1.5 text-center">
            <div className="text-[10px] font-black uppercase tracking-widest" style={{ color: col }}>{k}</div>
            <div className="text-white text-xs font-bold">{fmt(v, currency)}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function Assumptions({ assumptions }) {
  if (!assumptions?.length) return null
  return (
    <div>
      <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Forecast Assumptions</div>
      <ul className="space-y-1">
        {assumptions.map((a, i) => (
          <li key={i} className="text-xs text-slate-300 flex items-start gap-2">
            <span className="text-gold/60 mt-px flex-shrink-0" aria-hidden="true">→</span>
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
  // Start the trajectory from current revenue (fallback: lowest scenario).
  const start = report?.annual_revenue || Math.min(...[forecast.base, forecast.bull, forecast.bear].filter(Boolean), 0) || 0

  if (!val.mid && !forecast.base) return null

  return (
    <div className="space-y-6">
      {val.mid > 0 && (
        <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-6">
          <div className="text-white font-bold text-sm mb-1 flex items-center gap-1.5">
            Business Valuation Range
            <InfoTip label="Valuation range" text="An indicative value for the business. Bear is conservative, Base is the central estimate, Bull is optimistic. Use a registered valuator for a formal opinion." />
          </div>
          <div className="text-slate-400 text-xs mb-5">
            Mid-point: <span className="text-gold font-bold">{fmt(val.mid, cur)}</span>
          </div>
          <ValuationBar low={val.low} mid={val.mid} high={val.high} currency={cur} />
          {val.method && (
            <div className="mt-4 pt-4 border-t border-white/[0.06] space-y-0.5">
              <MethodRow label="Valuation Method" value={val.method} />
            </div>
          )}
          <p className="text-slate-500 text-xs mt-4 leading-relaxed italic">
            Indicative only. Engage a registered Business Valuator (SAVCA/SAICA) for a formal opinion.
          </p>
        </div>
      )}

      {(forecast.base > 0 || forecast.bull > 0 || forecast.bear > 0) && (
        <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-6">
          <ForecastChart start={start} base={forecast.base} bull={forecast.bull} bear={forecast.bear} currency={cur} />
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
