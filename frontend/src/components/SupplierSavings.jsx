import InfoTip from './InfoTip'

const STATUS = {
  above: { c: 'text-red-400', t: 'Above benchmark' },
  within: { c: 'text-slate-300', t: 'Within benchmark' },
  below: { c: 'text-emerald-400', t: 'Below benchmark' },
  no_benchmark: { c: 'text-slate-500', t: 'No benchmark band' },
}

function money(n, cur = 'ZAR') {
  if (n == null) return '—'
  const s = n < 0 ? '-' : ''; const a = Math.abs(n)
  if (a >= 1e6) return `${s}${cur} ${(a / 1e6).toFixed(2)}M`
  if (a >= 1e3) return `${s}${cur} ${(a / 1e3).toFixed(0)}K`
  return `${s}${cur} ${a.toFixed(0)}`
}

export default function SupplierSavings({ report, currency = 'ZAR' }) {
  const sb = report.supplier_benchmark
  if (!sb?.available) return null

  return (
    <div className="space-y-5">
      <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5">
        <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1 flex items-center gap-1.5">
          Estimated annual supplier savings
          <InfoTip label="Supplier savings" text="For each expense line, Imara compares your spend to a benchmark band and surfaces lower-cost suppliers at equivalent service. Savings are indicative ranges off your actual spend — verify current quotes. Decision-support; it does not change the Imara Score." />
        </div>
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className="text-3xl font-bold text-emerald-400">{money(sb.total_est_saving_low, currency)}–{money(sb.total_est_saving_high, currency)}</span>
          <span className="text-sm text-slate-400">/ year{sb.total_est_saving_pct_of_revenue != null ? ` · ${sb.total_est_saving_pct_of_revenue}% of revenue` : ''}</span>
        </div>
        <p className="text-slate-500 text-xs mt-1">Across {sb.total_expense_lines} expense line items. Acting on these maps to the "Switch to benchmarked lower-cost suppliers" lever in the Action Simulator.</p>
      </div>

      <div className="space-y-2">
        {sb.opportunities.map((o, i) => {
          const st = STATUS[o.status] || STATUS.no_benchmark
          const hasSaving = o.est_saving_low != null
          return (
            <div key={i} className="bg-navy-card border border-white/[0.08] rounded-xl p-4">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <span className="text-white text-sm font-medium">{o.label}</span>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-slate-400">{money(o.spend, currency)}{o.pct_of_revenue != null ? ` · ${o.pct_of_revenue}%` : ''}</span>
                  <span className={st.c}>{st.t}</span>
                  {hasSaving && <span className="text-emerald-400 font-semibold">save {money(o.est_saving_low, currency)}–{money(o.est_saving_high, currency)}</span>}
                </div>
              </div>
              {(o.alternatives || []).length > 0 && (
                <div className="mt-1.5 text-xs text-slate-400">
                  Lower-cost options: <span className="text-slate-300">{o.alternatives.join(' · ')}</span>
                  {o.incumbent && <span className="text-slate-500"> (vs {o.incumbent})</span>}
                </div>
              )}
              {o.equivalence && <div className="mt-1 text-[11px] text-slate-600 italic">Equivalence: {o.equivalence}</div>}
              {(o.live_pricing || []).length > 0 && (
                <div className="mt-1.5 space-y-0.5">
                  {o.live_pricing.map((lp, j) => (
                    <div key={j} className="text-[11px] text-amber-300">live · {lp.provider}: {lp.snippet} {lp.url && <a href={lp.url} target="_blank" rel="noreferrer" className="underline text-amber-400">source</a>}</div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
      <p className="text-slate-600 text-[11px] italic leading-relaxed">{sb.disclaimer}{sb.opportunities[0]?.source ? ` Reference: ${sb.opportunities[0].source}.` : ''}</p>
    </div>
  )
}
