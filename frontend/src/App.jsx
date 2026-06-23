import { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import SmartIntake from './components/SmartIntake'
import AnalysisProgress from './components/AnalysisProgress'
import Dashboard from './components/Dashboard'
import AdminDashboard from './components/AdminDashboard'
import SharedReport from './components/SharedReport'
import TaxPlanner from './components/TaxPlanner'
import Login from './components/Login'
import Toast from './components/Toast'
import { uploadFiles, pollStatus, getReport, getHealth, getToken } from './api/client'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function App() {
  const [phase, setPhase] = useState('intake') // intake | analyzing | done | admin
  const [profile, setProfile] = useState(null)
  const [analysisId, setAnalysisId] = useState(null)
  const [status, setStatus] = useState(null)
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)
  const [sharedId, setSharedId] = useState(null)
  const [sharedToken, setSharedToken] = useState(null)
  const [authRequired, setAuthRequired] = useState(false)
  const [authed, setAuthed] = useState(() => !!getToken())
  const [authChecked, setAuthChecked] = useState(false)

  // Hash routing — handle /report/:id URLs
  useEffect(() => {
    const checkHash = () => {
      const hash = window.location.hash
      const match = hash.match(/^#\/report\/([a-f0-9-]{36})$/)
      const tokenMatch = hash.match(/^#\/shared\/([A-Za-z0-9_-]+)$/)
      if (match) {
        setSharedId(match[1]); setSharedToken(null)
      } else if (tokenMatch) {
        setSharedToken(tokenMatch[1]); setSharedId(null)
      } else if (hash === '#/tax') {
        setSharedId(null); setSharedToken(null); setPhase('tax')
      } else {
        setSharedId(null); setSharedToken(null)
      }
    }
    checkHash()
    window.addEventListener('hashchange', checkHash)
    return () => window.removeEventListener('hashchange', checkHash)
  }, [])

  // Operator-auth status (whether a login is required for this deployment)
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      // Retry the health check; its answer decides whether the operator login gate shows.
      for (let attempt = 0; attempt < 3 && !cancelled; attempt++) {
        try {
          const h = await getHealth()
          if (!cancelled) { setAuthRequired(!!h.auth_required); setAuthChecked(true) }
          return
        } catch {
          await new Promise(r => setTimeout(r, 700 * (attempt + 1)))
        }
      }
      // All attempts failed -> fail CLOSED. Never silently expose the intake form to an
      // unauthenticated user; assume a login is required so the gate still appears.
      if (!cancelled) { setAuthRequired(true); setAuthChecked(true) }
    })()
    return () => { cancelled = true }
  }, [])

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  const startAnalysis = async (files, profileData) => {
    setError(null)
    setProfile(profileData)
    setPhase('analyzing')
    try {
      const { analysis_id } = await uploadFiles(files, profileData)
      setAnalysisId(analysis_id)
    } catch (e) {
      setError(e.message)
      setPhase('intake')
    }
  }

  useEffect(() => {
    if (!analysisId || phase !== 'analyzing') return
    let cancelled = false
    let timer = null
    const startedAt = Date.now()
    const MAX_POLL_MS = 40 * 60 * 1000      // hard stop: surface an error instead of polling forever
    const BASE_MS = 2000
    const MAX_INTERVAL_MS = 30000
    let interval = BASE_MS

    const tick = async () => {
      if (cancelled) return
      if (Date.now() - startedAt > MAX_POLL_MS) {
        setError('Analysis is taking longer than expected. Please try again or contact support.')
        setPhase('intake')
        return
      }
      try {
        const s = await pollStatus(analysisId)
        if (cancelled) return
        setStatus(s)
        if (s.status === 'complete') {
          const r = await getReport(analysisId)
          if (cancelled) return
          setReport(r)
          setPhase('done')
          return
        }
        if (s.status === 'error') {
          setError(s.error || 'Analysis failed. Please try again.')
          setPhase('intake')
          return
        }
        interval = BASE_MS                  // healthy response -> reset backoff
      } catch (e) {
        interval = Math.min(MAX_INTERVAL_MS, Math.round(interval * 1.6))  // back off on transient errors
      }
      timer = setTimeout(tick, interval)
    }
    timer = setTimeout(tick, interval)
    return () => { cancelled = true; if (timer) clearTimeout(timer) }
  }, [analysisId, phase])

  const loadDemo = async () => {
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/demo`)
      if (!res.ok) throw new Error('Demo endpoint not available — is the backend running?')
      const r = await res.json()
      setReport(r)
      setAnalysisId('demo-001')
      setPhase('done')
      showToast('Demo report loaded — no API credits used!')
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  const resetAll = () => {
    setPhase('intake')
    setProfile(null)
    setReport(null)
    setAnalysisId(null)
    setStatus(null)
    setError(null)
  }

  const viewReportFromAdmin = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/report/${id}`)
      if (!res.ok) throw new Error('Report not found')
      const r = await res.json()
      setReport(r)
      setAnalysisId(id)
      setPhase('done')
    } catch (e) {
      showToast('Could not load report: ' + e.message, 'error')
    }
  }

  // Operator login gate. Public #/shared/{token} links are exempt (clients never sign in).
  if (!sharedToken) {
    if (!authChecked) return <div className="min-h-screen bg-navy" aria-busy="true" />
    if (authRequired && !authed) return <Login onAuthed={() => setAuthed(true)} />
  }

  // Shared report view (hash routing) — by analysis id or by share token
  if (sharedId || sharedToken) {
    return (
      <div className="min-h-screen bg-navy font-sans">
        <Navbar
          phase="shared"
          onAdmin={() => {}}
          onNewAnalysis={() => {
            window.location.hash = ''
            resetAll()
          }}
          showToast={showToast}
        />
        <SharedReport analysisId={sharedId} token={sharedToken} showToast={showToast} />
        <Toast toast={toast} />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-navy font-sans">
      <Navbar
        phase={phase}
        onAdmin={() => setPhase(phase === 'admin' ? 'profile' : 'admin')}
        onTax={() => { window.location.hash = '#/tax'; setPhase('tax') }}
        onNewAnalysis={resetAll}
        analysisId={analysisId}
        showToast={showToast}
      />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {phase === 'intake' && (
          <div className="fade-in">
            <SmartIntake onAnalyze={startAnalysis} onDemo={loadDemo} error={error} />
          </div>
        )}

        {phase === 'analyzing' && (
          <div className="fade-in">
            <AnalysisProgress status={status} profile={profile} />
          </div>
        )}

        {phase === 'done' && report && (
          <div className="fade-in">
            <Dashboard
              report={report}
              analysisId={analysisId}
              onNewAnalysis={resetAll}
              showToast={showToast}
            />
          </div>
        )}

        {phase === 'admin' && (
          <div className="fade-in">
            <AdminDashboard onViewReport={viewReportFromAdmin} />
          </div>
        )}

        {phase === 'tax' && (
          <div className="fade-in">
            <TaxPlanner />
          </div>
        )}
      </main>

      <Toast toast={toast} />
    </div>
  )
}
