import { useEffect, useState } from 'react'
import InfoTip from './InfoTip'

export default function ScoreReasons({ analysisId, report }) {
  // Prefer the reasons embedded in the report (self-contained — works on token-shared
  // links that carry no analysis id); fall back to the on-demand endpoint when present.
  const embedded = report && report.reason_codes
  const [data, setData] = useState(embedded || null)
  const [contesting, setContesting] = useState(false)
  const [cFactor, setCFactor] = useState('')
  const [cStatement, setCStatement] = useState('')
  const [cContact, setCContact] = useState('')
  const [cDone, setCDone] = useState(false)
  const [cErr, setCErr] = useState(null)

  useEffect(() => {
    if (embedded || !analysisId) { if (embedded) setData(embedded); return }
    let on = true
    import('../api/client').then(({ getReasons }) => getReasons(analysisId))
      .then(d => { if (on) setData(d) }).catch(() => { if (on) setData(null) })
    return () => { on = false }
  }, [analysisId, embedded])

  const submitContest = async () => {
    setCErr(null)
    try {
      const { contestScore } = await import('../api/client')
      await contestScore(analysisId, { factor: cFactor, statement: cStatement, contact: cContact })
      setCDone(true); setContesting(false); setCStatement(''); setCContact('')
    } catch (e) { setCErr(e.message) }
  }

  if (!data || !data.available || !data.reasons?.length) return null
  const maxImpact = Math.max(...data.reasons.map(r => r.impact), 1)

  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-5 mb-4">
      <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
        Why this score — principal factors
        <InfoTip label="Score drivers" text="The factors holding the Imara Score back, ordered by impact, derived directly from the score's own weighted components and tied to the underlying numbers. Decision-support — not a credit decision or adverse-action notice under the NCA." />
      </div>

      <div className="space-y-2.5">
        {data.reasons.map((r, i) => (
          <div key={i} className="flex items-start gap-3">
            <span className="text-slate-600 text-xs font-bold w-4 mt-0.5">{i + 1}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="text-white text-sm font-medium">{r.factor}</span>
                <span className="text-slate-500 text-xs tabular-nums">{r.score}/100</span>
              </div>
              <div className="text-slate-400 text-xs mt-0.5">{r.detail}</div>
              <div className="mt-1 h-1 rounded-full bg-white/[0.06] overflow-hidden">
                <div className="h-full bg-gold/70 rounded-full" style={{ width: `${Math.round((r.impact / maxImpact) * 100)}%` }} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {data.strengths?.length > 0 && (
        <div className="mt-4">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1.5">Strengths</div>
          <div className="flex flex-wrap gap-1.5">
            {data.strengths.map((s, i) => (
              <span key={i} className="text-[11px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full px-2.5 py-1">
                {s.factor} <span className="text-emerald-300/70">{s.score}</span>
              </span>
            ))}
          </div>
        </div>
      )}
      <p className="text-slate-600 text-[11px] mt-3 leading-relaxed italic">{data.disclaimer}</p>

      {/* POPIA s71(3) — right to make representations against the score (needs an analysis id to lodge) */}
      {analysisId && <div className="mt-3 pt-3 border-t border-white/[0.06]">
        {cDone ? (
          <div className="text-[11px] text-emerald-400">✓ Your representation was lodged and recorded in the tamper-evident audit log. A human will review it.</div>
        ) : !contesting ? (
          <button type="button" onClick={() => { setContesting(true); setCFactor(data.reasons[0]?.factor || '') }}
            className="text-[11px] text-slate-400 hover:text-gold underline underline-offset-2">
            Disagree with this score? Contest a factor →
          </button>
        ) : (
          <div className="space-y-2">
            <div className="text-[11px] text-slate-400">Lodge a representation (POPIA s71(3)). A human reviews it — the score is decision-support, not a credit decision.</div>
            <select value={cFactor} onChange={(e) => setCFactor(e.target.value)}
              className="w-full text-xs rounded-lg bg-navy border border-white/10 px-2.5 py-1.5 text-slate-200 focus:border-gold/40 outline-none">
              {data.reasons.map((r, i) => <option key={i} value={r.factor}>{r.factor}</option>)}
            </select>
            <textarea value={cStatement} onChange={(e) => setCStatement(e.target.value)} rows={3}
              placeholder="Why is this factor wrong or incomplete? (e.g. margins recovered after the statement period)"
              className="w-full text-xs rounded-lg bg-navy border border-white/10 px-2.5 py-1.5 text-white focus:border-gold/40 outline-none" />
            <input value={cContact} onChange={(e) => setCContact(e.target.value)}
              placeholder="Contact (optional)"
              className="w-full text-xs rounded-lg bg-navy border border-white/10 px-2.5 py-1.5 text-white focus:border-gold/40 outline-none" />
            {cErr && <div className="text-[11px] text-red-300">{cErr}</div>}
            <div className="flex gap-2">
              <button type="button" onClick={submitContest} disabled={!cStatement.trim()}
                className="text-[11px] rounded-lg px-3 py-1.5 bg-gold text-navy font-semibold disabled:opacity-50">Lodge representation</button>
              <button type="button" onClick={() => setContesting(false)}
                className="text-[11px] rounded-lg px-3 py-1.5 border border-white/10 text-slate-400">Cancel</button>
            </div>
          </div>
        )}
      </div>}
    </div>
  )
}
