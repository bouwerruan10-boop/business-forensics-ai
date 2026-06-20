import { useEffect, useRef, useState } from 'react'

// Full pipeline, in execution order — must match the agents the backend actually
// runs (CEO + market scan + 15 specialists + market deep-dive + 2 SA compliance).
// Derived from the real progress feed; no hard-coded total/ETA.
const AGENT_ORDER = [
  'CEO Agent',
  'Market Research Agent',
  'Financial Forensics Agent',
  'Accounting Agent',
  'Auditor Agent',
  'Operations Agent',
  'Logistics Agent',
  'Sales Agent',
  'Marketing Agent',
  'Human Resources Agent',
  'Procurement Agent',
  'Strategy Agent',
  'Legal Risk Agent',
  'Fraud & Anomaly Detection Agent',
  'Credit Readiness Agent',
  'Valuation Agent',
  'Forecast Agent',
  'Market Intelligence Agent',
  'Economic Environment Agent',
  'SA Tax Compliance Agent',
  'SA Corporate Law & BBBEE Agent',
]

const AGENT_ICONS = {
  'CEO Agent': '💼',
  'Market Research Agent': '🔭',
  'Financial Forensics Agent': '💰',
  'Accounting Agent': '📊',
  'Auditor Agent': '🔍',
  'Operations Agent': '⚙️',
  'Logistics Agent': '🚚',
  'Sales Agent': '📈',
  'Marketing Agent': '📣',
  'Human Resources Agent': '👥',
  'Procurement Agent': '🛒',
  'Strategy Agent': '♟️',
  'Legal Risk Agent': '⚖️',
  'Fraud & Anomaly Detection Agent': '🚨',
  'Credit Readiness Agent': '🏦',
  'Valuation Agent': '💎',
  'Forecast Agent': '🔮',
  'Market Intelligence Agent': '🌐',
  'SA Tax Compliance Agent': '🧾',
  'SA Corporate Law & BBBEE Agent': '⚖️',
}

function fmtDuration(sec) {
  sec = Math.max(0, Math.round(sec))
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

export default function AnalysisProgress({ status, profile }) {
  const currentAgent = status?.current_agent || 'Initialising...'
  const progress = status?.progress || []

  // Live elapsed timer (resets when this screen mounts, i.e. when the run starts)
  const startRef = useRef(Date.now())
  const targetRef = useRef(null)  // monotonic finish-time estimate (ms)
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setElapsed((Date.now() - startRef.current) / 1000), 1000)
    return () => clearInterval(t)
  }, [])

  // Completed = unique agent names seen in the feed, excluding the one running now
  const seen = [...new Set(progress.map(p => p.agent).filter(Boolean))]
  const completedAgents = seen.filter(a => a !== currentAgent)

  const totalAgents = AGENT_ORDER.length
  const completedCount = completedAgents.length
  const pct = Math.min(98, Math.round((completedCount / totalAgents) * 100))

  // Honest, dynamic ETA derived from the observed pace — no fabricated "3–8 min".
  let etaLabel = `A full analysis runs ${totalAgents} AI specialists — this can take several minutes.`
  if (completedCount >= 2) {
    // Monotonic ETA: the estimate may only pull the finish line EARLIER, never later,
    // so the displayed countdown never increases. Agents finish in parallel bursts, which
    // would otherwise make a naive elapsed/completed estimate jump up between waves.
    const perAgent = elapsed / completedCount
    const candidate = Date.now() + perAgent * (totalAgents - completedCount) * 1000
    targetRef.current = targetRef.current == null ? candidate : Math.min(targetRef.current, candidate)
    const remaining = Math.max(0, (targetRef.current - Date.now()) / 1000)
    // "finishing up" must reflect real progress, not an exhausted estimate: only show it
    // when genuinely near done. If the (optimistic) estimate runs out earlier while the
    // slow tail is still running, say "still working" instead of a misleading "finishing up".
    const nearDone = completedCount >= totalAgents - 2
    if (nearDone) {
      etaLabel = `Elapsed ${fmtDuration(elapsed)} \u00b7 finishing up\u2026`
    } else if (remaining > 3) {
      etaLabel = `Elapsed ${fmtDuration(elapsed)} \u00b7 about ${fmtDuration(remaining)} remaining`
    } else {
      etaLabel = `Elapsed ${fmtDuration(elapsed)} \u00b7 still working\u2026`
    }
  } else if (elapsed > 4) {
    etaLabel = `Elapsed ${fmtDuration(elapsed)} \u00b7 estimating remaining time\u2026`
  }

  const headerLabel = currentAgent
    .replace(' is conducting investigation...', '')
    .replace(' conducting investigation...', '')

  return (
    <div className="max-w-2xl mx-auto">
      {/* Status header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 mb-4">
          <span className="pulse-dot w-2 h-2 rounded-full bg-gold inline-block" />
          <span className="pulse-dot pulse-dot-2 w-2 h-2 rounded-full bg-gold inline-block" />
          <span className="pulse-dot pulse-dot-3 w-2 h-2 rounded-full bg-gold inline-block" />
        </div>
        <h2 className="text-xl font-bold text-white mb-1">{headerLabel}</h2>
        <p className="text-slate-500 text-sm">
          {profile?.company_name} · {profile?.currency} · Analysis in progress
        </p>
        <p className="text-slate-600 text-xs mt-1">{etaLabel}</p>
      </div>

      {/* Progress bar */}
      <div className="mb-2">
        <div className="flex justify-between text-xs text-slate-500 mb-1.5">
          <span>{completedCount} of {totalAgents} agents complete</span>
          <span>{pct}%</span>
        </div>
        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
          <div
            className="h-full progress-shimmer rounded-full transition-all duration-700"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Agent feed */}
      <div className="mt-6 bg-navy-card border border-white/[0.08] rounded-2xl overflow-hidden">
        <div className="px-4 py-3 border-b border-white/[0.06]">
          <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">Agent Activity</span>
        </div>
        <div className="divide-y divide-white/[0.04] max-h-96 overflow-y-auto">
          {AGENT_ORDER.map(agent => {
            const isRunning = currentAgent === agent
            const isDone = !isRunning && completedAgents.includes(agent)
            const isPending = !isDone && !isRunning

            return (
              <div
                key={agent}
                className={`flex items-center gap-3 px-4 py-3 transition-colors ${
                  isRunning ? 'bg-gold/5' : ''
                }`}
              >
                <span className="text-lg w-7 text-center flex-shrink-0">
                  {AGENT_ICONS[agent] || '🤖'}
                </span>
                <span className={`text-sm flex-1 ${
                  isRunning ? 'text-white font-medium'
                  : isDone ? 'text-slate-400'
                  : 'text-slate-600'
                }`}>
                  {agent}
                </span>
                <span className="flex-shrink-0">
                  {isDone && <span className="text-emerald-400 text-sm">✓</span>}
                  {isRunning && (
                    <span className="flex gap-0.5">
                      <span className="pulse-dot w-1.5 h-1.5 rounded-full bg-gold inline-block" />
                      <span className="pulse-dot pulse-dot-2 w-1.5 h-1.5 rounded-full bg-gold inline-block" />
                      <span className="pulse-dot pulse-dot-3 w-1.5 h-1.5 rounded-full bg-gold inline-block" />
                    </span>
                  )}
                  {isPending && (
                    <span className="w-4 h-4 rounded-full border border-white/10 inline-block" />
                  )}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
