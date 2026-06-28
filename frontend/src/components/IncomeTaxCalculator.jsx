import { useState } from 'react'
import { getTaxIncome, getDisputeDeadlines, getSarsGuidance, getTaxAuditTrail } from '../api/client'

const rand = (n) => 'R ' + Math.round(Number(n) || 0).toLocaleString('en-ZA')
const numOrUndef = (v) => { const n = parseFloat(v); return !isNaN(n) && n > 0 ? n : undefined }

function NumField({ label, value, onChange, placeholder }) {
  return (
    <label className="text-xs text-slate-400">
      {label}
      <input type="number" min="0" inputMode="numeric" value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg bg-navy border border-white/10 px-2.5 py-1.5 text-sm text-white focus:border-gold/40 outline-none"
        placeholder={placeholder} />
    </label>
  )
}

function Row({ label, value, strong }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-white/5 last:border-0">
      <span className={strong ? 'text-sm text-white font-medium' : 'text-xs text-slate-400'}>{label}</span>
      <span className={strong ? 'text-sm text-white font-semibold' : 'text-sm text-slate-200'}>{value}</span>
    </div>
  )
}

function PositionBadge({ position }) {
  const map = {
    owing: 'border-red-400/40 text-red-300 bg-red-400/10',
    refund: 'border-emerald-400/40 text-emerald-300 bg-emerald-400/10',
    payable: 'border-red-400/40 text-red-300 bg-red-400/10',
    settled: 'border-white/15 text-slate-300 bg-white/5',
    nil: 'border-white/15 text-slate-300 bg-white/5',
  }
  return (
    <span className={`text-xs rounded-lg px-2.5 py-1 border ${map[position] || map.settled}`}>
      {position}
    </span>
  )
}

