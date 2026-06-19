import { useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const AUDIENCE_OPTIONS = [
  { value: 'owner',    label: 'Owner',    desc: 'Plain-language, action-focused' },
  { value: 'banker',   label: 'Banker',   desc: 'Credit & risk focus' },
  { value: 'investor', label: 'Investor', desc: 'Valuation & growth story' },
]

export default function ReportActions({ analysisId, businessName, onNewAnalysis, showToast }) {
  const [pdfLoading, setPdfLoading]     = useState(false)
  const [htmlLoading, setHtmlLoading]   = useState(false)
  const [audience, setAudience]         = useState('owner')
  const [showAudiencePicker, setShowAudiencePicker] = useState(false)
  const [showShare, setShowShare]       = useState(false)
  const [sharing, setSharing]           = useState(false)

  const slug = (businessName || 'report').replace(/\s+/g, '_')

  const downloadPdf = async () => {
    setPdfLoading(true)
    showToast(`Generating ${audience} PDF…`)
    try {
      const res = await fetch(`${API_BASE}/api/report/${analysisId}/pdf?audience=${audience}`)
      if (!res.ok) throw new Error('PDF generation failed')
      const blob = await res.blob()
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `${slug}_${audience}_report.pdf`
      link.click()
      showToast('PDF downloaded!')
    } catch (e) {
      showToast('PDF download failed: ' + e.message, 'error')
    } finally {
      setPdfLoading(false)
    }
  }

  const downloadHtml = async () => {
    setHtmlLoading(true)
    showToast('Generating interactive report…')
    try {
      const res = await fetch(`${API_BASE}/api/report/${analysisId}/html`)
      if (!res.ok) throw new Error('HTML generation failed')
      const blob = await res.blob()
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `${slug}_interactive_report.html`
      link.click()
      showToast('Interactive report downloaded!')
    } catch (e) {
      showToast('Download failed: ' + e.message, 'error')
    } finally {
      setHtmlLoading(false)
    }
  }

  const copyPermanentLink = () => {
    const url = `${window.location.origin}${window.location.pathname}#/report/${analysisId}`
    navigator.clipboard.writeText(url).then(() => showToast('Permanent link copied!'))
    setShowShare(false)
  }

  const copyExpiringLink = async (days) => {
    setSharing(true)
    try {
      const res = await fetch(`${API_BASE}/api/report/${analysisId}/share?expires_in_days=${days}`, { method: 'POST' })
      if (!res.ok) throw new Error('Could not create link')
      const { token } = await res.json()
      const url = `${window.location.origin}${window.location.pathname}#/shared/${token}`
      await navigator.clipboard.writeText(url)
      showToast(`${days}-day link copied!`)
    } catch (e) {
      showToast('Could not create link: ' + e.message, 'error')
    } finally {
      setSharing(false)
      setShowShare(false)
    }
  }

  const currentAudience = AUDIENCE_OPTIONS.find(o => o.value === audience)

  return (
    <div className="sticky top-14 z-40 bg-navy/95 backdrop-blur-sm border-b border-white/[0.08] px-4 sm:px-6 lg:px-8 py-3 -mx-4 sm:-mx-6 lg:-mx-8 mb-6">
      <div className="max-w-6xl mx-auto flex items-center gap-3 justify-between flex-wrap">
        <div className="text-white font-semibold text-sm hidden sm:block">{businessName}</div>

        <div className="flex items-center gap-2 ml-auto flex-wrap">
          {/* Audience picker */}
          <div className="relative">
            <button type="button" onClick={() => setShowAudiencePicker(v => !v)} aria-expanded={showAudiencePicker}
              className="flex items-center gap-1.5 border border-white/10 text-slate-300 hover:border-gold/40 hover:text-gold text-xs px-3 py-2 rounded-lg transition-colors">
              <span className="text-slate-400">Report for:</span>
              <span className="text-gold font-bold">{currentAudience?.label}</span>
              <span className="text-slate-400" aria-hidden="true">▾</span>
            </button>
            {showAudiencePicker && (
              <div className="absolute top-full mt-1 left-0 w-48 bg-[#0D1B2A] border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50">
                {AUDIENCE_OPTIONS.map(opt => (
                  <button key={opt.value} type="button"
                    onClick={() => { setAudience(opt.value); setShowAudiencePicker(false) }}
                    className={`w-full text-left px-4 py-2.5 text-xs hover:bg-white/5 transition-colors ${audience === opt.value ? 'text-gold' : 'text-slate-300'}`}>
                    <div className="font-bold">{opt.label}</div>
                    <div className="text-slate-400">{opt.desc}</div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <button type="button" onClick={downloadPdf} disabled={pdfLoading}
            className="flex items-center gap-1.5 bg-gold hover:bg-gold-light disabled:opacity-50 text-navy font-bold text-xs px-4 py-2 rounded-lg transition-colors">
            ↓ {pdfLoading ? 'Generating…' : 'PDF'}
          </button>

          <button type="button" onClick={downloadHtml} disabled={htmlLoading}
            className="flex items-center gap-1.5 border border-gold/30 text-gold hover:bg-gold/10 disabled:opacity-50 font-bold text-xs px-4 py-2 rounded-lg transition-colors hidden sm:flex">
            ⬡ {htmlLoading ? 'Building…' : 'Interactive'}
          </button>

          {/* Share dropdown — permanent or expiring links */}
          <div className="relative">
            <button type="button" onClick={() => setShowShare(v => !v)} aria-expanded={showShare} aria-label="Share report"
              className="flex items-center gap-1.5 border border-white/10 text-slate-300 hover:border-gold/40 hover:text-gold text-xs px-3 py-2 rounded-lg transition-colors">
              🔗 <span className="hidden sm:inline">Share</span> <span className="text-slate-400" aria-hidden="true">▾</span>
            </button>
            {showShare && (
              <div className="absolute top-full mt-1 right-0 w-56 bg-[#0D1B2A] border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50">
                <button type="button" onClick={copyPermanentLink} disabled={sharing}
                  className="w-full text-left px-4 py-2.5 text-xs text-slate-300 hover:bg-white/5 transition-colors">
                  <div className="font-bold">Copy link</div>
                  <div className="text-slate-400">Permanent — works until revoked</div>
                </button>
                <button type="button" onClick={() => copyExpiringLink(7)} disabled={sharing}
                  className="w-full text-left px-4 py-2.5 text-xs text-slate-300 hover:bg-white/5 transition-colors border-t border-white/[0.06]">
                  <div className="font-bold">Copy 7-day link</div>
                  <div className="text-slate-400">Expires automatically in a week</div>
                </button>
                <button type="button" onClick={() => copyExpiringLink(30)} disabled={sharing}
                  className="w-full text-left px-4 py-2.5 text-xs text-slate-300 hover:bg-white/5 transition-colors border-t border-white/[0.06]">
                  <div className="font-bold">Copy 30-day link</div>
                  <div className="text-slate-400">Expires automatically in a month</div>
                </button>
              </div>
            )}
          </div>

          <button type="button" onClick={onNewAnalysis}
            className="border border-white/10 text-slate-400 hover:border-white/20 hover:text-white text-xs px-4 py-2 rounded-lg transition-colors hidden sm:block">
            + New
          </button>
        </div>
      </div>
    </div>
  )
}
