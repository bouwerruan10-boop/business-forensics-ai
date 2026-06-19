/**
 * SmartIntake — stepped intake wizard (4 steps) replacing the single long form.
 * Research shows segmented forms with a progress indicator + inline validation
 * dramatically reduce abandonment. State persists to sessionStorage so a refresh
 * (or the Back button) never wipes progress. The submit payload is unchanged.
 *   Step 1 Business Identity · Step 2 Financial & Tax · Step 3 Documents · Step 4 Context
 */
import { useState, useRef, useEffect } from 'react'
import { Check, ChevronLeft, ChevronRight, AlertCircle, X } from 'lucide-react'

const STORAGE_KEY = 'imara_intake_v1'

const INDUSTRIES = [
  { key: 'retail',           label: 'Retail & E-commerce' },
  { key: 'manufacturing',    label: 'Manufacturing' },
  { key: 'construction',     label: 'Construction' },
  { key: 'professional',     label: 'Professional Services' },
  { key: 'hospitality',      label: 'Hospitality & Tourism' },
  { key: 'healthcare',       label: 'Healthcare & Pharma' },
  { key: 'transport',        label: 'Transport & Logistics' },
  { key: 'agriculture',      label: 'Agriculture & Agri-processing' },
  { key: 'mining',           label: 'Mining & Resources' },
  { key: 'technology',       label: 'Technology & Software' },
  { key: 'financial',        label: 'Financial Services' },
  { key: 'education',        label: 'Education & Training' },
  { key: 'media',            label: 'Media & Creative' },
  { key: 'general',          label: 'Other / General' },
]

const ENTITY_TYPES = [
  'Private Company (Pty) Ltd', 'Close Corporation (CC)', 'Sole Proprietor',
  'Partnership', 'Trust', 'Non-Profit (NPO / NPC)', 'Public Company (Ltd)', 'Co-operative',
]

const BBBEE_LEVELS = [
  'Level 1', 'Level 2', 'Level 3', 'Level 4', 'Level 5', 'Level 6', 'Level 7', 'Level 8',
  'Exempt Micro Enterprise (EME)', 'Qualifying Small Enterprise (QSE)', 'Non-Compliant', 'Not Yet Verified',
]

const BANKS = ['Standard Bank', 'FNB / RMB', 'ABSA', 'Nedbank', 'Capitec Business', 'Investec', 'African Bank', 'Bidvest', 'Other']

