import { useEffect, useState } from 'react'
import InfoTip from './InfoTip'

const RISK = {
  low:    { c: 'text-emerald-400', b: 'bg-emerald-500/10 border-emerald-500/25', t: 'Likely to progress' },
  medium: { c: 'text-amber-400',   b: 'bg-amber-500/10 border-amber-500/25',     t: 'Would hesitate' },
  high:   { c: 'text-red-400',     b: 'bg-red-500/10 border-red-500/25',         t: 'Likely to decline' },
}
const SEV = { high: 'text-red-400 border-red-500/30', medium: 'text-amber-400 border-amber-500/30', low: 'text-slate-300 border-white/15' }

function money(n, cur = 'ZAR') {
  if (n == null) return '—'
  const s = n < 0 ? '-' : ''; const a = Math.abs(n)
  if (a >= 1e6) return `${s}${cur} ${(a / 1e6).toFixed(2)}M`
  if (a >= 1e3) return `${s}${cur} ${(a / 1e3).toFixed(0)}K`
  return `${s}${cur} ${a.toFixed(0)}`
}

export default function LenderView({ analysisId, currency = 'ZAR' }) {
  const [lv, setLv] = useState(null)
  const [nm, setNm] = useState(null)
  const [cm, setCm] = useState(null)
  const [wcap, setWcap] = useState(null)
  const [error, setError] = useState(null)
  const [packUrl, setPackUrl] = useState(null)

  useEffect(() => {
    let on = true
    import('../api/client').then(({ getLenderView, getNormalization, getBankReadyPackUrl, getCreditMemo, getWorkingCapital }) => {
      getLenderView(analysisId).then(d => { if (on) setLv(d) }).catch(e => { if (on) setError(e.message) })
      getNormalization(analysisId).then(d => { if (on) setNm(d) }).catch(() => {})
      getCreditMemo(analysisId).then(d => { if (on) setCm(d) }).catch(() => {})
      getWorkingCapital(analysisId).then(d => { if (on) setWcap(d) }).catch(() => {})
      if (on) setPackUrl(getBankReadyPackUrl(analysisId))
    })
    return () => { on = false }
  }, [analysisId])

  if (error) return <div className="text-slate-600 text-sm">Lender view unavailable: {error}</div>
  if (!lv) return <div className="text-slate-500 text-sm">Loading the lender's-eye view…</div>
  if (!lv.available) return <div className="text-slate-500 text-sm">{lv.reason || 'Not computed for this analysis.'}</div>

  const r = RISK[lv.decline_risk] || RISK.medium
  const m = lv.cash_flow_metrics || {}
  const rec = lv.reconciliation || {}
  const bc = lv.borrowing_capacity || {}
  const wc = bc.working_capital_facility
  const tl = bc.term_loan

  return (
    <div className="space-y-5">
      {/* Decline-risk verdict */}
      <div className={`rounded-2xl border p-5 ${r.b}`}>
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-slate-400 mb-1">
          Would a lender fund this today?
          <InfoTip label="Decline risk" text="A deterministic read of how a lender would view this business on CASH-FLOW grounds (not your credit score) — built from your bank statements + financials. Decision-support, not a credit decision, and not part of the Imara Score." />
        </div>
        <div className="flex items-baseline gap-3">
          <span className={`text-2xl font-bold ${r.c}`}>{r.t}</span>
          <span className="text-slate-500 text-xs uppercase tracking-wide">decline risk: <span className={r.c}>{lv.decline_risk}</span></span>
        </div>
        <p className="text-slate-300 text-sm mt-1.5 leading-relaxed">{lv.verdict}</p>
        {packUrl && (
          <a href={packUrl} target="_blank" rel="noopener noreferrer"
             className="inline-flex items-center gap-1.5 mt-3 text-xs font-semibold bg-white/10 hover:bg-white/15 border border-white/15 rounded-lg px-3 py-1.5 text-white transition-colors">
            ⬇ Download Bank-Ready Pack (PDF)
          </a>
        )}
      </div>


      {/* 5 Cs of credit + DSCR — how a credit committee reads the file */}
      {cm?.available && (
        <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
            How a credit committee reads this — the 5 Cs + DSCR
            <InfoTip label="5 Cs of credit" text="Lenders assess Character, Capacity, Capital, Collateral and Conditions, with DSCR as the hard number (~1.25x target). Computed from your figures — decision-support, not a credit decision, not part of the Imara Score." />
          </div>
          <div className="flex items-baseline gap-3 mb-2 flex-wrap">
            <span className="text-slate-400 text-sm">DSCR</span>
            <span className={`text-2xl font-bold ${cm.dscr.status === 'pass' ? 'text-emerald-400' : cm.dscr.status === 'watch' ? 'text-amber-400' : cm.dscr.status === 'fail' ? 'text-red-400' : 'text-slate-400'}`}>{cm.dscr.value != null ? `${cm.dscr.value}x` : '—'}</span>
            <span className="text-slate-500 text-xs">target ~{cm.dscr.target}x</span>
          </div>
          <p className="text-slate-500 text-[11px] mb-3 leading-relaxed">{cm.dscr.basis}</p>
          <div className="space-y-2">
            {cm.five_cs.map((c, i) => {
              const col = c.status === 'pass' ? 'text-emerald-400 border-emerald-500/30' : c.status === 'watch' ? 'text-amber-400 border-amber-500/30' : c.status === 'fail' ? 'text-red-400 border-red-500/30' : 'text-slate-400 border-white/15'
              return (
                <div key={i} className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3">
                  <div className="flex items-start justify-between gap-3">
                    <span className="text-white text-sm font-semibold">{c.c}</span>
                    <span className={`shrink-0 text-[10px] uppercase font-bold border rounded-full px-2 py-0.5 ${col}`}>{c.status}</span>
                  </div>
                  <div className="text-slate-400 text-xs mt-1 leading-relaxed">{c.evidence}</div>
                  {c.fix && <div className="text-slate-500 text-xs mt-1"><span className="text-emerald-400/80 font-semibold">Fix: </span>{c.fix}</div>}
                </div>
              )
            })}
          </div>
          <p className="text-white text-sm font-medium mt-3">{cm.committee_read}</p>
        </div>
      )}

      {/* Reasons + fixes */}
      {Array.isArray(lv.reasons) && lv.reasons.length > 0 && (
        <div>
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-2">What's holding it back — and the fix</div>
          <div className="space-y-2">
            {lv.reasons.map((x, i) => (
              <div key={i} className="bg-navy-card border border-white/[0.08] rounded-xl p-3">
                <div className="flex items-start justify-between gap-3">
                  <span className="text-white text-sm font-medium">{x.issue}</span>
                  <span className={`shrink-0 text-[10px] uppercase font-bold border rounded-full px-2 py-0.5 ${SEV[x.severity] || SEV.low}`}>{x.severity}</span>
                </div>
                {x.fix && <div className="text-slate-400 text-xs mt-1 leading-relaxed"><span className="text-emerald-400/80 font-semibold">Fix: </span>{x.fix}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cash-flow conduct + reconciliation */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="bg-navy-card border border-white/[0.08] rounded-xl p-4">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
            Cash-flow conduct
            <InfoTip label="What lenders read" text="The signals lenders actually weigh: average balance, deposit consistency, bounced debit orders and overdraft use." />
          </div>
          <Row label="Average balance" v={money(m.average_daily_balance, currency)} />
          <Row label="Avg monthly deposits" v={money(m.average_monthly_deposits, currency)} />
          <Row label="Deposit consistency" v={m.deposit_consistency || '—'} warn={m.deposit_consistency && m.deposit_consistency !== 'consistent'} />
          <Row label="Returned debit orders" v={m.returned_debit_orders ?? '—'} warn={m.returned_debit_orders > 0} />
          <Row label="Months of history" v={m.period_months || '—'} />
        </div>
        <div className="bg-navy-card border border-white/[0.08] rounded-xl p-4">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
            Statements vs financials
            <InfoTip label="Reconciliation" text="Lenders decline when bank deposits tell a different story than the declared revenue. This reconciles your banked deposits against the income statement." />
          </div>
          {rec.available ? (
            <>
              <Row label="Declared revenue" v={money(rec.declared_revenue, currency)} />
              <Row label="Annualised deposits" v={money(rec.annualized_deposits, currency)} />
              <Row label="Gap" v={rec.gap_pct != null ? `${rec.gap_pct}%` : '—'} warn={rec.material} />
              <p className="text-slate-400 text-xs mt-2 leading-relaxed">{rec.interpretation}</p>
            </>
          ) : <p className="text-slate-500 text-xs">{rec.reason || 'Not enough data to reconcile.'}</p>}
        </div>
      </div>

      {/* Borrowing capacity */}
      {(wc || tl) && (
        <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
            Indicative borrowing capacity
            <InfoTip label="Indicative only" text="A rough, indicative range of what this business could plausibly support — lenders vary widely. Not an offer." />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {wc && (
              <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3">
                <div className="text-slate-400 text-xs mb-1">Working-capital facility</div>
                <div className="text-white font-bold">{money(wc.low, currency)} – {money(wc.high, currency)}</div>
                <div className="text-slate-600 text-[11px] mt-1">{wc.basis}</div>
              </div>
            )}
            {tl && (
              <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3">
                <div className="text-slate-400 text-xs mb-1">Term loan (indicative principal)</div>
                <div className="text-white font-bold">{money(tl.implied_principal_low, currency)} – {money(tl.implied_principal_high, currency)}</div>
                <div className="text-slate-600 text-[11px] mt-1">{tl.basis}</div>
              </div>
            )}
          </div>
          {bc.assumptions && <p className="text-slate-600 text-[11px] mt-3 italic">{bc.assumptions}</p>}
        </div>
      )}


      {/* Working-capital cycle & trapped cash */}
      {wcap?.available && (
        <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
            Working-capital cycle & trapped cash
            <InfoTip label="Cash conversion cycle" text="Days from paying for stock to collecting cash — lower is better. We also estimate the cash freed by reaching sector-benchmark inventory/debtor days: the working capital a facility provides, without the debt." />
          </div>
          <div className="flex items-baseline gap-3 mb-3 flex-wrap">
            <span className="text-slate-400 text-sm">Cash conversion cycle</span>
            <span className={`text-2xl font-bold ${wcap.cash_conversion_cycle.status === 'good' ? 'text-emerald-400' : wcap.cash_conversion_cycle.status === 'warning' ? 'text-amber-400' : wcap.cash_conversion_cycle.status === 'critical' ? 'text-red-400' : 'text-slate-400'}`}>{wcap.cash_conversion_cycle.value} days</span>
            {wcap.cash_conversion_cycle.benchmark != null && <span className="text-slate-500 text-xs">sector ~{wcap.cash_conversion_cycle.benchmark} days</span>}
          </div>
          {wcap.working_capital_release.total > 0 ? (
            <div className="bg-emerald-500/5 border border-emerald-500/25 rounded-xl p-3">
              <div className="text-emerald-400 font-bold text-lg">≈ {money(wcap.working_capital_release.total, currency)} trapped above sector norms</div>
              <div className="text-slate-400 text-xs mt-1 mb-2">{wcap.working_capital_release.basis}</div>
              {wcap.working_capital_release.items.map((it, i) => (
                <div key={i} className="text-xs text-slate-300 mt-1.5">
                  <span className="text-white font-semibold">{it.driver}:</span> {it.excess_days} days over benchmark → {money(it.amount, currency)}
                  <div className="text-slate-500"><span className="text-emerald-400/80 font-semibold">Fix: </span>{it.fix}</div>
                </div>
              ))}
            </div>
          ) : <p className="text-slate-400 text-xs">{wcap.working_capital_release.basis}</p>}
        </div>
      )}

      {/* Adjusted EBITDA (tax-books vs deal/loan-books) */}
      {nm && nm.available && (
        <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
            True earning power — Adjusted EBITDA
            <InfoTip label="Deal/loan-book view" text="Tax-optimised books understate true earnings. Adding back owner-personal and one-off costs gives the normalised (Adjusted EBITDA / SDE) figure buyers and banks actually assess. Indicative — confirm the owner-personal portion." />
          </div>
          <div className="flex items-baseline gap-3 flex-wrap">
            <span className="text-slate-400 text-sm">Reported EBITDA <span className="text-white font-semibold">{money(nm.reported_ebitda, currency)}</span></span>
            <span className="text-slate-500">→</span>
            <span className="text-emerald-400 font-bold text-lg">{money(nm.adjusted_ebitda_low, currency)} – {money(nm.adjusted_ebitda_high, currency)}</span>
          </div>
          {Array.isArray(nm.add_backs) && nm.add_backs.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {nm.add_backs.map((a, i) => (
                <span key={i} className="text-[11px] bg-white/[0.04] border border-white/10 rounded-full px-2.5 py-1 text-slate-300">
                  +{a.label}: <span className="text-white font-semibold">{money(a.amount, currency)}</span>
                </span>
              ))}
            </div>
          )}
          {nm.loan_account_flag?.flagged && (
            <div className="mt-3 bg-amber-500/5 border border-amber-500/25 rounded-xl px-3 py-2 text-xs text-amber-300 leading-relaxed">
              ⚠ {nm.loan_account_flag.detail} <span className="text-amber-200 font-semibold">Fix:</span> {nm.loan_account_flag.fix}
            </div>
          )}
        </div>
      )}

      <p className="text-slate-600 text-[11px] leading-relaxed italic">{lv.note}</p>
    </div>
  )
}

function Row({ label, v, warn }) {
  return (
    <div className="flex items-center justify-between py-1 border-b border-white/[0.04] last:border-0">
      <span className="text-slate-400 text-xs">{label}</span>
      <span className={`text-sm font-semibold ${warn ? 'text-amber-400' : 'text-white'}`}>{v}</span>
    </div>
  )
}
