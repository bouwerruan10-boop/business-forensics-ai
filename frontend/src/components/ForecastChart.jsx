// Lazy-loaded forecast chart — isolates the heavy Recharts/D3 bundle into its own
// async chunk so it only downloads when a report with a forecast is shown.
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import InfoTip from './InfoTip'

function fmt(v, cur) {
  if (!v) return '—'
  if (v >= 1_000_000_000) return `${cur} ${(v / 1_000_000_000).toFixed(2)}B`
  if (v >= 1_000_000)     return `${cur} ${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000)         return `${cur} ${(v / 1_000).toFixed(0)}K`
  return `${cur} ${v.toFixed(0)}`
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

export default function ForecastChart({ start, base, bull, bear, currency }) {
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
