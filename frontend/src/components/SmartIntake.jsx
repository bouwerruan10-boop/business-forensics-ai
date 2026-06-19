/**
 * SmartIntake — unified single-page intake replacing BusinessProfile + FileUpload.
 * Four collapsible sections:
 *   1. Business Identity (core + SA-specific fields)
 *   2. Financial & Tax Profile
 *   3. Document Upload (6 dedicated zones)
 *   4. Context & Focus
 */
import { useState, useRef } from 'react'

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
  'Private Company (Pty) Ltd',
  'Close Corporation (CC)',
  'Sole Proprietor',
  'Partnership',
  'Trust',
  'Non-Profit (NPO / NPC)',
  'Public Company (Ltd)',
  'Co-operative',
]

const BBBEE_LEVELS = [
  'Level 1', 'Level 2', 'Level 3', 'Level 4',
  'Level 5', 'Level 6', 'Level 7', 'Level 8',
  'Exempt Micro Enterprise (EME)',
  'Qualifying Small Enterprise (QSE)',
  'Non-Compliant',
  'Not Yet Verified',
]

const BANKS = [
  'Standard Bank', 'FNB / RMB', 'ABSA', 'Nedbank',
  'Capitec Business', 'Investec', 'African Bank', 'Bidvest', 'Other',
]

const TAX_YEAR_ENDS = [
  'January', 'February (SARS default)', 'March', 'April',
  'May', 'June', 'July', 'August', 'September',
  'October', 'November', 'December',
]

const YEARS_OPTIONS = [
  'Less than 1 year', '1–3 years', '3–7 years', '7–15 years', '15+ years',
]

// Document zone definitions
const DOC_ZONES = [
  {
    id: 'financial',
    icon: '📊',
    label: 'Financial Records',
    desc: 'Income statement, balance sheet, management accounts, cash flow',
    types: 'Excel · CSV · PDF',
    required: true,
    agents: ['Financial Forensics', 'Accounting', 'Auditor'],
  },
  {
    id: 'bank',
    icon: '🏦',
    label: 'Bank Statements',
    desc: '3–6 months minimum. Enables cash flow & fraud anomaly detection',
    types: 'PDF · CSV · Excel',
    required: true,
    agents: ['Financial Forensics', 'Fraud Detection', 'Credit Readiness'],
  },
  {
    id: 'tax',
    icon: '🧾',
    label: 'Tax Documents',
    desc: 'VAT201, IT14, EMP201, IRP6, tax clearance certificate',
    types: 'PDF · Excel',
    required: false,
    agents: ['SA Tax Compliance'],
  },
  {
    id: 'legal',
    icon: '⚖️',
    label: 'Legal Documents',
    desc: 'MOI, shareholder agreement, key contracts, leases, permits',
    types: 'PDF · Word',
    required: false,
    agents: ['SA Corporate Law & BBBEE'],
  },
  {
    id: 'hr',
    icon: '👥',
    label: 'HR & Payroll',
    desc: 'Payroll summary, employment contracts, leave records, org chart',
    types: 'Excel · PDF · CSV',
    required: false,
    agents: ['HR Agent', 'SA Tax Compliance'],
  },
  {
    id: 'business_plan',
    icon: '📋',
    label: 'Business Plan',
    desc: 'Especially useful for businesses under 3 years old',
    types: 'PDF · Word',
    required: false,
    agents: ['Strategy', 'Valuation'],
  },
]

const ACCEPTED = '.pdf,.xlsx,.xls,.csv,.docx,.doc'

