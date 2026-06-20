import InfoTip from './InfoTip'

const ZONE = { safe: 'text-emerald-400', grey: 'text-amber-400', distress: 'text-red-400' }
const TIER = { strong: 'text-emerald-400', adequate: 'text-amber-400', weak: 'text-red-400' }

function money(n, cur = 'ZAR') {
  if (n == null) return '—'
  const s = n < 0 ? '-' : ''; const a = Math.abs(n)
  if (a >= 1e6) return `${s}${cur} ${(a / 1e6).toFixed(2)}M`
  if (a >= 1e3) return `${s}${cur} ${(a / 1e3).toFixed(0)}K`
  return `${s}${cur} ${a.toFixed(0)}`
}

function Stat({ label, value, bad }) {
  return (
    <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-2.5">
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`text-sm font-bold ${bad ? 'text-red-400' : 'text-white'}`}>{value == null ? '—' : value}</div>
    </div>
  )
}

export default function BankabilityEvidence({ report, currency = 'ZAR' }) {
  const z = report.distress_score
  const b = report.bank_signals
  const ds = report.decision_support

  return (
    <div className="space-y-5">
      {/* Independent distress cross-check (Altman Z'') */}
      {z?.available && (
        <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
            Independent distress cross-check
            <InfoTip label="Altman Z&Prime; (emerging markets)" text="A published, peer-reviewed bankruptcy-distress model computed purely by arithmetic from your balance sheet — independent of the Imara Score. When the two agree, that is convergent evidence the rating reads the business correctly." />
          </div>
          <div className="flex items-baseline gap-3 flex-wrap">
            <span className={`text-3xl font-bold ${ZONE[z.zone] || 'text-slate-300'}`}>{z.z_score}</span>
            <span className={`text-sm font-semibold ${ZONE[z.zone] || 'text-slate-400'}`}>{z.zone_label}</span>
            <span className="text-slate-500 text-xs">Altman Z&Prime; (emerging markets) · safe &gt; {z.thresholds.safe_above} · distress &lt; {z.thresholds.distress_below}</span>
          </div>
          {z.convergence?.statement && (
            <div className={`mt-2 text-xs ${z.convergence.agrees === false ? 'text-amber-300' : 'text-slate-400'}`}>{z.convergence.statement}</div>
          )}
        </div>
      )}

      {/* Bank-statement cash-flow signals */}
      {b?.available && (
        <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
            Bank-statement cash-flow signals
            <InfoTip label="Bank signals" text="Deterministic signals read from your bank statement — bounced debit orders, overdraft, debit-order load, cash-flow direction. For thin-file SMEs this is the strongest creditworthiness evidence. Decision-support only; it does not change the Imara Score." />
            <span className="text-slate-500 normal-case">health: <span className={`font-semibold ${TIER[b.bank_health_tier] || 'text-slate-300'}`}>{b.bank_health_score}/100 {b.bank_health_tier}</span></span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
            <Stat label="Returned debit orders" value={b.returned_debit_orders} bad={b.returned_debit_orders > 0} />
            <Stat label="Negative-balance rows" value={b.negative_balance_rows} bad={b.negative_balance_rows > 0} />
            <Stat label="Debit orders" value={b.debit_order_count} />
            <Stat label="Months of history" value={b.period_months} bad={b.period_months < 3} />
            <Stat label="Net cash flow" value={money(b.net_flow, currency)} bad={b.net_flow != null && b.net_flow < 0} />
            <Stat label="Min balance" value={money(b.min_balance, currency)} bad={b.min_balance != null && b.min_balance < 0} />
            <Stat label="Largest inflow" value={money(b.largest_inflow, currency)} />
            <Stat label="Largest outflow" value={money(b.largest_outflow, currency)} />
          </div>
          {(b.risk_drivers || []).length > 0 && (
            <ul className="space-y-1">
              {b.risk_drivers.map((d, i) => (<li key={i} className="text-xs text-red-300">• {d}</li>))}
            </ul>
          )}
          {(b.strengths || []).length > 0 && (
            <ul className="space-y-1 mt-1">
              {b.strengths.map((d, i) => (<li key={i} className="text-xs text-emerald-300">• {d}</li>))}
            </ul>
          )}
          <p className="text-slate-600 text-[11px] mt-3 italic leading-relaxed">{b.note}</p>
        </div>
      )}

      {/* Decision-support framing (NCA / fairness) */}
      {ds && (
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-2">How to use this · decision-support</div>
          <p className="text-slate-300 text-sm leading-relaxed">
            Imara is <span className="text-white font-medium">{ds.classification}</span> — <span className="text-slate-400">not {ds.is_not}</span>. {ds.intended_use}
          </p>
          <p className="text-slate-500 text-xs mt-2 leading-relaxed">{ds.nca}</p>
          {ds.fairness && <p className="text-slate-500 text-xs mt-1 leading-relaxed">{ds.fairness}</p>}
        </div>
      )}
    </div>
  )
}
