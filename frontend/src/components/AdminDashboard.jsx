import { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function fmt(n, cur = '') {
  if (!n) return '—'
  if (n >= 1_000_000) return `${cur} ${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${cur} ${(n / 1_000).toFixed(0)}K`
  return `${cur} ${n}`
}

function statusBadge(status) {
  const map = {
    complete: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    processing: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    error: 'bg-red-500/10 text-red-400 border-red-500/20',
  }
  return (
    <span className={`text-xs border rounded-full px-2 py-0.5 font-medium ${map[status] || 'bg-white/5 text-slate-400 border-white/10'}`}>
      {status}
    </span>
  )
}

export default function AdminDashboard({ onViewReport }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/admin/analyses?limit=50`)
      if (!res.ok) throw new Error('Could not load analysis history')
      const d = await res.json()
      setData(d)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const totals = data?.totals || {}
  const analyses = data?.analyses || []

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-white font-bold text-lg">Analysis History</h2>
          <p className="text-slate-500 text-sm">All past analyses stored in local database</p>
        </div>
        <button
          onClick={load}
          className="text-xs border border-white/10 text-slate-400 hover:text-white hover:border-white/20 px-3 py-1.5 rounded-lg transition-colors"
        >
          ↻ Refresh
        </button>
      </div>

      {/* Totals */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {[
          { label: 'Total', value: totals.total ?? '—' },
          { label: 'Complete', value: totals.complete ?? '—', color: 'text-emerald-400' },
          { label: 'Processing', value: totals.processing ?? '—', color: 'text-amber-400' },
          { label: 'Errors', value: totals.error ?? '—', color: 'text-red-400' },
        ].map(t => (
          <div key={t.label} className="bg-navy-card border border-white/[0.08] rounded-xl p-4 text-center">
            <div className={`text-2xl font-bold ${t.color || 'text-white'}`}>{t.value}</div>
            <div className="text-slate-500 text-xs mt-0.5">{t.label}</div>
          </div>
        ))}
      </div>

      {loading && (
        <div className="text-center py-12">
          <div className="flex justify-center gap-1 mb-2">
            <span className="pulse-dot w-2 h-2 rounded-full bg-gold inline-block" />
            <span className="pulse-dot pulse-dot-2 w-2 h-2 rounded-full bg-gold inline-block" />
            <span className="pulse-dot pulse-dot-3 w-2 h-2 rounded-full bg-gold inline-block" />
          </div>
          <p className="text-slate-500 text-sm">Loading...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">{error}</div>
      )}

      {!loading && !error && analyses.length === 0 && (
        <div className="text-center py-12 text-slate-600">
          No analyses yet — run your first analysis to see it here.
        </div>
      )}

      {analyses.length > 0 && (
        <div className="bg-navy-card border border-white/[0.08] rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="text-left text-xs text-slate-500 font-medium px-5 py-3">Company</th>
                  <th className="text-left text-xs text-slate-500 font-medium px-5 py-3 hidden sm:table-cell">Industry</th>
                  <th className="text-left text-xs text-slate-500 font-medium px-5 py-3 hidden md:table-cell">Revenue</th>
                  <th className="text-left text-xs text-slate-500 font-medium px-5 py-3">Status</th>
                  <th className="text-left text-xs text-slate-500 font-medium px-5 py-3 hidden lg:table-cell">Date</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {analyses.map(a => (
                  <tr key={a.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-5 py-3">
                      <div className="text-white font-medium">{a.company_name || '—'}</div>
                      <div className="text-slate-600 text-xs">{a.id.slice(0, 8)}...</div>
                    </td>
                    <td className="px-5 py-3 text-slate-400 hidden sm:table-cell">{a.industry_key}</td>
                    <td className="px-5 py-3 text-slate-400 hidden md:table-cell">
                      {fmt(a.annual_revenue, a.currency)}
                    </td>
                    <td className="px-5 py-3">{statusBadge(a.status)}</td>
                    <td className="px-5 py-3 text-slate-600 text-xs hidden lg:table-cell">
                      {new Date(a.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-5 py-3 text-right">
                      {a.status === 'complete' && (
                        <button
                          onClick={() => onViewReport(a.id)}
                          className="text-xs text-gold hover:text-gold-light transition-colors font-medium"
                        >
                          View →
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
