import InfoTip from './InfoTip'

const ELIGIBLE = {
  likely: { c: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10', t: 'Likely eligible' },
  possibly: { c: 'text-amber-300 border-amber-500/30 bg-amber-500/10', t: 'Possibly eligible' },
  review: { c: 'text-slate-300 border-slate-500/25 bg-slate-500/10', t: 'To review' },
}

function money(n, cur = 'ZAR') {
  if (n == null) return '—'
  const s = n < 0 ? '-' : ''; const a = Math.abs(n)
  if (a >= 1e6) return `${s}${cur} ${(a / 1e6).toFixed(2)}M`
  if (a >= 1e3) return `${s}${cur} ${(a / 1e3).toFixed(0)}K`
  return `${s}${cur} ${a.toFixed(0)}`
}

export default function TaxOptimisation({ report, currency = 'ZAR' }) {
  const tx = report.tax_optimization
  if (!tx?.available) return null
  const cur = tx.currency || currency

  return (
    <div className="space-y-5">
      <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5">
        <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1 flex items-center gap-1.5">
          Estimated annual tax saving (legal reliefs)
          <InfoTip label="Tax Me If You Can" text="Legitimate SA reliefs you may QUALIFY for but could be missing — computed deterministically from your figures and the dated SARS rate corpus. Compliance-positive, GAAR-respecting legal planning only — not avoidance, and not tax advice. Confirm eligibility and current rates with a registered tax practitioner. Does not change the Imara Score." />
        </div>
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className="text-3xl font-bold text-emerald-400">{money(tx.total_saving_high, cur)}</span>
          <span className="text-sm text-slate-400">/ year confirmed-quantifiable{tx.quantified_count ? ` · ${tx.quantified_count} quantified relief${tx.quantified_count === 1 ? '' : 's'}` : ''}</span>
        </div>
        <p className="text-slate-500 text-xs mt-1">{tx.summary}</p>
        <p className="text-slate-600 text-[11px] mt-1">Rates as of {tx.as_of} · SBC table {tx.sbc_tax_year}.</p>
      </div>

      <div className="space-y-2">
        {tx.opportunities.map((o, i) => {
          const el = ELIGIBLE[o.eligible] || ELIGIBLE.review
          return (
            <div key={i} className="bg-navy-card border border-white/[0.08] rounded-xl p-4">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <span className="text-white text-sm font-medium">{o.name}</span>
                <div className="flex items-center gap-3 text-xs">
                  <span className={`rounded-full px-2 py-0.5 border ${el.c}`}>{el.t}</span>
                  {o.quantified
                    ? <span className="text-emerald-400 font-semibold">save {money(o.est_saving_high, cur)}</span>
                    : (o.est_saving_high > 0
                        ? <span className="text-amber-300/80">up to {money(o.est_saving_high, cur)} <span className="text-slate-500">(unconfirmed)</span></span>
                        : <span className="text-slate-500">potential</span>)}
                </div>
              </div>
              <p className="mt-1.5 text-xs text-slate-300 leading-relaxed">{o.basis}</p>
              <div className="mt-1 text-[11px] text-slate-400"><span className="text-slate-500">Action:</span> {o.action}</div>
              {o.caveat && <div className="mt-0.5 text-[11px] text-slate-600 italic">{o.caveat}</div>}
            </div>
          )
        })}
      </div>

      <p className="text-slate-600 text-[11px] italic leading-relaxed">{tx.disclaimer}</p>
    </div>
  )
}