function DocZone({ zone, files, onAdd, onRemove, highlight }) {
  const inputRef = useRef()
  const hasFiles = files.length > 0

  return (
    <div
      className={`relative rounded-xl border-2 p-4 transition-all cursor-pointer text-center
        ${hasFiles
          ? 'border-green-500/40 bg-green-500/5'
          : zone.required
          ? 'border-gold/25 bg-gold/3'
          : 'border-white/10 bg-white/2 hover:border-white/20'
        }
        ${highlight ? 'ring-2 ring-red-500/40' : ''}
      `}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPTED}
        className="hidden"
        onChange={e => onAdd(Array.from(e.target.files))}
        onClick={e => e.stopPropagation()}
      />

      {/* Required / uploaded badge */}
      <div className="absolute top-2 right-2">
        {hasFiles ? (
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-green-500/15 text-green-400 border border-green-500/25">
            ✓ {files.length} {files.length === 1 ? 'file' : 'files'}
          </span>
        ) : zone.required ? (
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-gold/15 text-gold border border-gold/30">
            REQUIRED
          </span>
        ) : (
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-white/5 text-slate-500 border border-white/10">
            OPTIONAL
          </span>
        )}
      </div>

      <div className="text-2xl mb-2">{zone.icon}</div>
      <div className="text-[12px] font-bold text-white mb-1">{zone.label}</div>
      <div className="text-[10px] text-slate-400 leading-snug mb-1">{zone.desc}</div>
      <div className="text-[9px] text-slate-500 mb-2">{zone.types}</div>

      {/* Agent pills */}
      <div className="flex flex-wrap gap-1 justify-center">
        {zone.agents.map(a => (
          <span key={a} className="text-[8px] px-1.5 py-0.5 rounded-full bg-white/5 text-slate-500 border border-white/8">
            {a}
          </span>
        ))}
      </div>

      {/* Uploaded file chips */}
      {hasFiles && (
        <div className="mt-3 flex flex-wrap gap-1 justify-center">
          {files.map((f, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded bg-green-500/10 border border-green-500/20 text-green-400"
              onClick={e => { e.stopPropagation(); onRemove(i) }}
            >
              {f.name.length > 14 ? f.name.slice(0, 12) + '…' : f.name}
              <span className="text-green-600 hover:text-red-400">×</span>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function Field({ label, required, hint, children }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
        {label}{required && <span className="text-gold ml-1">*</span>}
      </label>
      {children}
      {hint && <span className="text-[10px] text-slate-500">{hint}</span>}
    </div>
  )
}

const inputCls = "w-full bg-[#0f1117] border border-white/10 rounded-lg px-3 py-2 text-white text-[13px] outline-none focus:border-gold/40 transition-colors"

export default function SmartIntake({ onAnalyze, onDemo, error }) {
  // Section 1 — Identity
  const [companyName, setCompanyName] = useState('')
  const [entityType, setEntityType] = useState('')
  const [industryKey, setIndustryKey] = useState('general')
  const [cipcNumber, setCipcNumber] = useState('')
  const [country, setCountry] = useState('South Africa')
  const [yearsInBusiness, setYearsInBusiness] = useState('')

  // Section 2 — Financial & Tax
  const [annualRevenue, setAnnualRevenue] = useState('')
  const [currency, setCurrency] = useState('ZAR')
  const [headcount, setHeadcount] = useState('')
  const [vatRegistered, setVatRegistered] = useState('unknown')
  const [vatNumber, setVatNumber] = useState('')
  const [taxYearEnd, setTaxYearEnd] = useState('')
  const [bbbeeLevel, setBbbeeLevel] = useState('')

  // Section 3 — Documents (per zone)
  const [docFiles, setDocFiles] = useState({
    financial: [], bank: [], tax: [], legal: [], hr: [], business_plan: [],
  })
  const [missingRequired, setMissingRequired] = useState(false)

  // Section 4 — Context
  const [primaryConcern, setPrimaryConcern] = useState('')
  const [bankingPartner, setBankingPartner] = useState('')
  const [reportAudience, setReportAudience] = useState('owner')

  const [submitting, setSubmitting] = useState(false)

  const addFiles = (zone, newFiles) => {
    setDocFiles(prev => ({
      ...prev,
      [zone]: [...prev[zone], ...newFiles],
    }))
    setMissingRequired(false)
  }

  const removeFile = (zone, idx) => {
    setDocFiles(prev => ({
      ...prev,
      [zone]: prev[zone].filter((_, i) => i !== idx),
    }))
  }

  const totalFiles = Object.values(docFiles).flat().length
  const hasFinancial = docFiles.financial.length > 0 || docFiles.bank.length > 0

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!companyName.trim()) return
    if (!hasFinancial) {
      setMissingRequired(true)
      document.getElementById('doc-zones')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }

    setSubmitting(true)

    // Build flat arrays: files + matching category labels
    const allFiles = []
    const allCategories = []
    for (const [zone, files] of Object.entries(docFiles)) {
      for (const f of files) {
        allFiles.push(f)
        allCategories.push(zone)
      }
    }

    const profile = {
      company_name: companyName.trim(),
      industry_key: industryKey,
      annual_revenue: parseFloat(annualRevenue.replace(/[^\d.]/g, '')) || 0,
      headcount: parseInt(headcount) || 0,
      currency,
      country,
      primary_concern: primaryConcern,
      entity_type: entityType,
      cipc_number: cipcNumber,
      vat_registered: vatRegistered,
      vat_number: vatNumber,
      tax_year_end: taxYearEnd,
      years_in_business: yearsInBusiness,
      bbbee_level: bbbeeLevel,
      banking_partner: bankingPartner,
      report_audience: reportAudience,
      file_categories: JSON.stringify(allCategories),
    }

    try {
      await onAnalyze(allFiles, profile)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-3xl mx-auto pb-16">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-black text-white mb-2">Business Profile</h1>
        <p className="text-slate-400 text-sm">
          Fill in what you have — the more context you provide, the more targeted the analysis.
          At minimum, upload one financial document to get started.
        </p>
      </div>

      {/* ── Section 1: Business Identity ── */}
      <div className="bg-[#161b27] border border-white/8 rounded-2xl p-6 mb-4">
        <h2 className="text-[13px] font-bold text-white mb-5 flex items-center gap-2">
          <span className="w-5 h-5 rounded-full bg-gold text-navy text-[10px] font-black flex items-center justify-center">1</span>
          Business Identity
        </h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <Field label="Company Name" required>
              <input
                className={inputCls}
                placeholder="e.g. Mzansi Trading (Pty) Ltd"
                value={companyName}
                onChange={e => setCompanyName(e.target.value)}
                required
              />
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
            <input
              className={inputCls}
              placeholder="e.g. 2015/123456/07"
              value={cipcNumber}
              onChange={e => setCipcNumber(e.target.value)}
            />
          </Field>
          <Field label="Country">
            <input className={inputCls} value={country} onChange={e => setCountry(e.target.value)} />
          </Field>
          <Field label="Years in Business" hint="Calibrates benchmarks and unlocks business plan zone">
            <select className={inputCls} value={yearsInBusiness} onChange={e => setYearsInBusiness(e.target.value)}>
              <option value="">Select...</option>
              {YEARS_OPTIONS.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </Field>
        </div>
      </div>

      {/* ── Section 2: Financial & Tax ── */}
      <div className="bg-[#161b27] border border-white/8 rounded-2xl p-6 mb-4">
        <h2 className="text-[13px] font-bold text-white mb-5 flex items-center gap-2">
          <span className="w-5 h-5 rounded-full bg-gold text-navy text-[10px] font-black flex items-center justify-center">2</span>
          Financial & Tax Profile
        </h2>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Annual Revenue (approx.)">
            <input
              className={inputCls}
              placeholder="e.g. 6 000 000"
              value={annualRevenue}
              onChange={e => setAnnualRevenue(e.target.value)}
            />
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
            <input
              className={inputCls}
              type="number"
              placeholder="e.g. 25"
              value={headcount}
              onChange={e => setHeadcount(e.target.value)}
            />
          </Field>
          <Field label="VAT Registered?">
            <select className={inputCls} value={vatRegistered} onChange={e => setVatRegistered(e.target.value)}>
              <option value="unknown">Unknown</option>
              <option value="yes">Yes</option>
              <option value="no">No</option>
              <option value="pending">Pending registration</option>
            </select>
          </Field>
          <Field label="VAT Number" hint="10-digit SARS vendor number">
            <input
              className={inputCls}
              placeholder="e.g. 4123456789"
              value={vatNumber}
              onChange={e => setVatNumber(e.target.value)}
              disabled={vatRegistered !== 'yes'}
            />
          </Field>
          <Field label="Tax Year-End Month">
            <select className={inputCls} value={taxYearEnd} onChange={e => setTaxYearEnd(e.target.value)}>
              <option value="">Select month...</option>
              {TAX_YEAR_ENDS.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </Field>
        </div>

        {/* BBBEE */}
        <div className="mt-5 pt-4 border-t border-white/6">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">BBBEE Level</div>
          <div className="flex flex-wrap gap-2">
            {BBBEE_LEVELS.map(lvl => (
              <button
                key={lvl}
                type="button"
                className={`text-[11px] px-3 py-1.5 rounded-lg border transition-all ${
                  bbbeeLevel === lvl
                    ? 'border-gold/50 bg-gold/10 text-gold'
                    : 'border-white/10 bg-[#0f1117] text-slate-400 hover:border-white/20'
                }`}
                onClick={() => setBbbeeLevel(bbbeeLevel === lvl ? '' : lvl)}
              >
                {lvl}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Section 3: Document Upload ── */}
      <div className="bg-[#161b27] border border-white/8 rounded-2xl p-6 mb-4" id="doc-zones">
        <h2 className="text-[13px] font-bold text-white mb-1 flex items-center gap-2">
          <span className="w-5 h-5 rounded-full bg-gold text-navy text-[10px] font-black flex items-center justify-center">3</span>
          Document Upload
          {totalFiles > 0 && (
            <span className="ml-auto text-[11px] text-green-400 font-normal">{totalFiles} file{totalFiles !== 1 ? 's' : ''} uploaded</span>
          )}
        </h2>
        <p className="text-[11px] text-slate-400 mb-4">
          Each zone routes documents to the specialist agent best equipped to analyse them.
          At least one financial document (Financial Records or Bank Statements) is required.
        </p>

        {missingRequired && (
          <div className="mb-4 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-[12px] text-red-400">
            Please upload at least one Financial Record or Bank Statement to continue.
          </div>
        )}

        <div className="grid grid-cols-3 gap-3">
          {DOC_ZONES.map(zone => (
            <DocZone
              key={zone.id}
              zone={zone}
              files={docFiles[zone.id]}
              onAdd={files => addFiles(zone.id, files)}
              onRemove={idx => removeFile(zone.id, idx)}
              highlight={missingRequired && zone.required && docFiles[zone.id].length === 0}
            />
          ))}
        </div>

        {/* New-business plan nudge */}
        {yearsInBusiness && (yearsInBusiness === 'Less than 1 year' || yearsInBusiness === '1–3 years') && docFiles.business_plan.length === 0 && (
          <div className="mt-3 px-3 py-2 rounded-lg bg-gold/5 border border-gold/20 text-[11px] text-gold">
            💡 We noticed your business is under 3 years old — uploading your Business Plan unlocks deeper strategy and valuation insights.
          </div>
        )}
      </div>

      {/* ── Section 4: Context & Focus ── */}
      <div className="bg-[#161b27] border border-white/8 rounded-2xl p-6 mb-6">
        <h2 className="text-[13px] font-bold text-white mb-5 flex items-center gap-2">
          <span className="w-5 h-5 rounded-full bg-gold text-navy text-[10px] font-black flex items-center justify-center">4</span>
          Context & Focus
        </h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <Field label="Primary Concern" hint="Agents will prioritise this. Be specific — good answers unlock better findings.">
              <textarea
                className={`${inputCls} h-20 resize-none`}
                placeholder="e.g. Our margins are shrinking every month but we can't identify why. Cash is also tight and we struggle to pay suppliers on time."
                value={primaryConcern}
                onChange={e => setPrimaryConcern(e.target.value)}
              />
            </Field>
          </div>
          <Field label="Main Banking Partner" hint="Aligns credit readiness findings to your lender's criteria">
            <select className={inputCls} value={bankingPartner} onChange={e => setBankingPartner(e.target.value)}>
              <option value="">Select bank...</option>
              {BANKS.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </Field>
          <Field label="Who is this report for?">
            <div className="flex gap-2">
              {[
                { val: 'owner', label: '👤 Business Owner', desc: 'Operational focus' },
                { val: 'banker', label: '🏦 Bank / Funder', desc: 'Credit focus' },
                { val: 'investor', label: '📈 Investor', desc: 'Valuation focus' },
              ].map(opt => (
                <button
                  key={opt.val}
                  type="button"
                  className={`flex-1 p-2 rounded-lg border text-left transition-all ${
                    reportAudience === opt.val
                      ? 'border-gold/50 bg-gold/8 text-gold'
                      : 'border-white/10 text-slate-400 hover:border-white/20'
                  }`}
                  onClick={() => setReportAudience(opt.val)}
                >
                  <div className="text-[11px] font-bold">{opt.label}</div>
                  <div className="text-[9px] opacity-60">{opt.desc}</div>
                </button>
              ))}
            </div>
          </Field>
        </div>
      </div>

      {/* Agents summary */}
      <div className="bg-gold/4 border border-gold/15 rounded-2xl p-4 mb-6">
        <div className="text-[11px] font-bold text-white mb-2">⚡ 17 Specialist Agents Will Run</div>
        <div className="flex flex-wrap gap-1.5">
          {[
            'CEO Synthesiser','Financial Forensics','Accounting','Auditor',
            'Operations','Logistics','Sales','Marketing','HR','Procurement',
            'Strategy','Legal Risk','Fraud Detection','Credit Readiness',
            'Valuation','Market Research',
          ].map(a => (
            <span key={a} className="text-[9px] px-2 py-0.5 rounded-full bg-white/5 border border-white/8 text-slate-400">{a}</span>
          ))}
          <span className="text-[9px] px-2 py-0.5 rounded-full bg-gold/10 border border-gold/25 text-gold font-bold">✦ SA Tax Compliance</span>
          <span className="text-[9px] px-2 py-0.5 rounded-full bg-gold/10 border border-gold/25 text-gold font-bold">✦ SA Corporate Law & BBBEE</span>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/30 text-[13px] text-red-400">
          {error}
        </div>
      )}

      {/* CTA */}
      <div className="flex items-center gap-4">
        <button
          type="submit"
          disabled={submitting || !companyName.trim()}
          className="bg-gold text-navy font-black text-[14px] px-8 py-3 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed hover:bg-amber-400 transition-colors"
        >
          {submitting ? 'Starting analysis…' : 'Run Analysis →'}
        </button>
        <button
          type="button"
          onClick={onDemo}
          className="border border-white/10 text-slate-400 text-[13px] px-5 py-3 rounded-xl hover:border-white/20 transition-colors"
        >
          ⚡ Try Demo
        </button>
        <span className="text-[11px] text-slate-500">
          {hasFinancial ? `${totalFiles} file${totalFiles !== 1 ? 's' : ''} ready` : 'Upload at least 1 financial document'}
        </span>
      </div>
    </form>
  )
}
