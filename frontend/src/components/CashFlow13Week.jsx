import { useEffect, useState } from 'react'
import InfoTip from './InfoTip'

function money(n, cur = 'ZAR') {
  if (n == null) return '—'
  const s = n < 0 ? '-' : ''; const a = Math.abs(n)
  if (a >= 1e6) return `${s}${cur} ${(a / 1e6).toFixed(2)}M`
  if (a >= 1e3) return `${s}${cur} ${(a / 1e3).toFixed(0)}K`
  return `${s}${cur} ${a.toFixed(0)}`
}

export default function CashFlow13Week({ analysisId, currency = 'ZAR' }) {
  const [cf, setCf] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let on = true
    import('../api/client').then(({ getCashflow }) => {
      getCashflow(analysisId).then(d => { if (on) setCf(d) }).catch(e => { if (on) setError(e.message) })
    })
    return () => { on = false }
  }, [analysisId])

  if (error) return <div className="text-slate-600 text-sm">13-week cash flow unavailable: {error}</div>
  if (!cf) return <div className="text-slate-500 text-sm">Projecting the next 13 weeks…</div>
  if (!cf.available) return <div className="text-slate-500 text-sm">{cf.reason || 'Needs revenue and operating profit to project.'}</div>

  const weeks = cf.weeks || []
  const closings = weeks.map(w => w.closing)
  const maxAbs = Math.max(1, ...closings.map(v => Math.abs(v)), Math.abs(cf.opening_cash || 0))
  const neg = cf.goes_negative

  return (
    <div className="space-y-5">
      {/* Verdict */}
      <div className={`rounded-2xl border p-5 ${neg ? 'bg-red-500/10 border-red-500/25' : 'bg-emerald-500/10 border-emerald-500/25'}`}>
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-slate-400 mb-1">
          Short-term liquidity — next 13 weeks
          <InfoTip label="13-week cash flow" text="The direct-method 13-week forecast is the SME survival tool: it shows when cash gets tight, which the annual P&L hides. Modelled from your run-rate plus the lumpy cash events (loan instalments, VAT). Indicative, and not part of the Imara Score." />
        </div>
        <div className="text-2xl font-bold text-white">
          {neg
            ? <span className="text-red-400">Cash runs short in week {cf.negative_week}</span>
            : <span className="text-emerald-400">Cash stays positive for 13 weeks</span>}
        </div>
        <p className="text-slate-300 text-sm mt-1.5 leading-relaxed">
          Low point <span className="font-semibold text-white">{money(cf.min_balance, currency)}</span> in week {cf.min_week};
          ending cash <span className="font-semibold text-white">{money(cf.ending_cash, currency)}</span>.
        </p>
      </div>

      {/* Stat row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat label="Opening cash" v={money(cf.opening_cash, currency)} sub={cf.opening_known ? 'proxy' : 'unknown — from 0'} />
        <Stat label="Weekly operating net" v={money(cf.weekly_operating_net, currency)} warn={cf.weekly_operating_net < 0} />
        {cf.debt_service_monthly > 0 && <Stat label="Monthly loan instalment" v={money(cf.debt_service_monthly, currency)} />}
        {cf.vat_remittance > 0 && <Stat label="VAT remittance (bi-monthly)" v={money(cf.vat_remittance, currency)} />}
      </div>

      {/* Trajectory bars */}
      <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5">
        <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-3">Closing cash balance by week</div>
        <div className="flex items-end gap-1.5 h-40 border-b border-white/10 relative">
          {weeks.map((w) => {
            const h = Math.round(Math.abs(w.closing) / maxAbs * 70)
            const lump = (w.lumps || []).length > 0
            return (
              <div key={w.week} className="flex-1 flex flex-col items-center justify-end h-full group relative">
                <div
                  className={`w-full rounded-t ${w.closing < 0 ? 'bg-red-500/70' : 'bg-emerald-500/60'} ${lump ? 'ring-1 ring-amber-400/60' : ''}`}
                  style={{ height: `${Math.max(4, h)}%` }}
                  title={`Week ${w.week}: ${money(w.closing, currency)}${lump ? ' • ' + w.lumps.map(l => l.label).join(', ') : ''}`}
                />
                <span className="text-[9px] text-slate-600 mt-1">{w.week}</span>
              </div>
            )
          })}
        </div>
        <div className="flex items-center gap-4 mt-3 text-[10px] text-slate-500">
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-emerald-500/60 inline-block" /> positive</span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-red-500/70 inline-block" /> negative</span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm ring-1 ring-amber-400/60 inline-block" /> loan / VAT outflow week</span>
        </div>
      </div>

      {/* Assumptions */}
      {Array.isArray(cf.assumptions) && (
        <details className="bg-navy-card border border-white/[0.08] rounded-xl p-4">
          <summary className="text-[11px] uppercase tracking-wider text-slate-400 cursor-pointer">Model assumptions</summary>
          <ul className="mt-2 space-y-1.5">
            {cf.assumptions.map((a, i) => (
              <li key={i} className="text-slate-400 text-xs leading-relaxed flex gap-2"><span className="text-slate-600">•</span>{a}</li>
            ))}
          </ul>
        </details>
      )}

      <p className="text-slate-600 text-[11px] leading-relaxed italic">
        This is the liquidity horizon — the short-term cash view that complements the 12-month strategic forecast. Indicative, built from annual figures rather than a transaction-level cash ledger.
      </p>
    </div>
  )
}

function Stat({ label, v, sub, warn }) {
  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-xl p-3">
      <div className="text-slate-400 text-[11px] mb-1">{label}</div>
      <div className={`text-sm font-bold ${warn ? 'text-amber-400' : 'text-white'}`}>{v}</div>
      {sub && <div className="text-slate-600 text-[10px] mt-0.5">{sub}</div>}
    </div>
  )
}
