// Financial Fundamentals — deterministic ratios computed from the uploaded
// financials (arithmetic, not LLM-generated). Each metric is traceable to its
// source figures, so a lender can trust the numbers.
import { CheckCircle2, AlertTriangle, XCircle, MinusCircle } from 'lucide-react'
import InfoTip from './InfoTip'

function statusMeta(status) {
  if (status === 'good')     return { col: 'text-emerald-400', Icon: CheckCircle2, label: 'Good' }
  if (status === 'warning')  return { col: 'text-amber-400',   Icon: AlertTriangle, label: 'Warning' }
  if (status === 'critical') return { col: 'text-red-400',     Icon: XCircle,       label: 'Critical' }
  return { col: 'text-slate-300', Icon: MinusCircle, label: '—' }
}

export default function FinancialRatios({ report }) {
  if (!report) return null
  const ratios = report.financial_ratios && typeof report.financial_ratios === 'object'
    ? Object.values(report.financial_ratios) : []
  if (!ratios.length) return null
  const fund = report.financial_fundamentals_score

  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 sm:p-6">
      <div className="flex items-baseline justify-between mb-1 flex-wrap gap-2">
        <h3 className="text-white font-bold text-lg flex items-center gap-1.5">
          Financial Fundamentals
          <InfoTip label="Financial Fundamentals" text="Ratios calculated directly from your statements (arithmetic, not AI). The Benchmark column shows the typical level for your industry, so each value can be read in context." />
        </h3>
        {fund ? (
          <span className="text-slate-300 text-sm">
            Fundamentals score: <span className="text-gold font-semibold">{fund}/100</span>
          </span>
        ) : null}
      </div>
      <p className="text-slate-400 text-xs mb-4 leading-relaxed">
        Computed directly from your financial statements — arithmetic, not AI-generated.
        Each figure is traceable to its source line items.
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <caption className="sr-only">Financial ratios with value, industry benchmark, status and source figures</caption>
          <thead>
            <tr className="text-slate-400 text-[11px] uppercase tracking-wider border-b border-white/[0.08]">
              <th scope="col" className="text-left font-medium py-2 pr-3">Metric</th>
              <th scope="col" className="text-right font-medium py-2 px-3">Value</th>
              <th scope="col" className="text-right font-medium py-2 px-3">Benchmark</th>
              <th scope="col" className="text-left font-medium py-2 px-3">Status</th>
              <th scope="col" className="text-left font-medium py-2 pl-3 hidden md:table-cell">Source figures</th>
            </tr>
          </thead>
          <tbody>
            {ratios.map((r, i) => {
              const m = statusMeta(r.status)
              const val = r.value != null ? `${r.value}${r.unit || ''}` : '—'
              return (
                <tr key={i} className="border-b border-white/[0.04]">
                  <th scope="row" className="py-2 pr-3 text-white font-medium whitespace-nowrap text-left">{r.label}</th>
                  <td className={`py-2 px-3 text-right font-bold whitespace-nowrap ${m.col}`}>{val}</td>
                  <td className="py-2 px-3 text-right text-slate-300 whitespace-nowrap">{r.benchmark}</td>
                  <td className={`py-2 px-3 whitespace-nowrap ${m.col}`}>
                    <span className="inline-flex items-center gap-1">
                      <m.Icon size={13} aria-hidden="true" />
                      <span>{r.status ? r.status.charAt(0).toUpperCase() + r.status.slice(1) : '—'}</span>
                    </span>
                  </td>
                  <td className="py-2 pl-3 text-slate-500 text-xs hidden md:table-cell">{r.source}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
