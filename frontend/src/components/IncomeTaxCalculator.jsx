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

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const setI = (k, v) => setInc((s) => ({ ...s, [k]: v }))
  const setV = (k, v) => setVat((s) => ({ ...s, [k]: v }))
  const addEmp = () => setEmps((e) => [...e, { age: '', monthly_remuneration: '' }])
  const setEmp = (i, k, v) => setEmps((e) => e.map((x, j) => (j === i ? { ...x, [k]: v } : x)))
  const delEmp = (i) => setEmps((e) => e.filter((_, j) => j !== i))
  const setP = (k, v) => setProv((s) => ({ ...s, [k]: v }))

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
          {data.disclaimer && <p className="text-xs text-slate-500">{data.disclaimer}</p>}
        </div>
      )}
    </div>
  )
}
