import { useEffect, useState } from 'react'

const AGENT_ORDER = [
  'CEO Agent',
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
]

const AGENT_ICONS = {
  'CEO Agent': '💼',
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
}

export default function AnalysisProgress({ status, profile }) {
  const [completedAgents, setCompletedAgents] = useState([])
  const currentAgent = status?.current_agent || 'Initialising...'
  const progress = status?.progress || []

  // Build completed agent list from progress log
  useEffect(() => {
    const names = [...new Set(progress.map(p => p.agent).filter(a => a !== currentAgent))]
    setCompletedAgents(names)
  }, [progress, currentAgent])

  const totalAgents = 12
  const completedCount = completedAgents.length
  const pct = Math.min(95, Math.round((completedCount / totalAgents) * 100))

  return (
    <div className="max-w-2xl mx-auto">
      {/* Status header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 mb-4">
          <span className="pulse-dot w-2 h-2 rounded-full bg-gold inline-block" />
          <span className="pulse-dot pulse-dot-2 w-2 h-2 rounded-full bg-gold inline-block" />
          <span className="pulse-dot pulse-dot-3 w-2 h-2 rounded-full bg-gold inline-block" />
        </div>
        <h2 className="text-xl font-bold text-white mb-1">
          {currentAgent.replace(' is conducting investigation...', '')}
        </h2>
        <p className="text-slate-500 text-sm">
          {profile?.company_name} · {profile?.currency} · Analysis in progress
        </p>
        <p className="text-slate-600 text-xs mt-1">Estimated time: 3–8 minutes</p>
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
        <div className="divide-y divide-white/[0.04] max-h-80 overflow-y-auto">
          {AGENT_ORDER.map(agent => {
            const isDone = completedAgents.includes(agent)
            const isRunning = currentAgent.includes(agent.replace(' Agent', ''))
              || currentAgent === agent
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
                  isDone ? 'text-slate-400'
                  : isRunning ? 'text-white font-medium'
                  : 'text-slate-600'
                }`}>
                  {agent}
                </span>
                <span className="flex-shrink-0">
                  {isDone && (
                    <span className="text-emerald-400 text-sm">✓</span>
                  )}
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
