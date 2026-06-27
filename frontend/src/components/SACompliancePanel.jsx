/**
 * SACompliancePanel — displays SA Tax + SA Legal findings in the Dashboard.
 * Shows only when sa_tax_performed or sa_legal_performed is true.
 */

function StatusBadge({ status, label }) {
  const colors = {
    compliant:     'bg-green-500/15 text-green-400 border-green-500/30',
    valid:         'bg-green-500/15 text-green-400 border-green-500/30',
    risk:          'bg-red-500/15 text-red-400 border-red-500/30',
    expired:       'bg-red-500/15 text-red-400 border-red-500/30',
    overdue:       'bg-red-500/15 text-red-400 border-red-500/30',
    not_provided:  'bg-slate-500/15 text-slate-400 border-slate-500/30',
    unknown:       'bg-slate-500/15 text-slate-400 border-slate-500/30',
    pending:       'bg-amber-500/15 text-amber-400 border-amber-500/30',
  }
  const cls = colors[status] || colors.unknown
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${cls}`}>
      {label || status}
    </span>
  )
}

function RiskBar({ score, label }) {
  const pct = Math.min(100, Math.max(0, score))
  const color = pct >= 70 ? '#ef4444' : pct >= 40 ? '#f59e0b' : '#22c55e'
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-[11px] text-slate-400">{label}</span>
        <span className="text-[11px] font-bold" style={{ color }}>{pct}/100</span>
      </div>
      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  )
}

function BBBEECard({ bbbeeAnalysis, bbbeeLevel }) {
  if (!bbbeeAnalysis && !bbbeeLevel) return null
  const declared = bbbeeLevel || bbbeeAnalysis?.declared_level || 'Not specified'
  const riskFlags = bbbeeAnalysis?.risk_flags || []
  const findingCount = bbbeeAnalysis?.finding_count || 0

  const levelColor = declared.includes('1') || declared.includes('EME') ? 'text-green-400'
    : declared.includes('Non-Compliant') ? 'text-red-400'
    : 'text-amber-400'

  return (
    <div className="bg-[#0f1117] border border-white/8 rounded-xl p-4">
      <div className="text-[11px] font-bold text-slate-300 mb-3 flex items-center gap-2">
        🏛 BBBEE Status
      </div>
      <div className="flex items-baseline gap-2 mb-2">
        <span className={`text-lg font-black ${levelColor}`}>{declared}</span>
      </div>
      {findingCount > 0 && (
        <div className="text-[11px] text-amber-400 mb-2">{findingCount} compliance finding{findingCount !== 1 ? 's' : ''} identified</div>
      )}
      {riskFlags.length > 0 && (
        <ul className="space-y-1">
          {riskFlags.slice(0, 3).map((flag, i) => (
            <li key={i} className="text-[10px] text-slate-400 flex gap-1.5">
              <span className="text-amber-400 flex-shrink-0">⚠</span>
              {flag}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function SACompliancePanel({ report }) {
  const taxPerformed = report?.sa_tax_performed
  const legalPerformed = report?.sa_legal_performed

  if (!taxPerformed && !legalPerformed) return null

  const taxScore      = report?.sa_tax_risk_score || 0
  const legalScore    = report?.sa_legal_risk_score || 0
  const vatStatus     = report?.sa_vat_status || 'unknown'
  const taxClearance  = report?.sa_tax_clearance_status || 'unknown'
  const cipcStatus    = report?.sa_cipc_status || 'unknown'
  const taxSummary    = report?.sa_tax_summary || ''
  const legalSummary  = report?.sa_legal_summary || ''
  const bbbeeAnalysis = report?.sa_bbbee_analysis || {}
  const bbbeeLevel    = report?.bbbee_level || ''
  const assurance     = report?.assurance || null
  const calendar      = report?.compliance_calendar || null
  const tcs           = report?.tcs_status || null

  // Pull SA findings from all_findings_ranked
  const allFindings = report?.all_findings_ranked || []
  const taxFindings   = allFindings.filter(f => f.agent === 'SA Tax Compliance Agent')
  const legalFindings = allFindings.filter(f => f.agent === 'SA Corporate Law & BBBEE Agent')

  const sevColor = { critical: 'text-red-400', high: 'text-orange-400', medium: 'text-amber-400', low: 'text-slate-400' }

  return (
    <div className="mt-6 space-y-4">
      <h2 className="text-lg font-bold text-white flex items-center gap-2">
        🇿🇦 SA Compliance Intelligence
        <span className="text-[11px] text-slate-400 font-normal">Companies Act · BBBEE · SARS · POPIA</span>
      </h2>

      {/* Risk score bars */}
      <div className="bg-[#161b27] border border-white/8 rounded-2xl p-5">
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-3">
            <RiskBar score={taxScore} label="SA Tax Risk Score" />
            <div className="flex flex-wrap gap-2 pt-1">
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] text-slate-400">VAT Status</span>
                <StatusBadge status={vatStatus} label={vatStatus === 'compliant' ? '✓ Compliant' : vatStatus === 'risk' ? '⚠ Risk' : 'Unknown'} />
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] text-slate-400">Tax Clearance</span>
                <StatusBadge status={taxClearance} label={taxClearance === 'valid' ? '✓ Valid' : taxClearance === 'expired' ? '✗ Expired' : taxClearance === 'not_provided' ? 'Not provided' : 'Unknown'} />
              </div>
            </div>
            {taxSummary && (
              <p className="text-[11px] text-slate-400 pt-1 border-t border-white/5">{taxSummary}</p>
            )}
          </div>
          <div className="space-y-3">
            <RiskBar score={legalScore} label="SA Legal Risk Score" />
            <div className="flex flex-wrap gap-2 pt-1">
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] text-slate-400">CIPC Standing</span>
                <StatusBadge status={cipcStatus} label={cipcStatus === 'compliant' ? '✓ Good standing' : cipcStatus === 'overdue' ? '✗ Overdue' : 'Unknown'} />
              </div>
            </div>
            {legalSummary && (
              <p className="text-[11px] text-slate-400 pt-1 border-t border-white/5">{legalSummary}</p>
            )}
          </div>
        </div>
      </div>

      {assurance?.available && (
        <div className="bg-[#161b27] border border-white/8 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="text-[13px] font-bold text-white flex items-center gap-2">
              📋 Assurance Requirement &amp; CIPC
              <span className="text-[10px] text-slate-400 font-normal">Companies Act · Public Interest Score</span>
            </div>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
              assurance.recommended_tier === 'audit' ? 'bg-red-500/15 text-red-400 border-red-500/30'
              : assurance.recommended_tier === 'compilation' ? 'bg-green-500/15 text-green-400 border-green-500/30'
              : 'bg-amber-500/15 text-amber-400 border-amber-500/30'}`}>
              {assurance.recommended_tier?.toUpperCase()}{assurance.is_mandatory ? ' (required)' : ''}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-[#0f1117] border border-white/8 rounded-xl p-3 text-center">
              <div className="text-[10px] text-slate-400 mb-1">Public Interest Score</div>
              <div className="text-2xl font-black text-white">{assurance.public_interest_score}</div>
              <div className="text-[9px] text-slate-500 mt-1">
                emp {assurance.pis_breakdown?.employees} · turnover {assurance.pis_breakdown?.turnover_Rm} · liab {assurance.pis_breakdown?.third_party_liabilities_Rm}
              </div>
            </div>
            <div className="col-span-2 space-y-2">
              <p className="text-[11px] text-slate-300">{assurance.reasoning}</p>
              {(assurance.notes || []).map((nt, i) => (
                <p key={i} className="text-[10px] text-amber-300/90">• {nt}</p>
              ))}
              {assurance.potential_saving && (
                <p className="text-[10px] text-green-400 font-semibold">💰 {assurance.potential_saving}</p>
              )}
            </div>
          </div>
          {assurance.cipc?.flag && (
            <p className="text-[10px] text-slate-400 mt-3 pt-2 border-t border-white/5">🏛 CIPC: {assurance.cipc.flag}</p>
          )}
          <p className="text-[9px] text-slate-600 mt-2">{assurance.disclaimer}</p>
        </div>
      )}

      {calendar?.available && (
        <div className="bg-[#161b27] border border-white/8 rounded-2xl p-5">
          <div className="text-[13px] font-bold text-white flex items-center gap-2 mb-3">
            📅 Compliance Calendar
            <span className="text-[10px] text-slate-400 font-normal">{calendar.count} obligations · SARS · CIPC · POPIA · B-BBEE</span>
          </div>
          {calendar.free_quick_wins?.length > 0 && (
            <div className="mb-3 bg-green-500/5 border border-green-500/25 rounded-xl p-3">
              <div className="text-[10px] uppercase tracking-wider text-green-400 mb-1">Free quick wins most SMEs miss</div>
              {calendar.free_quick_wins.map((w, i) => (
                <div key={i} className="text-[11px] text-slate-300"><span className="text-green-400 font-semibold">{w.title}:</span> {w.action}</div>
              ))}
            </div>
          )}
          <div className="space-y-1.5">
            {calendar.obligations.map((o, i) => {
              const col = o.priority === 'critical' ? 'text-red-400 border-red-500/30' : o.priority === 'high' ? 'text-orange-400 border-orange-500/30' : o.priority === 'medium' ? 'text-amber-400 border-amber-500/30' : 'text-slate-400 border-white/15'
              return (
                <div key={i} className="flex items-start justify-between gap-3 border-b border-white/5 pb-1.5 last:border-0">
                  <div className="flex-1">
                    <span className="text-[12px] text-white font-medium">{o.title}</span>
                    {o.free && <span className="ml-1.5 text-[9px] text-green-400 font-bold">FREE</span>}
                    <div className="text-[10px] text-slate-500">{o.authority} · {o.cadence} · {o.timing}</div>
                  </div>
                  <span className={`shrink-0 text-[9px] uppercase font-bold border rounded-full px-2 py-0.5 ${col}`}>{o.priority}</span>
                </div>
              )
            })}
          </div>
          <p className="text-[9px] text-slate-600 mt-2">{calendar.note}</p>
        </div>
      )}

      {tcs?.available && (() => {
        const pillarMeta = {
          registration: 'Registration',
          submission: 'Submission of returns',
          debt: 'Outstanding debt',
          relevant_material: 'Relevant material',
        }
        const pillCol = { pass: 'text-green-400 border-green-500/30', action: 'text-red-400 border-red-500/30', verify: 'text-amber-400 border-amber-500/30' }
        const pillLabel = { pass: '✓ Clear', action: '✗ Action', verify: '? Verify' }
        const overallCol = tcs.overall === 'action_required' ? 'bg-red-500/15 text-red-400 border-red-500/30'
          : tcs.overall === 'likely_compliant' ? 'bg-green-500/15 text-green-400 border-green-500/30'
          : 'bg-amber-500/15 text-amber-400 border-amber-500/30'
        return (
          <div className="bg-[#161b27] border border-white/8 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[13px] font-bold text-white flex items-center gap-2">
                ✅ Tax Compliance Status (TCS)
                <span className="text-[10px] text-slate-400 font-normal">SARS eFiling · 4 pillars · bankability gate</span>
              </div>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${overallCol}`}>
                {tcs.overall?.replace(/_/g, ' ').toUpperCase()}
              </span>
            </div>
            <p className="text-[11px] text-slate-300 mb-3">{tcs.verdict}</p>
            <div className="grid grid-cols-2 gap-2 mb-3">
              {Object.entries(tcs.pillars).map(([key, p]) => (
                <div key={key} className="bg-[#0f1117] border border-white/8 rounded-xl p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[11px] font-semibold text-slate-300">{pillarMeta[key] || key}</span>
                    <span className={`text-[9px] font-bold border rounded-full px-2 py-0.5 ${pillCol[p.status] || pillCol.verify}`}>{pillLabel[p.status] || p.status}</span>
                  </div>
                  <p className="text-[10px] text-slate-500">{p.detail}</p>
                  {key === 'registration' && p.required?.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {p.required.map((r, i) => (
                        <span key={i} className={`text-[9px] px-1.5 py-0.5 rounded border ${r.satisfied === false ? 'text-red-400 border-red-500/30' : r.satisfied === true ? 'text-green-400 border-green-500/30' : 'text-slate-400 border-white/15'}`}>{r.tax}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
            <p className="text-[10px] text-slate-400">{tcs.why_it_matters}</p>
            <p className="text-[10px] text-slate-400 mt-1">{tcs.how_to_get}</p>
            <p className="text-[9px] text-slate-600 mt-2">{tcs.note}</p>
          </div>
        )
      })()}

      {/* BBBEE card + finding columns */}
      <div className="grid grid-cols-3 gap-4">
        <BBBEECard bbbeeAnalysis={bbbeeAnalysis} bbbeeLevel={bbbeeLevel} />

        {/* Tax findings */}
        <div className="col-span-1 bg-[#0f1117] border border-white/8 rounded-xl p-4">
          <div className="text-[11px] font-bold text-slate-300 mb-3">🧾 Top Tax Findings</div>
          {taxFindings.length === 0 ? (
            <p className="text-[11px] text-slate-500">No tax findings recorded.</p>
          ) : (
            <ul className="space-y-2">
              {taxFindings.slice(0, 4).map((f, i) => (
                <li key={i} className="text-[10px]">
                  <span className={`font-bold ${sevColor[f.severity] || 'text-slate-400'}`}>[{f.severity?.toUpperCase()}]</span>
                  <span className="text-slate-300 ml-1">{f.title}</span>
                  {f.financial_impact && (
                    <div className="text-slate-500 mt-0.5">{f.financial_impact}</div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Legal findings */}
        <div className="col-span-1 bg-[#0f1117] border border-white/8 rounded-xl p-4">
          <div className="text-[11px] font-bold text-slate-300 mb-3">⚖️ Top Legal Findings</div>
          {legalFindings.length === 0 ? (
            <p className="text-[11px] text-slate-500">No legal findings recorded.</p>
          ) : (
            <ul className="space-y-2">
              {legalFindings.slice(0, 4).map((f, i) => (
                <li key={i} className="text-[10px]">
                  <span className={`font-bold ${sevColor[f.severity] || 'text-slate-400'}`}>[{f.severity?.toUpperCase()}]</span>
                  <span className="text-slate-300 ml-1">{f.title}</span>
                  {f.financial_impact && (
                    <div className="text-slate-500 mt-0.5">{f.financial_impact}</div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
