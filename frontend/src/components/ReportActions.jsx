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

  const slug = (businessName || 'report').replace(/\s+/g, '_')

  const downloadPdf = async () => {
    setPdfLoading(true)
    showToast(`Generating ${audience} PDF…`)
    try {
      const url = `${API_BASE}/api/report/${analysisId}/pdf?audience=${audience}`
      const res = await fetch(url)
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
      const url = `${API_BASE}/api/report/${analysisId}/html`
      const res = await fetch(url)
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

  const copyShareLink = () => {
    const url = `${window.location.origin}${window.location.pathname}#/report/${analysisId}`
    navigator.clipboard.writeText(url).then(() => showToast('Share link copied!'))
  }

  const currentAudience = AUDIENCE_OPTIONS.find(o => o.value === audience)

  return (
    <div className="sticky top-14 z-40 bg-navy/95 backdrop-blur-sm border-b border-white/[0.08] px-4 sm:px-6 lg:px-8 py-3 -mx-4 sm:-mx-6 lg:-mx-8 mb-6">
      <div className="max-w-6xl mx-auto flex items-center gap-3 justify-between flex-wrap">
        <div className="text-white font-semibold text-sm hidden sm:block">{businessName}</div>

        <div className="flex items-center gap-2 ml-auto flex-wrap">
          {/* Audience picker */}
          <div className="relative">
            <button
              onClick={() => setShowAudiencePicker(v => !v)}
              className="flex items-center gap-1.5 border border-white/10 text-slate-300 hover:border-gold/40 hover:text-gold text-xs px-3 py-2 rounded-lg transition-colors"
            >
              <span className="text-slate-500">Report for:</span>
              <span className="text-gold font-bold">{currentAudience?.label}</span>
              <span className="text-slate-500">▾</span>
            </button>
            {showAudiencePicker && (
              <div className="absolute top-full mt-1 left-0 w-48 bg-[#0D1B2A] border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50">
                {AUDIENCE_OPTIONS.map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => { setAudience(opt.value); setShowAudiencePicker(false) }}
                    className={`w-full text-left px-4 py-2.5 text-xs hover:bg-white/5 transition-colors ${audience === opt.value ? 'text-gold' : 'text-slate-300'}`}
                  >
                    <div className="font-bold">{opt.label}</div>
                    <div className="text-slate-500">{opt.desc}</div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* PDF download */}
          <button
            onClick={downloadPdf}
            disabled={pdfLoading}
            className="flex items-center gap-1.5 bg-gold hover:bg-gold-light disabled:opacity-50 text-navy font-bold text-xs px-4 py-2 rounded-lg transition-colors"
          >
            ↓ {pdfLoading ? 'Generating…' : 'PDF'}
          </button>

          {/* Interactive HTML download */}
          <button
            onClick={downloadHtml}
            disabled={htmlLoading}
            className="flex items-center gap-1.5 border border-gold/30 text-gold hover:bg-gold/10 disabled:opacity-50 font-bold text-xs px-4 py-2 rounded-lg transition-colors hidden sm:flex"
          >
            ⬡ {htmlLoading ? 'Building…' : 'Interactive'}
          </button>

          <button
            onClick={copyShareLink}
            className="flex items-center gap-1.5 border border-white/10 text-slate-400 hover:border-gold/40 hover:text-gold text-xs px-4 py-2 rounded-lg transition-colors"
          >
            🔗
          </button>

          <button
            onClick={onNewAnalysis}
            className="border border-white/10 text-slate-400 hover:border-white/20 hover:text-white text-xs px-4 py-2 rounded-lg transition-colors hidden sm:block"
          >
            + New
          </button>
        </div>
      </div>
    </div>
  )
}
