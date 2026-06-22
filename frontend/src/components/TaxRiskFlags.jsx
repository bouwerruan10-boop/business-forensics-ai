import InfoTip from './InfoTip'

// The mirror of TaxOptimisation: structural patterns that can attract SARS / GAAR
// scrutiny. Risk-AWARENESS only — never an accusation. Renders report.tax_risk_flags.
const SEV = {
  high: { dot: 'bg-red-400', chip: 'text-red-300 border-red-500/30 bg-red-500/10', t: 'High' },
  medium: { dot: 'bg-amber-400', chip: 'text-amber-300 border-amber-500/30 bg-amber-500/10', t: 'Medium' },
  low: { dot: 'bg-slate-400', chip: 'text-slate-300 border-slate-500/25 bg-slate-500/10', t: 'Low' },
}

const BAND = {
  high: 'text-red-400',
  medium: 'text-amber-300',
  low: 'text-slate-300',
  none: 'text-emerald-400',
}

export default function TaxRiskFlags({ report }) {
  const rk = report.tax_risk_flags
  if (!rk?.available) return null
  const band = rk.risk_band || 'none'
  const flags = rk.flags || []

  return (
    <div className="space-y-5">
      <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5">
        <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1 flex items-center gap-1.5">
          Structural tax-risk band
          <InfoTip label="GAAR &amp; SARS Scrutiny" text="Structural patterns that commonly attract SARS audit selection or the General Anti-Avoidance Rule (Income Tax Act ss 80A-80L). These are risk-AWARENESS flags to manage with commercial substance and documentation — NOT findings of wrongdoing, and not legal/tax advice. Detected deterministically from your figures and documents. Confirm your position with a registered tax practitioner." />
        </div>
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className={`text-3xl font-bold uppercase ${BAND[band] || BAND.none}`}>{band}</span>
          <span className="text-sm text-slate-400">{rk.flag_count ? `· ${rk.flag_count} flag${rk.flag_count === 1 ? '' : 's'}` : ''}</span>
        </div>
        <p className="text-slate-500 text-xs mt-1">{rk.summary}</p>
      </div>

      {flags.length > 0 && (
        <div className="space-y-2">
          {flags.map((f, i) => {
            const sv = SEV[f.severity] || SEV.low
            return (
              <div key={i} className="bg-navy-card border border-white/[0.08] rounded-xl p-4">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <span className="text-white text-sm font-medium flex items-center gap-2">
                    <span className={`inline-block w-2 h-2 rounded-full ${sv.dot}`} />
                    {f.title}
                  </span>
                  <span className={`rounded-full px-2 py-0.5 border text-xs ${sv.chip}`}>{sv.t}</span>
                </div>
                <p className="mt-1.5 text-xs text-slate-300 leading-relaxed">{f.detail}</p>
                <div className="mt-1 text-[11px] text-slate-400"><span className="text-slate-500">Basis:</span> {f.basis}</div>
                <div className="mt-0.5 text-[11px] text-slate-400"><span className="text-slate-500">Action:</span> {f.action}</div>
              </div>
            )
          })}
        </div>
      )}

      <p className="text-slate-600 text-[11px] italic leading-relaxed">{rk.disclaimer}</p>
    </div>
  )
}