const TAX_YEAR_ENDS = ['January', 'February (SARS default)', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

const YEARS_OPTIONS = ['Less than 1 year', '1–3 years', '3–7 years', '7–15 years', '15+ years']

const DOC_ZONES = [
  { id: 'financial', icon: '📊', label: 'Financial Records', desc: 'Income statement, balance sheet, management accounts, cash flow', types: 'Excel · CSV · PDF', required: true, agents: ['Financial Forensics', 'Accounting', 'Auditor'] },
  { id: 'bank', icon: '🏦', label: 'Bank Statements', desc: '3–6 months minimum. Enables cash flow & fraud anomaly detection', types: 'PDF · CSV · Excel', required: true, agents: ['Financial Forensics', 'Fraud Detection', 'Credit Readiness'] },
  { id: 'tax', icon: '🧾', label: 'Tax Documents', desc: 'VAT201, IT14, EMP201, IRP6, tax clearance certificate', types: 'PDF · Excel', required: false, agents: ['SA Tax Compliance'] },
  { id: 'legal', icon: '⚖️', label: 'Legal Documents', desc: 'MOI, shareholder agreement, key contracts, leases, permits', types: 'PDF · Word', required: false, agents: ['SA Corporate Law & BBBEE'] },
  { id: 'hr', icon: '👥', label: 'HR & Payroll', desc: 'Payroll summary, employment contracts, leave records, org chart', types: 'Excel · PDF · CSV', required: false, agents: ['HR Agent', 'SA Tax Compliance'] },
  { id: 'business_plan', icon: '📋', label: 'Business Plan', desc: 'Especially useful for businesses under 3 years old', types: 'PDF · Word', required: false, agents: ['Strategy', 'Valuation'] },
]

const ACCEPTED = '.pdf,.xlsx,.xls,.csv,.docx,.doc'
const STEPS = ['Business Identity', 'Financial & Tax', 'Documents', 'Context & Focus']

function DocZone({ zone, files, onAdd, onRemove, highlight }) {
  const inputRef = useRef()
  const hasFiles = files.length > 0
  const open = () => inputRef.current?.click()
  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${zone.label} upload zone, ${zone.required ? 'required' : 'optional'}${hasFiles ? `, ${files.length} file${files.length === 1 ? '' : 's'} added` : ''}. Press Enter to choose files.`}
      className={`relative rounded-xl border-2 p-4 transition-all cursor-pointer text-center
        ${hasFiles ? 'border-green-500/40 bg-green-500/5' : zone.required ? 'border-gold/25 bg-gold/3' : 'border-white/10 bg-white/2 hover:border-white/20'}
        ${highlight ? 'ring-2 ring-red-500/50' : ''}`}
      onClick={open}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open() } }}
    >
      <input ref={inputRef} type="file" multiple accept={ACCEPTED} className="hidden"
        onChange={e => onAdd(Array.from(e.target.files))} onClick={e => e.stopPropagation()} />
      <div className="absolute top-2 right-2">
        {hasFiles ? (
          <span className="inline-flex items-center gap-0.5 text-[9px] font-bold px-1.5 py-0.5 rounded bg-green-500/15 text-green-400 border border-green-500/25">
            <Check size={9} aria-hidden="true" /> {files.length} {files.length === 1 ? 'file' : 'files'}
          </span>
        ) : zone.required ? (
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-gold/15 text-gold border border-gold/30">REQUIRED</span>
        ) : (
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-white/5 text-slate-400 border border-white/10">OPTIONAL</span>
        )}
      </div>
      <div className="text-2xl mb-2" aria-hidden="true">{zone.icon}</div>
      <div className="text-[12px] font-bold text-white mb-1">{zone.label}</div>
      <div className="text-[10px] text-slate-400 leading-snug mb-1">{zone.desc}</div>
      <div className="text-[9px] text-slate-400 mb-2">{zone.types}</div>
      <div className="flex flex-wrap gap-1 justify-center">
        {zone.agents.map(a => (
          <span key={a} className="text-[8px] px-1.5 py-0.5 rounded-full bg-white/5 text-slate-400 border border-white/8">{a}</span>
        ))}
      </div>
      {hasFiles && (
        <div className="mt-3 flex flex-wrap gap-1 justify-center">
          {files.map((f, i) => (
            <button key={i} type="button"
              aria-label={`Remove ${f.name}`}
              className="inline-flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded bg-green-500/10 border border-green-500/20 text-green-400 hover:border-red-400/40"
              onClick={e => { e.stopPropagation(); onRemove(i) }}>
              {f.name.length > 14 ? f.name.slice(0, 12) + '…' : f.name}
              <X size={9} aria-hidden="true" />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function Field({ label, required, hint, error, children }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[10px] font-semibold text-slate-300 uppercase tracking-wider">
        {label}{required && <span className="text-gold ml-1" aria-hidden="true">*</span>}
      </label>
      {children}
      {error
        ? <span className="text-[10px] text-red-400 inline-flex items-center gap-1"><AlertCircle size={11} aria-hidden="true" />{error}</span>
        : hint && <span className="text-[10px] text-slate-400">{hint}</span>}
    </div>
  )
}

const inputCls = "w-full bg-[#0f1117] border border-white/10 rounded-lg px-3 py-2 text-white text-[13px] outline-none focus:border-gold/40 transition-colors"

export default function SmartIntake({ onAnalyze, onDemo, error }) {
  const [step, setStep] = useState(0)

  // Identity
  const [companyName, setCompanyName] = useState('')
  const [entityType, setEntityType] = useState('')
  const [industryKey, setIndustryKey] = useState('general')
  const [cipcNumber, setCipcNumber] = useState('')
  const [country, setCountry] = useState('South Africa')
  const [yearsInBusiness, setYearsInBusiness] = useState('')
  // Financial & Tax
  const [annualRevenue, setAnnualRevenue] = useState('')
  const [currency, setCurrency] = useState('ZAR')
  const [headcount, setHeadcount] = useState('')
  const [vatRegistered, setVatRegistered] = useState('unknown')
  const [vatNumber, setVatNumber] = useState('')
  const [taxYearEnd, setTaxYearEnd] = useState('')
  const [bbbeeLevel, setBbbeeLevel] = useState('')
  // Documents
  const [docFiles, setDocFiles] = useState({ financial: [], bank: [], tax: [], legal: [], hr: [], business_plan: [] })
  // Context
  const [primaryConcern, setPrimaryConcern] = useState('')
  const [bankingPartner, setBankingPartner] = useState('')
  const [reportAudience, setReportAudience] = useState('owner')

  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)

  // Restore non-file fields from sessionStorage (Back/refresh must not punish progress).
  useEffect(() => {
    try {
      const d = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '{}')
      if (d.companyName !== undefined) setCompanyName(d.companyName)
      if (d.entityType) setEntityType(d.entityType)
      if (d.industryKey) setIndustryKey(d.industryKey)
      if (d.cipcNumber) setCipcNumber(d.cipcNumber)
      if (d.country) setCountry(d.country)
      if (d.yearsInBusiness) setYearsInBusiness(d.yearsInBusiness)
      if (d.annualRevenue) setAnnualRevenue(d.annualRevenue)
      if (d.currency) setCurrency(d.currency)
      if (d.headcount) setHeadcount(d.headcount)
      if (d.vatRegistered) setVatRegistered(d.vatRegistered)
      if (d.vatNumber) setVatNumber(d.vatNumber)
      if (d.taxYearEnd) setTaxYearEnd(d.taxYearEnd)
      if (d.bbbeeLevel) setBbbeeLevel(d.bbbeeLevel)
      if (d.primaryConcern) setPrimaryConcern(d.primaryConcern)
      if (d.bankingPartner) setBankingPartner(d.bankingPartner)
      if (d.reportAudience) setReportAudience(d.reportAudience)
    } catch { /* ignore */ }
  }, [])

  // Persist non-file fields on change.
  useEffect(() => {
    const d = { companyName, entityType, industryKey, cipcNumber, country, yearsInBusiness,
      annualRevenue, currency, headcount, vatRegistered, vatNumber, taxYearEnd, bbbeeLevel,
      primaryConcern, bankingPartner, reportAudience }
    try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(d)) } catch { /* ignore */ }
  }, [companyName, entityType, industryKey, cipcNumber, country, yearsInBusiness, annualRevenue,
      currency, headcount, vatRegistered, vatNumber, taxYearEnd, bbbeeLevel, primaryConcern,
      bankingPartner, reportAudience])

  const addFiles = (zone, newFiles) => {
    setDocFiles(prev => ({ ...prev, [zone]: [...prev[zone], ...newFiles] }))
    setErrors(e => ({ ...e, documents: undefined }))
  }
  const removeFile = (zone, idx) => setDocFiles(prev => ({ ...prev, [zone]: prev[zone].filter((_, i) => i !== idx) }))

  const totalFiles = Object.values(docFiles).flat().length
  const hasFinancial = docFiles.financial.length > 0 || docFiles.bank.length > 0

  // Per-step validation — errors don't bleed across steps.
  const validateStep = s => {
    const e = {}
    if (s === 0 && !companyName.trim()) e.companyName = 'Company name is required.'
    if (s === 2 && !hasFinancial) e.documents = 'Upload at least one Financial Record or Bank Statement to continue.'
    return e
  }

  const goNext = () => {
    const e = validateStep(step)
    setErrors(e)
    if (Object.keys(e).length) return
    setStep(s => Math.min(STEPS.length - 1, s + 1))
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  const goBack = () => { setErrors({}); setStep(s => Math.max(0, s - 1)); window.scrollTo({ top: 0, behavior: 'smooth' }) }
  const goTo = target => { if (target <= step) { setErrors({}); setStep(target) } }

  const handleSubmit = async e => {
    e.preventDefault()
    // Validate all gating steps before submit.
    const all = { ...validateStep(0), ...validateStep(2) }
    if (Object.keys(all).length) {
      setErrors(all)
      setStep(all.companyName ? 0 : 2)
      return
    }
    setSubmitting(true)
    const allFiles = []
    const allCategories = []
    for (const [zone, files] of Object.entries(docFiles)) {
      for (const f of files) { allFiles.push(f); allCategories.push(zone) }
    }
    const profile = {
      company_name: companyName.trim(), industry_key: industryKey,
      annual_revenue: parseFloat(annualRevenue.replace(/[^\d.]/g, '')) || 0,
      headcount: parseInt(headcount) || 0, currency, country, primary_concern: primaryConcern,
      entity_type: entityType, cipc_number: cipcNumber, vat_registered: vatRegistered,
      vat_number: vatNumber, tax_year_end: taxYearEnd, years_in_business: yearsInBusiness,
      bbbee_level: bbbeeLevel, banking_partner: bankingPartner, report_audience: reportAudience,
      file_categories: JSON.stringify(allCategories),
    }
    try {
      sessionStorage.removeItem(STORAGE_KEY)
      await onAnalyze(allFiles, profile)
    } finally {
      setSubmitting(false)
    }
  }

  const pct = Math.round(((step + 1) / STEPS.length) * 100)

  return (
    <form onSubmit={handleSubmit} className="max-w-3xl mx-auto pb-16">
      <div className="mb-6">
        <h1 className="text-3xl font-black text-white mb-2">Business Profile</h1>
        <p className="text-slate-300 text-sm">
          Four quick steps. The more context you provide, the more targeted the analysis — at minimum, upload one financial document.
        </p>
      </div>

      {/* Progress + step chips */}
      <div className="mb-6">
        <div className="flex justify-between text-[11px] text-slate-400 mb-1.5">
          <span>Step {step + 1} of {STEPS.length}: <span className="text-white font-semibold">{STEPS[step]}</span></span>
          <span>{pct}%</span>
        </div>
        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Intake progress">
          <div className="h-full progress-shimmer rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {STEPS.map((s, i) => {
            const done = i < step, current = i === step
            return (
              <button key={s} type="button" onClick={() => goTo(i)} disabled={i > step}
                aria-current={current ? 'step' : undefined}
                className={`inline-flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-full border transition-colors ${
                  current ? 'border-gold/50 bg-gold/10 text-gold'
                  : done ? 'border-emerald-400/30 bg-emerald-400/5 text-emerald-400 hover:border-emerald-400/50'
                  : 'border-white/10 text-slate-500 cursor-not-allowed'}`}>
                <span className={`w-4 h-4 rounded-full text-[9px] font-black flex items-center justify-center ${
                  current ? 'bg-gold text-navy' : done ? 'bg-emerald-400 text-navy' : 'bg-white/10 text-slate-400'}`}>
                  {done ? <Check size={10} aria-hidden="true" /> : i + 1}
                </span>
                {s}
              </button>
            )
          })}
        </div>
      </div>

      {/* ── Step 1: Identity ── */}
      {step === 0 && (
        <div className="bg-[#161b27] border border-white/8 rounded-2xl p-6 mb-4 fade-in">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Field label="Company Name" required error={errors.companyName}>
                <input className={inputCls} placeholder="e.g. Mzansi Trading (Pty) Ltd" value={companyName}
                  onChange={e => { setCompanyName(e.target.value); if (errors.companyName) setErrors(x => ({ ...x, companyName: undefined })) }} autoFocus />
              </Field>
            </div>
            <Field label="Entity Type" hint="Determines applicable law & tax regime">
              <select className={inputCls} value={entityType} onChange={e => setEntityType(e.target.value)}>
                <option value="">Select entity type...</option>
                {ENTITY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </Field>
            <Field label="Industry" required>
              <select className={inputCls} value={industryKey} onChange={e => setIndustryKey(e.target.value)}>
                {INDUSTRIES.map(i => <option key={i.key} value={i.key}>{i.label}</option>)}
              </select>
            </Field>
            <Field label="CIPC Registration Number" hint="e.g. 2015/123456/07 — used for compliance checks">
              <input className={inputCls} placeholder="e.g. 2015/123456/07" value={cipcNumber} onChange={e => setCipcNumber(e.target.value)} />
            </Field>
            <Field label="Country"><input className={inputCls} value={country} onChange={e => setCountry(e.target.value)} /></Field>
            <Field label="Years in Business" hint="Calibrates benchmarks and unlocks the business-plan zone">
              <select className={inputCls} value={yearsInBusiness} onChange={e => setYearsInBusiness(e.target.value)}>
                <option value="">Select...</option>
                {YEARS_OPTIONS.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
            </Field>
          </div>
        </div>
      )}

      {/* ── Step 2: Financial & Tax ── */}
      {step === 1 && (
        <div className="bg-[#161b27] border border-white/8 rounded-2xl p-6 mb-4 fade-in">
          <div className="grid grid-cols-3 gap-4">
            <Field label="Annual Revenue (approx.)">
              <input className={inputCls} placeholder="e.g. 6 000 000" value={annualRevenue} onChange={e => setAnnualRevenue(e.target.value)} />
            </Field>
            <Field label="Currency">
              <select className={inputCls} value={currency} onChange={e => setCurrency(e.target.value)}>
                <option value="ZAR">ZAR — South African Rand</option>
                <option value="USD">USD — US Dollar</option>
                <option value="EUR">EUR — Euro</option>
                <option value="GBP">GBP — British Pound</option>
              </select>
            </Field>
            <Field label="Headcount">
              <input className={inputCls} type="number" placeholder="e.g. 25" value={headcount} onChange={e => setHeadcount(e.target.value)} />
            </Field>
            <Field label="VAT Registered?">
              <select className={inputCls} value={vatRegistered} onChange={e => setVatRegistered(e.target.value)}>
                <option value="unknown">Unknown</option><option value="yes">Yes</option>
                <option value="no">No</option><option value="pending">Pending registration</option>
              </select>
            </Field>
            <Field label="VAT Number" hint="10-digit SARS vendor number">
              <input className={inputCls} placeholder="e.g. 4123456789" value={vatNumber} onChange={e => setVatNumber(e.target.value)} disabled={vatRegistered !== 'yes'} />
            </Field>
            <Field label="Tax Year-End Month">
              <select className={inputCls} value={taxYearEnd} onChange={e => setTaxYearEnd(e.target.value)}>
                <option value="">Select month...</option>
                {TAX_YEAR_ENDS.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </Field>
          </div>
          <div className="mt-5 pt-4 border-t border-white/6">
            <div className="text-[10px] font-bold text-slate-300 uppercase tracking-widest mb-3">BBBEE Level</div>
            <div className="flex flex-wrap gap-2">
              {BBBEE_LEVELS.map(lvl => (
                <button key={lvl} type="button"
                  aria-pressed={bbbeeLevel === lvl}
                  className={`text-[11px] px-3 py-1.5 rounded-lg border transition-all ${
                    bbbeeLevel === lvl ? 'border-gold/50 bg-gold/10 text-gold' : 'border-white/10 bg-[#0f1117] text-slate-300 hover:border-white/20'}`}
                  onClick={() => setBbbeeLevel(bbbeeLevel === lvl ? '' : lvl)}>
                  {lvl}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Step 3: Documents ── */}
      {step === 2 && (
        <div className="bg-[#161b27] border border-white/8 rounded-2xl p-6 mb-4 fade-in" id="doc-zones">
          <div className="flex items-baseline mb-1">
            <h2 className="text-[13px] font-bold text-white">Document Upload</h2>
            {totalFiles > 0 && <span className="ml-auto text-[11px] text-green-400">{totalFiles} file{totalFiles !== 1 ? 's' : ''} uploaded</span>}
          </div>
          <p className="text-[11px] text-slate-400 mb-4">
            Each zone routes documents to the specialist agent best equipped to analyse them.
            At least one financial document (Financial Records or Bank Statements) is required.
          </p>
          {errors.documents && (
            <div className="mb-4 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-[12px] text-red-400 inline-flex items-center gap-1.5">
              <AlertCircle size={13} aria-hidden="true" /> {errors.documents}
            </div>
          )}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {DOC_ZONES.map(zone => (
              <DocZone key={zone.id} zone={zone} files={docFiles[zone.id]}
                onAdd={files => addFiles(zone.id, files)} onRemove={idx => removeFile(zone.id, idx)}
                highlight={!!errors.documents && zone.required && docFiles[zone.id].length === 0} />
            ))}
          </div>
          {yearsInBusiness && (yearsInBusiness === 'Less than 1 year' || yearsInBusiness === '1–3 years') && docFiles.business_plan.length === 0 && (
            <div className="mt-3 px-3 py-2 rounded-lg bg-gold/5 border border-gold/20 text-[11px] text-gold">
              💡 Your business is under 3 years old — uploading your Business Plan unlocks deeper strategy and valuation insights.
            </div>
          )}
        </div>
      )}

      {/* ── Step 4: Context ── */}
      {step === 3 && (
        <div className="bg-[#161b27] border border-white/8 rounded-2xl p-6 mb-4 fade-in">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Field label="Primary Concern" hint="Agents will prioritise this. Be specific — good answers unlock better findings.">
                <textarea className={`${inputCls} h-20 resize-none`}
                  placeholder="e.g. Our margins are shrinking every month but we can't identify why. Cash is also tight and we struggle to pay suppliers on time."
                  value={primaryConcern} onChange={e => setPrimaryConcern(e.target.value)} />
              </Field>
            </div>
            <Field label="Main Banking Partner" hint="Aligns credit-readiness findings to your lender's criteria">
              <select className={inputCls} value={bankingPartner} onChange={e => setBankingPartner(e.target.value)}>
                <option value="">Select bank...</option>
                {BANKS.map(b => <option key={b} value={b}>{b}</option>)}
              </select>
            </Field>
            <Field label="Who is this report for?">
              <div className="flex gap-2">
                {[{ val: 'owner', label: '👤 Business Owner', desc: 'Operational focus' },
                  { val: 'banker', label: '🏦 Bank / Funder', desc: 'Credit focus' },
                  { val: 'investor', label: '📈 Investor', desc: 'Valuation focus' }].map(opt => (
                  <button key={opt.val} type="button" aria-pressed={reportAudience === opt.val}
                    className={`flex-1 p-2 rounded-lg border text-left transition-all ${
                      reportAudience === opt.val ? 'border-gold/50 bg-gold/8 text-gold' : 'border-white/10 text-slate-300 hover:border-white/20'}`}
                    onClick={() => setReportAudience(opt.val)}>
                    <div className="text-[11px] font-bold">{opt.label}</div>
                    <div className="text-[9px] opacity-70">{opt.desc}</div>
                  </button>
                ))}
              </div>
            </Field>
          </div>
          <div className="mt-5 bg-gold/4 border border-gold/15 rounded-xl p-4">
            <div className="text-[11px] font-bold text-white mb-2">⚡ 17 Specialist Agents Will Run</div>
            <div className="flex flex-wrap gap-1.5">
              {['CEO Synthesiser','Financial Forensics','Accounting','Auditor','Operations','Logistics','Sales','Marketing','HR','Procurement','Strategy','Legal Risk','Fraud Detection','Credit Readiness','Valuation','Market Research'].map(a => (
                <span key={a} className="text-[9px] px-2 py-0.5 rounded-full bg-white/5 border border-white/8 text-slate-300">{a}</span>
              ))}
              <span className="text-[9px] px-2 py-0.5 rounded-full bg-gold/10 border border-gold/25 text-gold font-bold">✦ SA Tax Compliance</span>
              <span className="text-[9px] px-2 py-0.5 rounded-full bg-gold/10 border border-gold/25 text-gold font-bold">✦ SA Corporate Law & BBBEE</span>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="mb-4 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/30 text-[13px] text-red-400 inline-flex items-center gap-2">
          <AlertCircle size={15} aria-hidden="true" /> {error}
        </div>
      )}

      {/* Footer nav */}
      <div className="flex items-center gap-3 mt-2">
        {step > 0 && (
          <button type="button" onClick={goBack}
            className="inline-flex items-center gap-1 border border-white/10 text-slate-300 text-[13px] px-4 py-3 rounded-xl hover:border-white/20 transition-colors">
            <ChevronLeft size={16} aria-hidden="true" /> Back
          </button>
        )}
        {step < STEPS.length - 1 ? (
          <button type="button" onClick={goNext}
            className="inline-flex items-center gap-1 bg-gold text-navy font-black text-[14px] px-7 py-3 rounded-xl hover:bg-amber-400 transition-colors">
            Continue <ChevronRight size={16} aria-hidden="true" />
          </button>
        ) : (
          <button type="submit" disabled={submitting || !companyName.trim() || !hasFinancial}
            className="bg-gold text-navy font-black text-[14px] px-8 py-3 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed hover:bg-amber-400 transition-colors">
            {submitting ? 'Starting analysis…' : 'Run Analysis →'}
          </button>
        )}
        <button type="button" onClick={onDemo}
          className="border border-white/10 text-slate-300 text-[13px] px-5 py-3 rounded-xl hover:border-white/20 transition-colors">
          ⚡ Try Demo
        </button>
        <span className="text-[11px] text-slate-400 ml-auto hidden sm:block">
          {hasFinancial ? `${totalFiles} file${totalFiles !== 1 ? 's' : ''} ready` : 'Upload ≥ 1 financial document'}
        </span>
      </div>
    </form>
  )
}
