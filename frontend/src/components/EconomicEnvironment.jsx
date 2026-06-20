import { useEffect, useState } from 'react'
import InfoTip from './InfoTip'

const EXP = {
  high:   'bg-red-500/10 text-red-400 border-red-500/25',
  medium: 'bg-amber-500/10 text-amber-400 border-amber-500/25',
  low:    'bg-emerald-500/10 text-emerald-400 border-emerald-500/25',
}
const RES = { fragile: 'text-red-400', moderate: 'text-amber-400', robust: 'text-emerald-400' }

function money(n, cur = 'ZAR') {
  if (n == null) return '—'
  const s = n < 0 ? '-' : ''; const a = Math.abs(n)
  if (a >= 1e6) return `${s}${cur} ${(a / 1e6).toFixed(2)}M`
  if (a >= 1e3) return `${s}${cur} ${(a / 1e3).toFixed(0)}K`
  return `${s}${cur} ${a.toFixed(0)}`
}

export default function EconomicEnvironment({ analysisId, currency = 'ZAR' }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let on = true
    import('../api/client').then(({ getMacro }) => getMacro(analysisId))
      .then(d => { if (on) setData(d) }).catch(e => { if (on) setError(e.message) })
    return () => { on = false }
  }, [analysisId])

  if (error) return <div className="text-slate-600 text-sm">Economic overlay unavailable: {error}</div>
  if (!data) return <div className="text-slate-500 text-sm">Loading economic environment…</div>

  const ind = data.snapshot?.indicators || {}
  const sens = data.sensitivity || {}
  const st = data.stress_test || {}
  const sc = Object.fromEntries((st.scenarios || []).map(s => [s.scenario, s]))

  return (
    <div className="space-y-5">
      {/* Macro snapshot */}
      <div>
        <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
          SA macro snapshot
          <span className="text-slate-600 normal-case">as of {data.snapshot?.as_of}</span>
          <InfoTip label="Macro snapshot" text="A dated snapshot of the key South African indicators. Figures are curated from SARB / Stats SA / World Bank — not live — and every number is dated for transparency." />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {Object.values(ind).map((v, i) => (
            <span key={i} className="text-[11px] bg-white/[0.04] border border-white/10 rounded-full px-2.5 py-1 text-slate-300">
              {v.label}: <span className="text-white font-semibold">{v.value}{v.unit === '%' ? '%' : v.unit === '%/yr' ? '%/yr' : ` ${v.unit}`}</span>
            </span>
          ))}
        </div>
      </div>

      {/* Firm exposure */}
      <div>
        <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
          This firm's macro exposure
          <InfoTip label="Exposure" text="Computed from your own statements (floating debt → rate sensitivity, cost base → inflation, energy-intensive opex → tariffs, FX-exposed inputs → the rand). Deterministic; the agent only narrates." />
          <span className="text-slate-500 normal-case">overall: <span className={`font-semibold ${sens.overall_exposure === 'high' ? 'text-red-400' : sens.overall_exposure === 'medium' ? 'text-amber-400' : 'text-emerald-400'}`}>{sens.overall_exposure}</span></span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {(sens.drivers || []).map((d, i) => (
            <div key={i} className="bg-navy-card border border-white/[0.08] rounded-xl p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-white text-sm font-medium">{d.driver}</span>
                <span className={`text-[10px] uppercase font-bold border rounded-full px-2 py-0.5 ${EXP[d.exposure] || EXP.low}`}>{d.exposure}</span>
              </div>
              <div className="text-slate-400 text-xs leading-relaxed">{d.note}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Macro stress test */}
      <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5">
        <div className="flex items-end justify-between mb-3 flex-wrap gap-2">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-1 flex items-center gap-1.5">
              Macro resilience
              <InfoTip label="Macro stress test" text="A probability-weighted stress test (base 50% / adverse 25% / upside 25%), each macro shock transmitted through your own cost, debt and demand structure. An overlay — it does not change your headline Imara Score." />
            </div>
            <div className="flex items-baseline gap-2">
              <span className={`text-3xl font-bold ${RES[st.macro_resilience_label] || 'text-slate-300'}`}>{st.macro_resilience}</span>
              <span className={`text-sm font-semibold ${RES[st.macro_resilience_label] || 'text-slate-400'}`}>{st.macro_resilience_label}</span>
            </div>
          </div>
          <div className="text-right">
            <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Expected net profit</div>
            <div className={`text-xl font-bold ${st.expected_net_profit < 0 ? 'text-red-400' : 'text-emerald-400'}`}>{money(st.expected_net_profit, currency)}</div>
          </div>
        </div>

        {st.flips_to_loss_under_adverse && (
          <div className="mb-3 bg-red-500/5 border border-red-500/25 rounded-xl px-3 py-2 text-xs text-red-300">
            ⚠ Under a plausible adverse macro scenario (higher rates + weaker rand + tariff hikes) this business <span className="font-semibold">flips into a loss</span>.
          </div>
        )}

        <div className="grid grid-cols-3 gap-2">
          {['Base', 'Adverse', 'Upside'].map(name => {
            const s = sc[name]; if (!s) return null
            const neg = s.net_profit < 0
            return (
              <div key={name} className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3 text-center">
                <div className="text-[11px] text-slate-400 mb-1">{name} <span className="text-slate-600">{Math.round(s.weight * 100)}%</span></div>
                <div className={`text-sm font-bold ${neg ? 'text-red-400' : 'text-white'}`}>{money(s.net_profit, currency)}</div>
                <div className="text-[11px] text-slate-500 mt-0.5">net · score {s.imara_score ?? '—'}</div>
              </div>
            )
          })}
        </div>
        <p className="text-slate-600 text-[11px] mt-3 leading-relaxed italic">{st.disclaimer}</p>
      </div>
    </div>
  )
}
