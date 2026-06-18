import { useState } from 'react'

const INDUSTRIES = [
  { value: 'retail', label: 'Retail & E-commerce' },
  { value: 'logistics', label: 'Logistics & Transport' },
  { value: 'manufacturing', label: 'Manufacturing' },
  { value: 'services', label: 'Professional Services' },
  { value: 'hospitality', label: 'Hospitality & Tourism' },
  { value: 'agriculture', label: 'Agriculture & Agriprocessing' },
  { value: 'technology', label: 'Technology & Software' },
  { value: 'healthcare', label: 'Healthcare & Pharma' },
  { value: 'construction', label: 'Construction & Property' },
  { value: 'general', label: 'Other / General Business' },
]

const CURRENCIES = [
  { value: 'ZAR', label: 'ZAR — South African Rand' },
  { value: 'USD', label: 'USD — US Dollar' },
  { value: 'EUR', label: 'EUR — Euro' },
  { value: 'GBP', label: 'GBP — British Pound' },
  { value: 'KES', label: 'KES — Kenyan Shilling' },
  { value: 'NGN', label: 'NGN — Nigerian Naira' },
  { value: 'GHS', label: 'GHS — Ghanaian Cedi' },
  { value: 'AUD', label: 'AUD — Australian Dollar' },
]

const AGENTS = [
  { icon: '💼', name: 'CEO', desc: 'Orchestrates & synthesises' },
  { icon: '💰', name: 'Financial Forensics', desc: 'Margin & cash analysis' },
  { icon: '📊', name: 'Accounting', desc: 'Books & reconciliation' },
  { icon: '🔍', name: 'Auditor', desc: 'Compliance & controls' },
  { icon: '⚙️', name: 'Operations', desc: 'Process efficiency' },
  { icon: '🚚', name: 'Logistics', desc: 'Supply chain & delivery' },
  { icon: '📈', name: 'Sales', desc: 'Revenue & pipeline' },
  { icon: '📣', name: 'Marketing', desc: 'Brand & acquisition' },
  { icon: '👥', name: 'Human Resources', desc: 'People & productivity' },
  { icon: '🛒', name: 'Procurement', desc: 'Supplier & costs' },
  { icon: '♟️', name: 'Strategy', desc: 'Competitive positioning' },
]

const inputClass = `
  w-full bg-navy-light border border-white/10 rounded-xl px-4 py-3
  text-white text-sm placeholder-slate-500
  focus:outline-none focus:border-gold/50 focus:ring-1 focus:ring-gold/20
  transition-colors
`

