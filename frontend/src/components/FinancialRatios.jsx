// Financial Fundamentals — deterministic ratios computed from the uploaded
// financials (arithmetic, not LLM-generated). Each metric is traceable to its
// source figures, so a lender can trust the numbers.

function statusColor(status) {
  if (status === 'good') return 'text-emerald-400'
  if (status === 'warning') return 'text-amber-400'
  if (status === 'critical') return 'text-red-400'
  return 'text-slate-400'
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
        <h3 className="text-white font-bold text-lg">Financial Fundamentals</h3>
        {fund ? (
          <span className="text-slate-400 text-sm">
            Fundamentals score: <span className="text-gold font-semibold">{fund}/100</span>
          </span>
        ) : null}
      </div>
      <p className="text-slate-500 text-xs mb-4 leading-relaxed">
        Computed directly from your financial statements — arithmetic, not AI-generated.
        Each figure is traceable to its source line items.
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-500 text-[11px] uppercase tracking-wider border-b border-white/[0.08]">
              <th className="text-left font-medium py-2 pr-3">Metric</th>
              <th className="text-right font-medium py-2 px-3">Value</th>
              <th className="text-right font-medium py-2 px-3">Benchmark</th>
              <th className="text-left font-medium py-2 px-3">Status</th>
              <th className="text-left font-medium py-2 pl-3 hidden md:table-cell">Source figures</th>
            </tr>
          </thead>
          <tbody>
            {ratios.map((r, i) => {
              const col = statusColor(r.status)
              const val = r.value != null ? `${r.value}${r.unit || ''}` : '—'
              return (
                <tr key={i} className="border-b border-white/[0.04]">
                  <td className="py-2 pr-3 text-white font-medium whitespace-nowrap">{r.label}</td>
                  <td className={`py-2 px-3 text-right font-bold whitespace-nowrap ${col}`}>{val}</td>
                  <td className="py-2 px-3 text-right text-slate-400 whitespace-nowrap">{r.benchmark}</td>
                  <td className={`py-2 px-3 whitespace-nowrap ${col}`}>
                    <span className="mr-1">●</span>{r.status ? r.status.charAt(0).toUpperCase() + r.status.slice(1) : '—'}
                  </td>
                  <td className="py-2 pl-3 text-slate-600 text-xs hidden md:table-cell">{r.source}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
