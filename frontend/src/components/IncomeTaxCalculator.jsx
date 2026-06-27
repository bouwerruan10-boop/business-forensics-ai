import { useState } from 'react'
import { getTaxIncome } from '../api/client'

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

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const setI = (k, v) => setInc((s) => ({ ...s, [k]: v }))
  const setV = (k, v) => setVat((s) => ({ ...s, [k]: v }))
  const addEmp = () => setEmps((e) => [...e, { age: '', monthly_remuneration: '' }])
  const setEmp = (i, k, v) => setEmps((e) => e.map((x, j) => (j === i ? { ...x, [k]: v } : x)))
  const delEmp = (i) => setEmps((e) => e.filter((_, j) => j !== i))
  const setP = (k, v) => setProv((s) => ({ ...s, [k]: v }))
  const setC = (k, v) => setCgt((s) => ({ ...s, [k]: v }))
  const setF = (k, v) => setFringe((s) => ({ ...s, [k]: v }))
  const setL = (k, v) => setLump((s) => ({ ...s, [k]: v }))

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
    try {
      setData(await getTaxIncome(payload))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const t = data?.income_tax
  const vr = data?.vat
  const er = data?.eti
  const pr = data?.provisional
  const cr = data?.cgt
  const fbr = data?.fringe_benefits
  const lr = data?.lump_sum

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
          {data.disclaimer && <p className="text-xs text-slate-500">{data.disclaimer}</p>}
        </div>
      )}
    </div>
  )
}