export default function BusinessProfile({ onComplete, onDemo }) {
  const [form, setForm] = useState({
    company_name: '',
    industry_key: '',
    annual_revenue: '',
    headcount: '',
    currency: 'ZAR',
    country: '',
    primary_concern: '',
  })
  const [errors, setErrors] = useState({})

  const set = (k, v) => {
    setForm(f => ({ ...f, [k]: v }))
    if (errors[k]) setErrors(e => ({ ...e, [k]: '' }))
  }

  const validate = () => {
    const e = {}
    if (!form.company_name.trim()) e.company_name = 'Company name is required'
    if (!form.industry_key) e.industry_key = 'Please select an industry'
    return e
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length) { setErrors(errs); return }
    onComplete({
      ...form,
      annual_revenue: parseFloat(form.annual_revenue) || 0,
      headcount: parseInt(form.headcount) || 0,
    })
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Hero */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 bg-gold/10 border border-gold/20 rounded-full px-4 py-1.5 mb-4">
          <div className="w-1.5 h-1.5 rounded-full bg-gold" />
          <span className="text-gold text-xs font-semibold tracking-wider">AI-POWERED DIAGNOSIS</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-white mb-3 leading-tight">
          Imara
        </h1>
        <p className="text-slate-400 text-sm sm:text-base max-w-xl mx-auto leading-relaxed">
          11 specialist AI agents analyse your financial data and produce a board-ready consulting report — in minutes.
        </p>
      </div>

      {/* Form card */}
      <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-6 sm:p-8 mb-6">
        <h2 className="text-white font-semibold text-base mb-6 flex items-center gap-2">
          <span className="w-6 h-6 rounded-full bg-gold text-navy text-xs font-bold flex items-center justify-center">1</span>
          Business Profile
        </h2>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {/* Company name */}
            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Company Name *</label>
              <input
                type="text"
                placeholder="e.g. Acme Trading Co"
                value={form.company_name}
                onChange={e => set('company_name', e.target.value)}
                className={inputClass + (errors.company_name ? ' border-red-500/50' : '')}
              />
              {errors.company_name && <p className="text-red-400 text-xs mt-1">{errors.company_name}</p>}
            </div>

            {/* Industry */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Industry *</label>
              <select
                value={form.industry_key}
                onChange={e => set('industry_key', e.target.value)}
                className={inputClass + ' appearance-none' + (errors.industry_key ? ' border-red-500/50' : '')}
              >
                <option value="">Select industry...</option>
                {INDUSTRIES.map(i => (
                  <option key={i.value} value={i.value}>{i.label}</option>
                ))}
              </select>
              {errors.industry_key && <p className="text-red-400 text-xs mt-1">{errors.industry_key}</p>}
            </div>

            {/* Country */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Country</label>
              <input
                type="text"
                placeholder="e.g. South Africa"
                value={form.country}
                onChange={e => set('country', e.target.value)}
                className={inputClass}
              />
            </div>

            {/* Currency */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Currency</label>
              <select
                value={form.currency}
                onChange={e => set('currency', e.target.value)}
                className={inputClass + ' appearance-none'}
              >
                {CURRENCIES.map(c => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>

            {/* Annual Revenue */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                Annual Revenue <span className="text-slate-600">(approx.)</span>
              </label>
              <input
                type="number"
                placeholder="e.g. 6000000"
                value={form.annual_revenue}
                onChange={e => set('annual_revenue', e.target.value)}
                className={inputClass}
                min="0"
              />
            </div>

            {/* Headcount */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                Headcount <span className="text-slate-600">(employees)</span>
              </label>
              <input
                type="number"
                placeholder="e.g. 25"
                value={form.headcount}
                onChange={e => set('headcount', e.target.value)}
                className={inputClass}
                min="0"
              />
            </div>

            {/* Primary concern */}
            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                Primary Concern <span className="text-slate-600">(optional — agents will prioritise this)</span>
              </label>
              <textarea
                placeholder="e.g. Our margins are shrinking every month and we don't know why"
                value={form.primary_concern}
                onChange={e => set('primary_concern', e.target.value)}
                rows={2}
                className={inputClass + ' resize-none'}
              />
            </div>
          </div>

          <div className="pt-2 flex flex-wrap items-center gap-3">
            <button
              type="submit"
              className="bg-gold hover:bg-gold-light text-navy font-bold text-sm px-8 py-3 rounded-xl transition-colors"
            >
              Continue → Upload Files
            </button>
            {onDemo && (
              <button
                type="button"
                onClick={onDemo}
                className="border border-white/10 text-slate-400 hover:border-gold/30 hover:text-gold text-sm px-5 py-3 rounded-xl transition-colors"
              >
                ⚡ Try Demo — no files needed
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Agent cards */}
      <div>
        <p className="text-xs text-slate-500 text-center mb-4 tracking-wider uppercase">
          Your AI Consulting Team
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          {AGENTS.map(a => (
            <div key={a.name} className="bg-navy-card border border-white/[0.06] rounded-xl p-3 card-hover">
              <div className="text-lg mb-1">{a.icon}</div>
              <div className="text-white text-xs font-semibold">{a.name}</div>
              <div className="text-slate-500 text-xs mt-0.5">{a.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
