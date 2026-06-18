import { useState } from 'react'

const SEV = {
  critical: { color: 'bg-red-500', text: 'text-red-400', border: 'border-l-red-500', badge: 'bg-red-500/10 text-red-400 border-red-500/20' },
  high:     { color: 'bg-orange-500', text: 'text-orange-400', border: 'border-l-orange-500', badge: 'bg-orange-500/10 text-orange-400 border-orange-500/20' },
  medium:   { color: 'bg-amber-500', text: 'text-amber-400', border: 'border-l-amber-500', badge: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
  low:      { color: 'bg-blue-500', text: 'text-blue-400', border: 'border-l-blue-500', badge: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
}

function FindingCard({ finding }) {
  const [expanded, setExpanded] = useState(false)
  const s = SEV[finding.severity] || SEV.medium

  return (
    <div className={`bg-navy-card border border-white/[0.08] border-l-4 ${s.border} rounded-xl overflow-hidden card-hover`}>
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full text-left px-5 py-4 flex items-start gap-3"
      >
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className={`text-xs font-bold uppercase tracking-wide border rounded-full px-2 py-0.5 ${s.badge}`}>
              {finding.severity}
            </span>
            {finding.quick_win && (
              <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full px-2 py-0.5 font-medium">
                ⚡ Quick Win
              </span>
            )}
            <span className="text-xs text-slate-600">{finding.agent?.replace(' Agent', '')}</span>
          </div>
          <div className="text-white text-sm font-semibold leading-snug">{finding.title}</div>
          <div className={`text-sm font-medium mt-1 ${s.text}`}>{finding.financial_impact}</div>
        </div>
        <span className="text-slate-600 text-sm flex-shrink-0 mt-0.5">
          {expanded ? '▲' : '▼'}
        </span>
      </button>

      {expanded && (
        <div className="px-5 pb-5 border-t border-white/[0.06] pt-4 space-y-3 text-sm">
          <div>
            <div className="text-xs text-slate-500 font-medium uppercase tracking-wide mb-1">Detail</div>
            <p className="text-slate-300 leading-relaxed">{finding.detail}</p>
          </div>
          <div>
            <div className="text-xs text-slate-500 font-medium uppercase tracking-wide mb-1">Recommendation</div>
            <p className="text-slate-300 leading-relaxed">{finding.recommendation}</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {finding.roi_estimate && (
              <div className="bg-emerald-500/5 border border-emerald-500/15 rounded-lg p-3">
                <div className="text-xs text-emerald-400 font-medium mb-0.5">ROI Estimate</div>
                <div className="text-slate-300 text-xs">{finding.roi_estimate}</div>
              </div>
            )}
            {finding.cost_of_inaction && (
              <div className="bg-red-500/5 border border-red-500/15 rounded-lg p-3">
                <div className="text-xs text-red-400 font-medium mb-0.5">Cost of Inaction</div>
                <div className="text-slate-300 text-xs">{finding.cost_of_inaction}</div>
              </div>
            )}
          </div>
          {finding.benchmark_reference && (
            <div className="bg-white/[0.03] rounded-lg p-3">
              <div className="text-xs text-slate-500 font-medium mb-0.5">Benchmark</div>
              <div className="text-slate-400 text-xs">{finding.benchmark_reference}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function FindingsList({ findings = [] }) {
  const [filter, setFilter] = useState('all')
  const [agentFilter, setAgentFilter] = useState('all')

  const agents = [...new Set(findings.map(f => f.agent).filter(Boolean))]
  const filtered = findings.filter(f => {
    const sevOk = filter === 'all' || f.severity === filter
    const agentOk = agentFilter === 'all' || f.agent === agentFilter
    return sevOk && agentOk
  })

  const counts = { all: findings.length }
  for (const s of ['critical', 'high', 'medium', 'low']) {
    counts[s] = findings.filter(f => f.severity === s).length
  }

  const filterBtn = (val, label) => (
    <button
      key={val}
      onClick={() => setFilter(val)}
      className={`text-xs px-3 py-1.5 rounded-lg border transition-colors font-medium ${
        filter === val
          ? 'bg-gold/15 border-gold/40 text-gold'
          : 'border-white/10 text-slate-400 hover:border-white/20 hover:text-white'
      }`}
    >
      {label} {counts[val] ? <span className="opacity-70">({counts[val]})</span> : null}
    </button>
  )

  return (
    <div>
      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-5">
        {filterBtn('all', 'All')}
        {counts.critical > 0 && filterBtn('critical', 'Critical')}
        {counts.high > 0 && filterBtn('high', 'High')}
        {counts.medium > 0 && filterBtn('medium', 'Medium')}
        {counts.low > 0 && filterBtn('low', 'Low')}
        {agents.length > 1 && (
          <select
            value={agentFilter}
            onChange={e => setAgentFilter(e.target.value)}
            className="text-xs bg-navy-card border border-white/10 text-slate-400 rounded-lg px-3 py-1.5 focus:outline-none focus:border-gold/40 ml-auto"
          >
            <option value="all">All Departments</option>
            {agents.map(a => (
              <option key={a} value={a}>{a.replace(' Agent', '')}</option>
            ))}
          </select>
        )}
      </div>

      {/* Findings */}
      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="text-slate-600 text-sm text-center py-8">No findings match this filter</div>
        ) : (
          filtered.map((f, i) => <FindingCard key={i} finding={f} />)
        )}
      </div>
    </div>
  )
}
