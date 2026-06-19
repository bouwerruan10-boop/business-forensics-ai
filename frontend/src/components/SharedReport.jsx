import { useEffect, useState } from 'react'
import Dashboard from './Dashboard'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function SharedReport({ analysisId, token, showToast }) {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const endpoint = token ? `${API_BASE}/api/shared/${token}` : `${API_BASE}/api/report/${analysisId}`
        const res = await fetch(endpoint)
        if (!res.ok) {
          if (res.status === 410) throw new Error('This shared link has expired or been revoked.')
          throw new Error(res.status === 404 ? 'Report not found' : 'Failed to load report')
        }
        const r = await res.json()
        setReport(r)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    if (analysisId || token) load()
  }, [analysisId, token])

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <div className="flex gap-1.5 mb-4">
        <span className="pulse-dot w-2.5 h-2.5 rounded-full bg-gold inline-block" />
        <span className="pulse-dot pulse-dot-2 w-2.5 h-2.5 rounded-full bg-gold inline-block" />
        <span className="pulse-dot pulse-dot-3 w-2.5 h-2.5 rounded-full bg-gold inline-block" />
      </div>
      <p className="text-slate-500 text-sm">Loading report...</p>
    </div>
  )

  if (error) return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <div className="text-4xl mb-4">🔍</div>
      <h2 className="text-white font-semibold mb-2">{error && error.includes('expired') ? 'Link Expired' : 'Report Not Found'}</h2>
      <p className="text-slate-500 text-sm mb-6">{error}</p>
      <a
        href={window.location.pathname}
        className="bg-gold text-navy font-bold text-sm px-6 py-2.5 rounded-xl hover:bg-gold-light transition-colors"
      >
        Start New Analysis
      </a>
    </div>
  )

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6 flex items-center gap-2">
        <span className="text-xs text-slate-500 bg-white/5 border border-white/10 rounded-full px-3 py-1">
          Shared Report
        </span>
        <a
          href={window.location.pathname}
          className="text-xs text-gold hover:underline ml-auto"
        >
          Run your own analysis →
        </a>
      </div>
      <Dashboard
        report={report}
        analysisId={analysisId}
        onNewAnalysis={() => { window.location.hash = '' }}
        showToast={showToast}
      />
    </div>
  )
}
