// Methodology & Confidence — a transparency panel. Research shows that disclosing
// how an analysis was produced, how confident it is, and what it could NOT verify
// raises trust rather than lowering it. All values come from the report itself.
import { ShieldCheck, AlertTriangle, Gauge, Database, Clock, Check, Minus, Coins } from 'lucide-react'
import InfoTip from './InfoTip'

const COVERAGE_LABELS = {
  financial: 'Financial Records', bank: 'Bank Statements', tax: 'Tax Documents',
  legal: 'Legal Documents', hr: 'HR & Payroll', business_plan: 'Business Plan',
}

function Stat({ Icon, label, value, tone = 'slate' }) {
  const toneCls = {
    emerald: 'text-emerald-400',
    amber: 'text-amber-400',
    red: 'text-red-400',
    gold: 'text-gold',
    slate: 'text-slate-200',
  }[tone] || 'text-slate-200'
  return (
    <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3">
      <div className="flex items-center gap-1.5 text-slate-400 text-[11px] uppercase tracking-wider mb-1">
        <Icon size={12} aria-hidden="true" /> {label}
      </div>
      <div className={`text-sm font-semibold ${toneCls}`}>{value}</div>
    </div>
  )
}

export default function MethodologyNote({ report }) {
  if (!report) return null
  const f = report.faithfulness_summary || {}
  const checked = Number(f.checked || 0)
  const confirmed = Number(f.confirmed || 0)
  const conflicts = Number(f.conflicts || 0)
  const conflictTitles = Array.isArray(f.conflict_titles) ? f.conflict_titles : []
  const benchChecked = Number(f.benchmark_checked || 0)
  const benchConflicts = Number(f.benchmark_conflicts || 0)
  const benchConflictTitles = Array.isArray(f.benchmark_conflict_titles) ? f.benchmark_conflict_titles : []
  const completeness = typeof report.imara_completeness === 'number' ? report.imara_completeness : null
  const confidence = report.imara_confidence || null
  const runtime = report.total_runtime_seconds
  const runtimeLabel = runtime ? (runtime >= 60 ? `${Math.round(runtime / 60)}m ${Math.round(runtime % 60)}s` : `${Math.round(runtime)}s`) : null
  const confTone = confidence === 'high' ? 'emerald' : confidence === 'medium' ? 'amber' : 'slate'
  const usage = report.llm_usage || {}
  const aiCost = typeof usage.est_cost_usd === 'number' ? usage.est_cost_usd : null

  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 sm:p-6">
      <h3 className="text-white font-bold text-lg flex items-center gap-1.5 mb-2">
        Methodology &amp; Confidence
        <InfoTip label="Methodology" text="How this analysis was produced and how far to trust it. Financial ratios are computed by arithmetic from your statements; AI specialists add context and recommendations; every AI-cited figure is cross-checked against the computed ratios." />
      </h3>
      <p className="text-slate-300 text-sm leading-relaxed mb-4">
        Imara blends two layers: a <span className="text-white">deterministic engine</span> that computes financial ratios
        directly from your statements (arithmetic, not AI), and a panel of <span className="text-white">AI specialist agents</span> that
        add interpretation, benchmarks and recommendations. Every figure an agent cites is automatically
        cross-checked against the computed ratios, and any mismatch is flagged.
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-4">
        {confidence && <Stat Icon={Gauge} label="Confidence" value={confidence.charAt(0).toUpperCase() + confidence.slice(1)} tone={confTone} />}
        {completeness != null && <Stat Icon={Database} label="Data completeness" value={`${completeness}% of signals`} tone={completeness >= 80 ? 'emerald' : completeness >= 50 ? 'amber' : 'red'} />}
        {checked > 0 && <Stat Icon={ShieldCheck} label="Figures checked" value={`${checked}`} tone="slate" />}
        {checked > 0 && <Stat Icon={ShieldCheck} label="Confirmed" value={`${confirmed}`} tone="emerald" />}
        {checked > 0 && <Stat Icon={AlertTriangle} label="Conflicts" value={`${conflicts}`} tone={conflicts > 0 ? 'amber' : 'emerald'} />}
        {benchChecked > 0 && <Stat Icon={AlertTriangle} label="Benchmarks checked" value={`${benchChecked - benchConflicts}/${benchChecked} ok`} tone={benchConflicts > 0 ? 'amber' : 'emerald'} />}
        {runtimeLabel && <Stat Icon={Clock} label="Analysis time" value={runtimeLabel} tone="slate" />}
        {aiCost != null && <Stat Icon={Coins} label="AI cost (est.)" value={`$${aiCost.toFixed(2)}${usage.calls ? ` \u00b7 ${usage.calls} calls` : ''}`} tone="slate" />}
      </div>

      {conflicts > 0 && conflictTitles.length > 0 && (
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-3 mb-4">
          <div className="text-amber-300 text-xs font-medium mb-1 flex items-center gap-1.5">
            <AlertTriangle size={13} aria-hidden="true" /> Figures flagged for verification
          </div>
          <ul className="text-slate-300 text-xs space-y-0.5 list-disc list-inside">
            {conflictTitles.slice(0, 6).map((t, i) => <li key={i}>{t}</li>)}
          </ul>
        </div>
      )}

      {benchConflicts > 0 && benchConflictTitles.length > 0 && (
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-3 mb-4">
          <div className="text-amber-300 text-xs font-medium mb-1 flex items-center gap-1.5">
            <AlertTriangle size={13} aria-hidden="true" /> Findings citing a sector benchmark that differs from the engine
          </div>
          <ul className="text-slate-300 text-xs space-y-0.5 list-disc list-inside">
            {benchConflictTitles.slice(0, 6).map((t, i) => <li key={i}>{t}</li>)}
          </ul>
        </div>
      )}

      {report.financial_extraction_source === 'ai' && (
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-3 mb-4 text-xs text-amber-200/90 leading-relaxed">
          <span className="font-semibold text-amber-300">Note on the figures:</span> the financial numbers were
          AI-extracted from an unstructured document (the deterministic parser could not read it directly), so the
          computed ratios carry lower confidence — verify them against your statements before relying on them.
        </div>
      )}

      {report.document_coverage && (
        <div className="mb-4">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-2">Documents analysed</div>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(COVERAGE_LABELS).map(([k, label]) => {
              const has = !!report.document_coverage[k]
              return (
                <span key={k}
                  className={`inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full border ${has ? 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20' : 'bg-white/[0.03] text-slate-500 border-white/10'}`}
                  aria-label={`${label}: ${has ? 'provided' : 'not provided'}`}>
                  {has ? <Check size={11} aria-hidden="true" /> : <Minus size={11} aria-hidden="true" />} {label}
                </span>
              )
            })}
          </div>
        </div>
      )}

      {report.cross_agent_consistency?.available && (
        <div className="mb-4">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
            Cross-agent corroboration
            <InfoTip label="Why it matters" text="Issues independently flagged by several specialist agents are the most credible. This is a deterministic cross-check, not an extra AI opinion, and it does not change the Imara Score." />
          </div>
          <p className="text-slate-300 text-xs mb-2 leading-relaxed">{report.cross_agent_consistency.summary}</p>
          <div className="space-y-1.5">
            {(report.cross_agent_consistency.corroborated || []).slice(0, 5).map((c, i) => (
              <div key={i} className="flex items-start justify-between gap-3 bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-1.5">
                <span className="text-white text-xs font-medium">{c.topic}</span>
                <span className="shrink-0 text-[10px] text-slate-400">{c.agent_count} agents · <span className={c.severity === 'critical' ? 'text-red-400' : c.severity === 'high' ? 'text-amber-400' : 'text-slate-300'}>{c.severity}</span></span>
              </div>
            ))}
          </div>
          {Array.isArray(report.cross_agent_consistency.diverging) && report.cross_agent_consistency.diverging.length > 0 && (
            <p className="text-amber-300/80 text-[11px] mt-2 leading-relaxed">
              ⚠ Severity divergence to reconcile: {report.cross_agent_consistency.diverging.map(d => d.topic).join(', ')}.
            </p>
          )}
        </div>
      )}

      {(report.input_security?.injection_detected || report.input_security?.pii_redacted > 0) && (
        <div className="mb-4">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
            Input security
            <InfoTip label="Why it matters" text="Uploaded documents are scanned before any agent reads them: instructions planted in a document to manipulate the analysis are neutralised, and obvious personal data (emails, ID/card numbers) is redacted. Deterministic - figures are never altered, and the Score is unaffected." />
          </div>
          <div className="flex flex-wrap gap-1.5">
            {report.input_security.injection_detected && (
              <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full border bg-amber-400/10 text-amber-300 border-amber-400/25">
                {report.input_security.injection_count} injected instruction{report.input_security.injection_count === 1 ? '' : 's'} neutralised
              </span>
            )}
            {report.input_security.pii_redacted > 0 && (
              <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full border bg-white/[0.03] text-slate-400 border-white/10">
                {report.input_security.pii_redacted} PII item{report.input_security.pii_redacted === 1 ? '' : 's'} redacted
              </span>
            )}
          </div>
        </div>
      )}

      <div className="text-slate-400 text-xs leading-relaxed">
        <span className="text-slate-300 font-medium">What this is — and isn&apos;t.</span> This report is decision-support, not
        a substitute for a registered auditor, business valuator, or tax practitioner.
        {completeness != null && completeness < 100 && ' A completeness below 100% means some inputs (e.g. bank statements, tax or legal documents) were not provided, so parts of the analysis are estimated from what was available.'}
        {' '}Indicative valuations and forecasts should be confirmed by a qualified professional before you rely on them.
      </div>
    </div>
  )
}