export default function IncomeTaxCalculator() {
  // IRP5-style income + deductions
  const [inc, setInc] = useState({
    salary: '', annual_payment: '', commission: '', overtime: '',
    travel_allowance: '', additional_income: '',
    travel_business_km: '', retirement_contribution: '', medical_members: '',
    paye_paid: '', age: '',
  })
  // VAT (optional)
  const [vat, setVat] = useState({
    standard_rated_incl: '', zero_rated: '', exempt: '',
    input_capital_incl: '', input_other_incl: '',
  })
  // ETI roster (optional)
  const [emps, setEmps] = useState([])
  const [etiYear, setEtiYear] = useState(1)
  const [prov, setProv] = useState({ estimate_taxable: '', latest_assessed_taxable: '', actual_taxable: '' })
  // Capital gains (optional)
  const [cgt, setCgt] = useState({ total_gains: '', total_losses: '', primary_residence_gain: '', other_taxable_income: '' })
  const [cgtTaxpayer, setCgtTaxpayer] = useState('individual')
  const [cgtDeath, setCgtDeath] = useState(false)
  // Fringe benefits (optional)
  const [fringe, setFringe] = useState({ car_determined_value: '', loan_amount: '', loan_interest_paid_pct: '', accommodation_remuneration_proxy: '' })
  const [carMaint, setCarMaint] = useState(false)
  // Lump sum (optional)
  const [lump, setLump] = useState({ amount: '', prior: '' })
  const [lumpKind, setLumpKind] = useState('retirement')
  // Assessed loss (optional)
  const [loss, setLossState] = useState({ taxable_income_before: '', balance_brought_forward: '' })
  const [lossTaxpayer, setLossTaxpayer] = useState('company')
  const [lossSuspect, setLossSuspect] = useState(false)
  // Cross-border (optional)
  const [resid, setResid] = useState({ current_year_days: '', p1: '', p2: '', p3: '', p4: '', p5: '', days_continuously_absent: '' })
  const [exitT, setExitT] = useState({ deemed_gains: '', other_taxable_income: '' })
  const [exitTaxpayer, setExitTaxpayer] = useState('individual')
  const [foreign, setForeign] = useState({ foreign_employment_income: '', days_outside_total: '', longest_continuous_days: '' })

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  // SARS dispute deadlines (independent lookup)
  const [disputeDate, setDisputeDate] = useState('')
  const [dispute, setDispute] = useState(null)
  const [disputeErr, setDisputeErr] = useState(null)

  const runDispute = async () => {
    setDisputeErr(null); setDispute(null)
    try {
      const r = await getDisputeDeadlines(disputeDate)
      if (!r.available) { setDisputeErr(r.reason || 'Enter the assessment date.'); return }
      setDispute(r)
    } catch (e) { setDisputeErr(e.message) }
  }

  // SARS process guidance (fetched once, lazily)
  const [guidance, setGuidance] = useState(null)
  const [openCard, setOpenCard] = useState(null)
  const loadGuidance = async () => {
    if (guidance) { setGuidance(null); return }   // toggle closed
    try { setGuidance(await getSarsGuidance()) } catch (e) { setDisputeErr(e.message) }
  }

  const setI = (k, v) => setInc((s) => ({ ...s, [k]: v }))
  const setV = (k, v) => setVat((s) => ({ ...s, [k]: v }))
  const addEmp = () => setEmps((e) => [...e, { age: '', monthly_remuneration: '' }])
  const setEmp = (i, k, v) => setEmps((e) => e.map((x, j) => (j === i ? { ...x, [k]: v } : x)))
  const delEmp = (i) => setEmps((e) => e.filter((_, j) => j !== i))
  const setP = (k, v) => setProv((s) => ({ ...s, [k]: v }))
  const setC = (k, v) => setCgt((s) => ({ ...s, [k]: v }))
  const setF = (k, v) => setFringe((s) => ({ ...s, [k]: v }))
  const setL = (k, v) => setLump((s) => ({ ...s, [k]: v }))
  const setLoss = (k, v) => setLossState((s) => ({ ...s, [k]: v }))
  const setR = (k, v) => setResid((s) => ({ ...s, [k]: v }))
  const setEx = (k, v) => setExitT((s) => ({ ...s, [k]: v }))
  const setFgn = (k, v) => setForeign((s) => ({ ...s, [k]: v }))

  const onlyPositive = (obj) => {
    const out = {}
    for (const k of Object.keys(obj)) { const v = numOrUndef(obj[k]); if (v) out[k] = v }
    return out
  }

  const run = async () => {
    setError(null); setLoading(true); setData(null)
    const payload = {}
    const income = onlyPositive(inc)
    if (Object.keys(income).length) payload.income = income
    const v = onlyPositive(vat)
    if (Object.keys(v).length) payload.vat = v
    const roster = emps
      .map((e) => ({ age: numOrUndef(e.age), monthly_remuneration: numOrUndef(e.monthly_remuneration) }))
      .filter((e) => e.age || e.monthly_remuneration)
    if (roster.length) { payload.employees = roster; payload.eti_year = etiYear }
    const provEst = numOrUndef(prov.estimate_taxable)
    if (provEst) {
      const pv = { estimate_taxable: provEst }
      if (numOrUndef(inc.age)) pv.age = numOrUndef(inc.age)
      if (numOrUndef(inc.paye_paid)) pv.paye_paid = numOrUndef(inc.paye_paid)
      if (numOrUndef(prov.latest_assessed_taxable)) pv.latest_assessed_taxable = numOrUndef(prov.latest_assessed_taxable)
      if (numOrUndef(prov.actual_taxable)) pv.actual_taxable = numOrUndef(prov.actual_taxable)
      payload.provisional = pv
    }
    const cgtIn = onlyPositive(cgt)
    if (Object.keys(cgtIn).length) {
      cgtIn.taxpayer = cgtTaxpayer
      if (cgtTaxpayer === 'individual') {
        if (numOrUndef(inc.age)) cgtIn.age = numOrUndef(inc.age)
        if (cgtDeath) cgtIn.year_of_death = true
      }
      payload.cgt = cgtIn
    }
    const fr = onlyPositive(fringe)
    if (Object.keys(fr).length) {
      if (carMaint) fr.car_has_maintenance = true
      payload.fringe_benefits = fr
    }
    const lumpAmt = numOrUndef(lump.amount)
    if (lumpAmt) {
      const lp = { amount: lumpAmt, kind: lumpKind }
      if (numOrUndef(lump.prior)) lp.prior = numOrUndef(lump.prior)
      payload.lump_sum = lp
    }
    const lossIn = onlyPositive(loss)
    if (numOrUndef(loss.balance_brought_forward)) {
      lossIn.taxpayer = lossTaxpayer
      if (lossTaxpayer !== 'company' && lossSuspect) lossIn.suspect_trade = true
      payload.assessed_loss = lossIn
    }
    const cyd = numOrUndef(resid.current_year_days)
    if (cyd) {
      const priors = ['p1', 'p2', 'p3', 'p4', 'p5'].map((k) => numOrUndef(resid[k]) || 0)
      const rp = { current_year_days: cyd, prior_years_days: priors }
      if (numOrUndef(resid.days_continuously_absent)) rp.days_continuously_absent = numOrUndef(resid.days_continuously_absent)
      payload.residency = rp
    }
    const dg = numOrUndef(exitT.deemed_gains)
    if (dg) {
      const ep = { deemed_gains: dg, taxpayer: exitTaxpayer }
      if (exitTaxpayer === 'individual') {
        if (numOrUndef(exitT.other_taxable_income)) ep.other_taxable_income = numOrUndef(exitT.other_taxable_income)
        if (numOrUndef(inc.age)) ep.age = numOrUndef(inc.age)
      }
      payload.exit_tax = ep
    }
    const fi = numOrUndef(foreign.foreign_employment_income)
    if (fi) {
      payload.foreign_income = {
        foreign_employment_income: fi,
        days_outside_total: numOrUndef(foreign.days_outside_total) || 0,
        longest_continuous_days: numOrUndef(foreign.longest_continuous_days) || 0,
      }
    }
    try {
      setData(await getTaxIncome(payload))
      setLastPayload(payload)
      setAudit(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const [lastPayload, setLastPayload] = useState(null)
  const [audit, setAudit] = useState(null)
  const loadAudit = async () => {
    if (audit) { setAudit(null); return }
    try { setAudit(await getTaxAuditTrail(lastPayload || {})) } catch (e) { setError(e.message) }
  }

  const t = data?.income_tax
  const vr = data?.vat
  const er = data?.eti
  const pr = data?.provisional
  const cr = data?.cgt
  const fbr = data?.fringe_benefits
  const lr = data?.lump_sum
  const alr = data?.assessed_loss
  const rr = data?.residency
  const etr = data?.exit_tax
  const fir = data?.foreign_income

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Income &amp; Tax (IRP5)</h1>
        <p className="text-sm text-slate-400 mt-1">
          Clone the figures from your IRP5 to estimate income tax, VAT and ETI for the year — deterministic,
          SARS 2026/27. Decision-support only, not tax advice.
        </p>
      </div>

      {/* Income & deductions */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
        <div className="text-xs font-semibold text-slate-300 uppercase tracking-wide">Income &amp; deductions (annual, ZAR)</div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <NumField label="Salary / wages (3601)" value={inc.salary} onChange={(v) => setI('salary', v)} />
          <NumField label="Annual payment / bonus (3605)" value={inc.annual_payment} onChange={(v) => setI('annual_payment', v)} />
          <NumField label="Commission (3606)" value={inc.commission} onChange={(v) => setI('commission', v)} />
          <NumField label="Overtime (3607)" value={inc.overtime} onChange={(v) => setI('overtime', v)} />
          <NumField label="Travel allowance (3701)" value={inc.travel_allowance} onChange={(v) => setI('travel_allowance', v)} />
          <NumField label="Other / additional income" value={inc.additional_income} onChange={(v) => setI('additional_income', v)} />
          <NumField label="Business km travelled" value={inc.travel_business_km} onChange={(v) => setI('travel_business_km', v)} />
          <NumField label="Retirement contribution (4001/4003/4006)" value={inc.retirement_contribution} onChange={(v) => setI('retirement_contribution', v)} />
          <NumField label="Medical-scheme members" value={inc.medical_members} onChange={(v) => setI('medical_members', v)} />
          <NumField label="PAYE already paid (4102)" value={inc.paye_paid} onChange={(v) => setI('paye_paid', v)} />
          <NumField label="Age" value={inc.age} onChange={(v) => setI('age', v)} />
        </div>
      </div>

      {/* VAT (optional) */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
        <div className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
          VAT for the period <span className="text-slate-500 normal-case">(optional — VAT-inclusive amounts)</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <NumField label="Standard-rated sales (incl.)" value={vat.standard_rated_incl} onChange={(v) => setV('standard_rated_incl', v)} />
          <NumField label="Zero-rated sales" value={vat.zero_rated} onChange={(v) => setV('zero_rated', v)} />
          <NumField label="Exempt supplies" value={vat.exempt} onChange={(v) => setV('exempt', v)} />
          <NumField label="Input — capital goods (incl.)" value={vat.input_capital_incl} onChange={(v) => setV('input_capital_incl', v)} />
          <NumField label="Input — other (incl.)" value={vat.input_other_incl} onChange={(v) => setV('input_other_incl', v)} />
        </div>
      </div>

      {/* ETI (optional) */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
            ETI roster <span className="text-slate-500 normal-case">(optional — young workers 18–29)</span>
          </div>
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => setEtiYear(etiYear === 1 ? 2 : 1)}
              className="text-xs rounded-lg px-2.5 py-1 border border-white/10 text-slate-300 hover:border-white/25">
              Year {etiYear}
            </button>
            <button type="button" onClick={addEmp}
              className="text-xs rounded-lg px-2.5 py-1 border border-gold/40 text-gold hover:bg-gold/10">
              + employee
            </button>
          </div>
        </div>
        {emps.length === 0 && <div className="text-xs text-slate-500">No employees added.</div>}
        {emps.map((e, i) => (
          <div key={i} className="grid grid-cols-[1fr_1fr_auto] gap-3 items-end">
            <NumField label="Age" value={e.age} onChange={(v) => setEmp(i, 'age', v)} />
            <NumField label="Monthly remuneration" value={e.monthly_remuneration} onChange={(v) => setEmp(i, 'monthly_remuneration', v)} />
            <button type="button" onClick={() => delEmp(i)}
              className="text-xs rounded-lg px-2.5 py-1.5 border border-white/10 text-slate-400 hover:border-red-400/40 hover:text-red-300">
              remove
            </button>
          </div>
        ))}
      </div>

      {/* Provisional tax (optional) */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
        <div className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
          Provisional tax (IRP6) <span className="text-slate-500 normal-case">(optional — uses Age & PAYE above)</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <NumField label="Estimated taxable income (year)" value={prov.estimate_taxable} onChange={(v) => setP('estimate_taxable', v)} />
          <NumField label="Last assessed taxable income" value={prov.latest_assessed_taxable} onChange={(v) => setP('latest_assessed_taxable', v)} />
          <NumField label="Actual taxable income (if known)" value={prov.actual_taxable} onChange={(v) => setP('actual_taxable', v)} />
        </div>
      </div>

      {/* Capital gains (optional) */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
            Capital gains (8th Schedule) <span className="text-slate-500 normal-case">(optional)</span>
          </div>
          <select value={cgtTaxpayer} onChange={(e) => setCgtTaxpayer(e.target.value)}
            className="text-xs rounded-lg bg-navy border border-white/10 px-2 py-1 text-slate-200 focus:border-gold/40 outline-none">
            <option value="individual">Individual</option>
            <option value="company">Company</option>
            <option value="trust">Trust</option>
          </select>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <NumField label="Total capital gains" value={cgt.total_gains} onChange={(v) => setC('total_gains', v)} />
          <NumField label="Total capital losses" value={cgt.total_losses} onChange={(v) => setC('total_losses', v)} />
          <NumField label="Primary-residence gain" value={cgt.primary_residence_gain} onChange={(v) => setC('primary_residence_gain', v)} />
          {cgtTaxpayer === 'individual' && (
            <NumField label="Other taxable income" value={cgt.other_taxable_income} onChange={(v) => setC('other_taxable_income', v)} />
          )}
        </div>
        {cgtTaxpayer === 'individual' && (
          <label className="flex items-center gap-2 text-xs text-slate-400">
            <input type="checkbox" checked={cgtDeath} onChange={(e) => setCgtDeath(e.target.checked)} className="accent-gold" />
            Year of death (R300k exclusion)
          </label>
        )}
      </div>

      {/* Fringe benefits (optional) */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
        <div className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
          Fringe benefits (7th Schedule) <span className="text-slate-500 normal-case">(optional — annual)</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <NumField label="Company-car determined value" value={fringe.car_determined_value} onChange={(v) => setF('car_determined_value', v)} />
          <NumField label="Low-interest loan amount" value={fringe.loan_amount} onChange={(v) => setF('loan_amount', v)} />
          <NumField label="Interest rate paid on loan (%)" value={fringe.loan_interest_paid_pct} onChange={(v) => setF('loan_interest_paid_pct', v)} />
          <NumField label="Accommodation remuneration proxy" value={fringe.accommodation_remuneration_proxy} onChange={(v) => setF('accommodation_remuneration_proxy', v)} />
        </div>
        <label className="flex items-center gap-2 text-xs text-slate-400">
          <input type="checkbox" checked={carMaint} onChange={(e) => setCarMaint(e.target.checked)} className="accent-gold" />
          Car has a maintenance plan (3.25% instead of 3.5%)
        </label>
      </div>

      {/* Lump sum (optional) */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
            Lump sum <span className="text-slate-500 normal-case">(optional — retirement / severance / withdrawal)</span>
          </div>
          <select value={lumpKind} onChange={(e) => setLumpKind(e.target.value)}
            className="text-xs rounded-lg bg-navy border border-white/10 px-2 py-1 text-slate-200 focus:border-gold/40 outline-none">
            <option value="retirement">Retirement / death</option>
            <option value="severance">Severance</option>
            <option value="withdrawal">Pre-retirement withdrawal</option>
          </select>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <NumField label="Lump-sum amount" value={lump.amount} onChange={(v) => setL('amount', v)} />
          <NumField label="Prior lump sums (lifetime)" value={lump.prior} onChange={(v) => setL('prior', v)} />
        </div>
      </div>

      {/* Assessed loss (optional) */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
            Assessed loss (s20) <span className="text-slate-500 normal-case">(optional — loss brought forward)</span>
          </div>
          <select value={lossTaxpayer} onChange={(e) => setLossTaxpayer(e.target.value)}
            className="text-xs rounded-lg bg-navy border border-white/10 px-2 py-1 text-slate-200 focus:border-gold/40 outline-none">
            <option value="company">Company</option>
            <option value="individual">Individual</option>
            <option value="trust">Trust</option>
          </select>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <NumField label="Taxable income (before set-off)" value={loss.taxable_income_before} onChange={(v) => setLoss('taxable_income_before', v)} />
          <NumField label="Assessed loss brought forward" value={loss.balance_brought_forward} onChange={(v) => setLoss('balance_brought_forward', v)} />
        </div>
        {lossTaxpayer !== 'company' && (
          <label className="flex items-center gap-2 text-xs text-slate-400">
            <input type="checkbox" checked={lossSuspect} onChange={(e) => setLossSuspect(e.target.checked)} className="accent-gold" />
            Suspect trade (s20A ring-fencing if top-bracket)
          </label>
        )}
      </div>

      {/* Cross-border (Tax Me If You Can) */}
      <div className="rounded-2xl border border-gold/20 bg-gold/[0.03] p-5 space-y-4">
        <div className="text-xs font-semibold text-gold uppercase tracking-wide">
          Cross-border — “Tax Me If You Can” <span className="text-slate-500 normal-case">(optional — residency, exit tax, foreign income)</span>
        </div>

        {/* Residency day-count */}
        <div className="space-y-2">
          <div className="text-[11px] font-semibold text-slate-300">Physical-presence test (days in SA)</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <NumField label="This year" value={resid.current_year_days} onChange={(v) => setR('current_year_days', v)} />
            <NumField label="Prior yr 1" value={resid.p1} onChange={(v) => setR('p1', v)} />
            <NumField label="Prior yr 2" value={resid.p2} onChange={(v) => setR('p2', v)} />
            <NumField label="Prior yr 3" value={resid.p3} onChange={(v) => setR('p3', v)} />
            <NumField label="Prior yr 4" value={resid.p4} onChange={(v) => setR('p4', v)} />
            <NumField label="Prior yr 5" value={resid.p5} onChange={(v) => setR('p5', v)} />
            <NumField label="Continuous days absent" value={resid.days_continuously_absent} onChange={(v) => setR('days_continuously_absent', v)} />
          </div>
        </div>

        {/* Exit tax */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-[11px] font-semibold text-slate-300">Exit tax (s9H deemed disposal)</div>
            <select value={exitTaxpayer} onChange={(e) => setExitTaxpayer(e.target.value)}
              className="text-xs rounded-lg bg-navy border border-white/10 px-2 py-1 text-slate-200 focus:border-gold/40 outline-none">
              <option value="individual">Individual</option>
              <option value="company">Company</option>
              <option value="trust">Trust</option>
            </select>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <NumField label="Deemed gain (excl. SA property)" value={exitT.deemed_gains} onChange={(v) => setEx('deemed_gains', v)} />
            {exitTaxpayer === 'individual' && (
              <NumField label="Other taxable income" value={exitT.other_taxable_income} onChange={(v) => setEx('other_taxable_income', v)} />
            )}
          </div>
        </div>

        {/* Foreign employment income */}
        <div className="space-y-2">
          <div className="text-[11px] font-semibold text-slate-300">Foreign employment income (s10(1)(o)(ii))</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <NumField label="Foreign employment income" value={foreign.foreign_employment_income} onChange={(v) => setFgn('foreign_employment_income', v)} />
            <NumField label="Days outside SA (total)" value={foreign.days_outside_total} onChange={(v) => setFgn('days_outside_total', v)} />
            <NumField label="Longest continuous days out" value={foreign.longest_continuous_days} onChange={(v) => setFgn('longest_continuous_days', v)} />
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button type="button" onClick={run} disabled={loading}
          className="rounded-xl px-5 py-2.5 text-sm font-semibold bg-gold text-navy hover:bg-gold/90 disabled:opacity-50">
          {loading ? 'Calculating…' : 'Calculate'}
        </button>
        {error && <span className="text-sm text-red-300">{error}</span>}
      </div>

      {/* Results */}
      {data && (
        <div className="space-y-4">
          {t && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-white">Income tax</h2>
                <PositionBadge position={t.position} />
              </div>
              <Row label="Gross income" value={rand(t.gross_income)} />
              <Row label="Retirement deduction" value={'− ' + rand(t.retirement_deduction)} />
              <Row label="Travel deduction (s8(1)(b))" value={'− ' + rand(t.travel_deduction)} />
              <Row label="Taxable income" value={rand(t.taxable_income)} strong />
              <Row label="Tax before credits" value={rand(t.tax_before_credits)} />
              <Row label="Medical tax credit" value={'− ' + rand(t.medical_tax_credit)} />
              <Row label="Tax payable" value={rand(t.tax_payable)} strong />
              <Row label="PAYE already paid" value={'− ' + rand(t.paye_paid)} />
              <Row label={t.position === 'refund' ? 'Refund due' : 'Balance owing'} value={rand(Math.abs(t.balance))} strong />
            </div>
          )}
          {vr && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-white">VAT ({vr.tax_fraction_label})</h2>
                <PositionBadge position={vr.net_position} />
              </div>
              <Row label="Output VAT" value={rand(vr.output.output_vat)} />
              <Row label="Input VAT (total)" value={'− ' + rand(vr.input.total_input_vat)} />
              <Row label={vr.net_position === 'refund' ? 'VAT refund' : 'Net VAT payable'} value={rand(Math.abs(vr.net_vat_payable))} strong />
            </div>
          )}
          {er && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
              <h2 className="text-sm font-semibold text-white mb-3">Employment Tax Incentive (year {er.year})</h2>
              <Row label="Qualifying employees" value={er.qualifying_count} />
              <Row label="Monthly ETI total" value={rand(er.monthly_total)} strong />
              <Row label="12-month projection" value={rand(er.annual_projection)} />
              <div className="mt-2 space-y-1">
                {er.employees.map((e, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Age {String(e.age)} · {rand(e.monthly_remuneration)}/mo</span>
                    <span className={e.reason === 'qualifying' ? 'text-emerald-300' : 'text-slate-500'}>
                      {e.reason === 'qualifying' ? rand(e.monthly_eti) + '/mo' : e.reason}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {pr && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
              <h2 className="text-sm font-semibold text-white mb-3">Provisional tax (IRP6)</h2>
              <Row label="Tax on estimate" value={rand(pr.tax_on_estimate)} />
              <Row label="First payment" value={rand(pr.first_payment)} />
              <Row label="Second payment" value={rand(pr.second_payment)} />
              <Row label="Total provisional" value={rand(pr.total_provisional)} strong />
              {pr.underestimation_penalty !== undefined && (
                <Row label="Under-estimation penalty (par 20)" value={rand(pr.underestimation_penalty)} />
              )}
              {pr.balance_on_assessment !== undefined && (
                <Row label="Balance on assessment" value={rand(pr.balance_on_assessment)} strong />
              )}
            </div>
          )}
          {cr && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-white">Capital gains tax ({cr.taxpayer})</h2>
                <span className="text-xs text-slate-400">incl. {Math.round(cr.inclusion_rate * 100)}%</span>
              </div>
              <Row label="Aggregate capital gain" value={rand(cr.aggregate_capital_gain)} />
              <Row label="Net capital gain" value={rand(cr.net_capital_gain)} />
              <Row label="Taxable capital gain" value={rand(cr.taxable_capital_gain)} />
              <Row label="CGT payable" value={rand(cr.cgt_payable)} strong />
              <Row label="Effective rate on gains" value={cr.effective_rate_pct + '%'} />
            </div>
          )}
          {fbr && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
              <h2 className="text-sm font-semibold text-white mb-3">Fringe benefits (taxable value)</h2>
              {fbr.company_car > 0 && <Row label="Company car" value={rand(fbr.company_car)} />}
              {fbr.low_interest_loan > 0 && <Row label={`Low-interest loan (vs ${fbr.official_rate_used}%)`} value={rand(fbr.low_interest_loan)} />}
              {fbr.accommodation > 0 && <Row label="Accommodation" value={rand(fbr.accommodation)} />}
              <Row label="Total taxable fringe benefits" value={rand(fbr.total_taxable_fringe_benefits)} strong />
            </div>
          )}
          {lr && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
              <h2 className="text-sm font-semibold text-white mb-3">Lump sum ({lr.kind})</h2>
              <Row label="Lump-sum amount" value={rand(lr.amount)} />
              {lr.prior_lump_sums > 0 && <Row label="Prior lump sums (lifetime)" value={rand(lr.prior_lump_sums)} />}
              <Row label="Tax on lump sum" value={rand(lr.tax)} strong />
              <Row label="Net in hand" value={rand(lr.net)} strong />
              <Row label="Effective rate" value={lr.effective_rate_pct + '%'} />
            </div>
          )}
          {alr && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-white">Assessed loss set-off ({alr.taxpayer})</h2>
                {alr.ring_fenced && <span className="text-xs rounded-lg px-2.5 py-1 border border-amber-400/40 text-amber-300 bg-amber-400/10">ring-fenced</span>}
                {alr.capped && <span className="text-xs rounded-lg px-2.5 py-1 border border-amber-400/40 text-amber-300 bg-amber-400/10">80% cap applied</span>}
              </div>
              <Row label="Taxable income before set-off" value={rand(alr.taxable_income_before)} />
              <Row label="Loss brought forward" value={rand(alr.balance_brought_forward)} />
              <Row label="Set-off allowed this year" value={'− ' + rand(alr.allowed_setoff)} />
              <Row label="Taxable income after set-off" value={rand(alr.taxable_income_after)} strong />
              <Row label="Loss carried forward" value={rand(alr.carried_forward)} strong />
            </div>
          )}
          {rr && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-white">Tax residency (physical-presence test)</h2>
                <span className={`text-xs rounded-lg px-2.5 py-1 border ${rr.resident_by_presence ? 'border-amber-400/40 text-amber-300 bg-amber-400/10' : 'border-emerald-400/40 text-emerald-300 bg-emerald-400/10'}`}>
                  {rr.status.replace(/_/g, ' ')}
                </span>
              </div>
              {rr.prongs.map((p) => (
                <Row key={p.prong} label={p.label} value={p.met ? '✓ met' : '✗ not met'} />
              ))}
              <p className="text-xs text-slate-400 mt-2">{rr.summary}</p>
              <p className="text-xs text-slate-600 mt-1">{rr.ordinarily_resident_note}</p>
            </div>
          )}
          {etr && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
              <h2 className="text-sm font-semibold text-white mb-3">Exit tax (s9H deemed disposal · {etr.taxpayer})</h2>
              <Row label="Deemed gain" value={rand(etr.deemed_gains)} />
              <Row label="Taxable capital gain" value={rand(etr.taxable_capital_gain)} />
              <Row label="Exit tax payable" value={rand(etr.exit_tax_payable)} strong />
              <p className="text-xs text-slate-600 mt-2">{etr.excluded_assets_note}</p>
            </div>
          )}
          {fir && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-white">Foreign employment income (s10(1)(o)(ii))</h2>
                <span className={`text-xs rounded-lg px-2.5 py-1 border ${fir.qualifies ? 'border-emerald-400/40 text-emerald-300 bg-emerald-400/10' : 'border-red-400/40 text-red-300 bg-red-400/10'}`}>
                  {fir.qualifies ? 'qualifies' : 'no exemption'}
                </span>
              </div>
              <Row label="Foreign employment income" value={rand(fir.foreign_employment_income)} />
              <Row label="Exempt (cap R1.25m)" value={'− ' + rand(fir.exempt_amount)} />
              <Row label="Taxable in SA" value={rand(fir.taxable_amount)} strong />
              <p className="text-xs text-slate-400 mt-2">{fir.summary}</p>
            </div>
          )}
          {/* SARS-cited audit trail — how each figure was derived */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-white">Audit trail — how each figure was derived</h2>
                <p className="text-xs text-slate-400 mt-1">Every number is computed in code from dated SARS constants; each section cites its statutory provision so it’s reproducible and examination-survivable.</p>
              </div>
              <button type="button" onClick={loadAudit}
                className="shrink-0 text-xs rounded-lg px-3 py-1.5 border border-white/10 text-slate-300 hover:border-white/25">
                {audit ? 'Hide' : 'Show audit trail'}
              </button>
            </div>
            {audit?.entries?.length > 0 && (
              <div className="mt-3 space-y-2">
                <div className="text-[11px] text-slate-500">Rates dated {audit.rates_dated} · {audit.rates_note}</div>
                {audit.entries.map((e) => (
                  <div key={e.section} className="rounded-lg border border-white/10 p-3">
                    <div className="text-sm text-white font-medium capitalize">{e.section.replace(/_/g, ' ')}</div>
                    <div className="text-xs text-gold/90 mt-0.5">{e.provision}</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">Rate source: {e.rate_source}</div>
                    <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-[11px] text-slate-400">
                      {Object.entries(e.figures).map(([k, v]) => (
                        <span key={k}>{k.replace(/_/g, ' ')}: <span className="text-slate-200">{typeof v === 'number' ? 'R ' + Math.round(v).toLocaleString('en-ZA') : String(v)}</span></span>
                      ))}
                    </div>
                  </div>
                ))}
                <p className="text-xs text-slate-500">{audit.note}</p>
              </div>
            )}
          </div>
          {data.disclaimer && <p className="text-xs text-slate-500">{data.disclaimer}</p>}
        </div>
      )}

      {/* SARS dispute deadlines (independent of the calculator) */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-white">SARS dispute deadlines</h2>
          <p className="text-xs text-slate-400 mt-1">
            Disagree with an assessment? Enter its date to see the statutory deadlines in TAA business
            days (weekends, public holidays and the 16 Dec–15 Jan recess excluded). The 80-day objection clock is the critical one.
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-xs text-slate-400">
            Assessment date
            <input type="date" value={disputeDate} onChange={(e) => setDisputeDate(e.target.value)}
              className="mt-1 block rounded-lg bg-navy border border-white/10 px-2.5 py-1.5 text-sm text-white focus:border-gold/40 outline-none" />
          </label>
          <button type="button" onClick={runDispute}
            className="rounded-xl px-4 py-2 text-sm font-semibold border border-gold/40 text-gold hover:bg-gold/10">
            Show deadlines
          </button>
          {disputeErr && <span className="text-sm text-red-300">{disputeErr}</span>}
        </div>
        {dispute && (
          <div className="space-y-1">
            {dispute.steps.map((s) => (
              <div key={s.key} className="flex items-center justify-between py-1.5 border-b border-white/5 last:border-0">
                <span className="text-xs text-slate-400">{s.label} <span className="text-slate-600">({s.business_days} bd)</span></span>
                <span className="text-sm text-slate-200 font-medium">{s.deadline}</span>
              </div>
            ))}
            <p className="text-xs text-slate-500 pt-2">{dispute.note}</p>
          </div>
        )}
      </div>

      {/* SARS process guidance */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-white">Dealing with SARS — process guide</h2>
            <p className="text-xs text-slate-400 mt-1">Verification, audit, VDP, record-keeping and debt relief — deadlines + do's/don'ts, cited to the TAA.</p>
          </div>
          <button type="button" onClick={loadGuidance}
            className="shrink-0 text-xs rounded-lg px-3 py-1.5 border border-white/10 text-slate-300 hover:border-white/25">
            {guidance ? 'Hide' : 'Show guide'}
          </button>
        </div>
        {guidance?.cards && (
          <div className="space-y-2">
            {guidance.cards.map((c) => (
              <div key={c.key} className="rounded-lg border border-white/10 overflow-hidden">
                <button type="button" onClick={() => setOpenCard(openCard === c.key ? null : c.key)}
                  className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-white/[0.03]">
                  <span className="text-sm text-white font-medium">{c.title}</span>
                  <span className="text-xs text-slate-500">{openCard === c.key ? '−' : '+'}</span>
                </button>
                {openCard === c.key && (
                  <div className="px-3 pb-3 space-y-2 text-xs">
                    <p className="text-slate-400">{c.what_it_is}</p>
                    <p className="text-amber-300/90"><span className="font-semibold">Deadline:</span> {c.deadline}</p>
                    <div className="grid sm:grid-cols-2 gap-2">
                      <div>
                        <div className="text-emerald-400 font-semibold mb-1">Do</div>
                        <ul className="space-y-0.5 text-slate-400">{c.do.map((d, i) => <li key={i}>· {d}</li>)}</ul>
                      </div>
                      <div>
                        <div className="text-red-400 font-semibold mb-1">Don't</div>
                        <ul className="space-y-0.5 text-slate-400">{c.dont.map((d, i) => <li key={i}>· {d}</li>)}</ul>
                      </div>
                    </div>
                    <p className="text-slate-600">{c.citation}</p>
                  </div>
                )}
              </div>
            ))}
            <p className="text-xs text-slate-500">{guidance.disclaimer}</p>
          </div>
        )}
      </div>
    </div>
  )
}
