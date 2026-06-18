import { CheckCircle, Loader, Circle } from 'lucide-react'

const AGENTS = [
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

export default function AgentActivity({ status }) {
  const progress = status?.progress || []
  const completedAgents = new Set(progress.map(p => p.agent))
  const currentAgent = status?.current_agent || ''

  return (
    <div style={{
      background: 'rgba(255,255,255,0.03)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: 14, padding: 20,
    }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: '#C9A84C', marginBottom: 16, letterSpacing: 1 }}>
        AGENT ACTIVITY
      </div>

      {AGENTS.map(agent => {
        const done = completedAgents.has(agent)
        const active = currentAgent === agent || currentAgent.startsWith(agent)

        return (
          <div key={agent} style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '7px 0',
            borderBottom: '1px solid rgba(255,255,255,0.04)',
            opacity: done || active ? 1 : 0.4,
          }}>
            {done ? (
              <CheckCircle size={16} color="#27AE60" />
            ) : active ? (
              <Loader size={16} color="#C9A84C" style={{ animation: 'spin 1s linear infinite' }} />
            ) : (
              <Circle size={16} color="#475569" />
            )}
            <span style={{
              fontSize: 13,
              color: done ? '#27AE60' : active ? '#C9A84C' : '#94a3b8',
              fontWeight: active || done ? 600 : 400,
            }}>
              {agent}
            </span>
            {active && (
              <span style={{ fontSize: 11, color: '#64748b', marginLeft: 'auto' }}>
                analyzing...
              </span>
            )}
            {done && (
              <span style={{ fontSize: 11, color: '#27AE60', marginLeft: 'auto' }}>
                complete
              </span>
            )}
          </div>
        )
      })}

      <style>{`@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}
