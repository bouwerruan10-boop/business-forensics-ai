import { useState, useEffect, useRef } from 'react'
import Navbar from './components/Navbar'
import SmartIntake from './components/SmartIntake'
import AnalysisProgress from './components/AnalysisProgress'
import Dashboard from './components/Dashboard'
import AdminDashboard from './components/AdminDashboard'
import SharedReport from './components/SharedReport'
import Toast from './components/Toast'
import { uploadFiles, pollStatus, getReport } from './api/client'

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
  const pollRef = useRef(null)

  // Hash routing — handle /report/:id URLs
  useEffect(() => {
    const checkHash = () => {
      const hash = window.location.hash
      const match = hash.match(/^#\/report\/([a-f0-9-]{36})$/)
      if (match) {
        setSharedId(match[1])
      } else {
        setSharedId(null)
      }
    }
    checkHash()
    window.addEventListener('hashchange', checkHash)
    return () => window.removeEventListener('hashchange', checkHash)
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
    pollRef.current = setInterval(async () => {
      try {
        const s = await pollStatus(analysisId)
        setStatus(s)
        if (s.status === 'complete') {
          clearInterval(pollRef.current)
          const r = await getReport(analysisId)
          setReport(r)
          setPhase('done')
        } else if (s.status === 'error') {
          clearInterval(pollRef.current)
          setError(s.error || 'Analysis failed. Please try again.')
          setPhase('upload')
        }
      } catch (e) { /* network hiccup — keep polling */ }
    }, 2000)
    return () => clearInterval(pollRef.current)
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

  // Shared report view (hash routing)
  if (sharedId) {
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
        <SharedReport analysisId={sharedId} showToast={showToast} />
        <Toast toast={toast} />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-navy font-sans">
      <Navbar
        phase={phase}
        onAdmin={() => setPhase(phase === 'admin' ? 'profile' : 'admin')}
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
      </main>

      <Toast toast={toast} />
    </div>
  )
}
