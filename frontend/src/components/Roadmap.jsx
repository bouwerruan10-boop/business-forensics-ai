const PHASE_COLORS = {
  0: { border: 'border-red-500/40', bg: 'bg-red-500/5', dot: 'bg-red-400', badge: 'text-red-400 bg-red-500/10 border-red-500/20' },
  1: { border: 'border-amber-500/40', bg: 'bg-amber-500/5', dot: 'bg-amber-400', badge: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
  2: { border: 'border-emerald-500/40', bg: 'bg-emerald-500/5', dot: 'bg-emerald-400', badge: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' },
}

export default function Roadmap({ roadmap = [] }) {
  if (!roadmap.length) return (
    <div className="text-slate-600 text-sm text-center py-8">Roadmap not available</div>
  )

  return (
    <div className="space-y-4">
      {roadmap.map((phase, i) => {
        const c = PHASE_COLORS[i] || PHASE_COLORS[2]
        return (
          <div
            key={i}
            className={`bg-navy-card border ${c.border} ${c.bg} rounded-2xl p-5`}
          >
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <span className={`text-xs font-bold border rounded-full px-3 py-0.5 ${c.badge}`}>
                {phase.priority_level?.toUpperCase() || 'PRIORITY'}
              </span>
              <h3 className="text-white font-semibold text-sm">{phase.phase}</h3>
            </div>
            <p className="text-slate-400 text-xs mb-4">{phase.focus}</p>
            <div className="space-y-2 mb-4">
              {(phase.actions || []).map((action, j) => (
                <div key={j} className="flex gap-3 text-sm">
                  <div className={`w-1.5 h-1.5 rounded-full ${c.dot} flex-shrink-0 mt-1.5`} />
                  <div className="flex-1">
                    <span className="text-slate-300">{action.action}</span>
                    {action.owner && (
                      <span className="text-slate-600 text-xs ml-2">— {action.owner}</span>
                    )}
                    {action.impact && (
                      <span className="text-emerald-400 text-xs ml-2">{action.impact}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
            {phase.expected_impact && (
              <div className="border-t border-white/[0.06] pt-3">
                <span className="text-xs text-slate-500">Expected impact: </span>
                <span className="text-emerald-400 text-xs font-medium">{phase.expected_impact}</span>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
