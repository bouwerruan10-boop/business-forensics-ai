import { useState } from 'react'
import { simulate } from '../api/client'

const SCENARIOS = [
  { label: 'Price increase +5%', variable: 'revenue', change: 5 },
  { label: 'Price increase +10%', variable: 'revenue', change: 10 },
  { label: 'Revenue growth +15%', variable: 'revenue', change: 15 },
  { label: 'Labour cost -10%', variable: 'labor_cost', change: -10 },
  { label: 'Labour cost -20%', variable: 'labor_cost', change: -20 },
  { label: 'Fuel cost +20%', variable: 'fuel_cost', change: 20 },
  { label: 'Fuel cost -15%', variable: 'fuel_cost', change: -15 },
]

function fmt(n, cur) {
  if (!n && n !== 0) return '—'
  const abs = Math.abs(n)
  const sign = n >= 0 ? '+' : '-'
  if (abs >= 1_000_000) return `${sign}${cur} ${(abs / 1_000_000).toFixed(2)}M`
  if (abs >= 1_000) return `${sign}${cur} ${(abs / 1_000).toFixed(0)}K`
  return `${sign}${cur} ${abs.toFixed(0)}`
}

export default function Simulator({ analysisId, currency = 'ZAR' }) {
  const [selected, setSelected] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const runScenario = async (scenario) => {
    setSelected(scenario.label)
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const r = await simulate(analysisId, scenario.variable, scenario.change, scenario.label)
      setResult(r)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const profitImpact = result?.profit_impact ?? result?.estimated_profit_impact ?? result?.annual_saving ?? null

  return (
    <div>
      <p className="text-slate-400 text-sm mb-4">
        Model what-if scenarios using your actual revenue and industry benchmark cost ratios.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
        {SCENARIOS.map(s => (
          <button
            key={s.label}
            onClick={() => runScenario(s)}
            className={`text-left px-4 py-3 rounded-xl border text-sm transition-all ${
              selected === s.label
                ? 'border-gold/40 bg-gold/10 text-gold'
                : 'border-white/10 bg-navy-card text-slate-400 hover:border-white/20 hover:text-white'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {loading && (
        <div className="text-center py-6">
          <div className="flex justify-center gap-1 mb-2">
            <span className="pulse-dot w-2 h-2 rounded-full bg-gold inline-block" />
            <span className="pulse-dot pulse-dot-2 w-2 h-2 rounded-full bg-gold inline-block" />
            <span className="pulse-dot pulse-dot-3 w-2 h-2 rounded-full bg-gold inline-block" />
          </div>
          <p className="text-slate-500 text-sm">Modelling scenario...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">{error}</div>
      )}

      {result && !loading && (
        <div className="bg-navy-card border border-gold/20 rounded-2xl p-5 fade-in">
          <div className="text-gold text-xs font-bold tracking-wider mb-3">{result.scenario}</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            {result.projected_revenue != null && (
              <div>
                <div className="text-slate-500 text-xs mb-0.5">Projected Revenue</div>
                <div className="text-white font-semibold text-sm">
                  {currency} {result.projected_revenue?.toLocaleString()}
                </div>
              </div>
            )}
            {profitImpact != null && (
              <div>
                <div className="text-slate-500 text-xs mb-0.5">Profit Impact</div>
                <div className={`font-bold text-sm ${profitImpact >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {fmt(profitImpact, currency)}
                </div>
              </div>
            )}
            {result.revenue_delta != null && (
              <div>
                <div className="text-slate-500 text-xs mb-0.5">Revenue Delta</div>
                <div className={`font-semibold text-sm ${result.revenue_delta >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {fmt(result.revenue_delta, currency)}
                </div>
              </div>
            )}
          </div>
          {result.note && (
            <p className="text-slate-600 text-xs mt-3 border-t border-white/[0.06] pt-3">{result.note}</p>
          )}
        </div>
      )}
    </div>
  )
}
