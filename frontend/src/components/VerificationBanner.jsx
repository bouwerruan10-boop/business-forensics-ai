import { useState } from 'react'

// "Prove it" banner — surfaces the report-wide claim ledger: how many of the numbers in
// Imara's narratives were verified against the deterministically-computed data, which
// conflict, and which are unverified estimates. Mark-visibly (never hides an unverified claim).
export default function VerificationBanner({ report }) {
  const [open, setOpen] = useState(false)
  const led = report?.claim_ledger
  if (!led?.available) return null

  // Narrative claims + per-finding figure claims (impact / recommendation / ROI / cost),
  // surfaced together so no unverified number is hidden from the reader.
  const claims = led.narrative_claims || []
  const findingClaims = (led.finding_figure_claims || []).map((c) => ({ ...c, section: c.section || 'Finding' }))
  const allClaims = [...claims, ...findingClaims]
  const conflicts = allClaims.filter((c) => c.verification === 'conflict')
  const unverified = allClaims.filter((c) => c.verification === 'unverified')

  const tone = led.overall === 'conflicts_present'
    ? { c: '#ef4444', label: 'NEEDS REVIEW', icon: '⚠' }
    : led.overall === 'unverified_present'
    ? { c: '#f59e0b', label: 'SOME ESTIMATES', icon: '◐' }
    : { c: '#22c55e', label: 'VERIFIED', icon: '✓' }

  const Row = ({ c }) => (
    <div className="flex items-start gap-2 py-1.5 border-b border-white/5 last:border-0">
      <span className="text-[10px] mt-0.5" style={{ color: c.verification === 'conflict' ? '#ef4444' : '#f59e0b' }}>
        {c.verification === 'conflict' ? '✗' : '?'}
      </span>
      <div className="min-w-0">
        <div className="text-[11px] text-slate-300">
          <span className="text-slate-500">{c.section}:</span> “{c.text}”
        </div>
        <div className="text-[11px] text-slate-400">{c.explanation}</div>
      </div>
    </div>
  )

  return (
    <div className="mb-6 rounded-2xl border bg-white/[0.02] p-4" style={{ borderColor: tone.c + '40' }}>
      <button type="button" onClick={() => setOpen(!open)} className="w-full flex items-center justify-between gap-3 text-left">
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-lg" style={{ color: tone.c }}>{tone.icon}</span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded border"
                style={{ color: tone.c, borderColor: tone.c + '55', background: tone.c + '15' }}>{tone.label}</span>
              <span className="text-sm text-white font-medium">Every number, checked against your data</span>
            </div>
            <div className="text-xs text-slate-400 mt-0.5">{led.headline}</div>
          </div>
        </div>
        <span className="text-xs text-slate-500 shrink-0">{open ? 'Hide' : 'Details'}</span>
      </button>

      {open && (
        <div className="mt-3 pt-3 border-t border-white/5 space-y-3">
          {conflicts.length > 0 && (
            <div>
              <div className="text-[11px] uppercase tracking-wider text-red-400 mb-1">Conflicts — the narrative disagrees with the computed figure</div>
              {conflicts.map((c, i) => <Row key={i} c={c} />)}
            </div>
          )}
          {unverified.length > 0 && (
            <div>
              <div className="text-[11px] uppercase tracking-wider text-amber-400 mb-1">Unverified estimates — not traceable to a computed figure</div>
              {unverified.map((c, i) => <Row key={i} c={c} />)}
            </div>
          )}
          {conflicts.length === 0 && unverified.length === 0 && (
            <div className="text-[11px] text-emerald-400">All numbers in the narrative match Imara’s computed values.</div>
          )}
          <p className="text-[10px] text-slate-600">{led.note}</p>
        </div>
      )}
    </div>
  )
}
