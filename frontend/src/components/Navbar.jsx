export default function Navbar({ phase, onAdmin, onNewAnalysis, analysisId, showToast }) {
  const copyShareLink = () => {
    if (!analysisId) return
    const url = `${window.location.origin}${window.location.pathname}#/report/${analysisId}`
    navigator.clipboard.writeText(url).then(() => showToast('Share link copied!'))
  }

  return (
    <nav className="sticky top-0 z-50 h-14 flex items-center px-4 sm:px-6 lg:px-8 border-b border-white/[0.08] bg-navy/95 backdrop-blur-sm">
      {/* Logo */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-2 h-2 rounded-full bg-gold flex-shrink-0" />
        <div className="flex items-baseline gap-2 min-w-0">
          <span className="font-bold text-sm tracking-wider text-white hidden sm:block">
            BUSINESS FORENSICS AI
          </span>
          <span className="font-bold text-sm tracking-wider text-white sm:hidden">
            BF AI
          </span>
          <span className="text-xs text-slate-500 hidden md:block">
            Virtual Consulting Firm
          </span>
        </div>
      </div>

      {/* Right actions */}
      <div className="ml-auto flex items-center gap-2">
        {phase === 'done' && analysisId && (
          <button
            onClick={copyShareLink}
            className="text-xs text-slate-400 border border-white/10 rounded-lg px-3 py-1.5 hover:border-gold/40 hover:text-gold transition-colors"
          >
            Share
          </button>
        )}
        {(phase === 'done' || phase === 'upload' || phase === 'analyzing') && (
          <button
            onClick={onNewAnalysis}
            className="text-xs text-slate-400 border border-white/10 rounded-lg px-3 py-1.5 hover:border-white/20 hover:text-white transition-colors"
          >
            New Analysis
          </button>
        )}
        <button
          onClick={onAdmin}
          className={`text-xs rounded-lg px-3 py-1.5 border transition-colors ${
            phase === 'admin'
              ? 'border-gold/50 text-gold bg-gold/10'
              : 'border-white/10 text-slate-400 hover:border-white/20 hover:text-white'
          }`}
        >
          {phase === 'admin' ? '← Back' : 'History'}
        </button>
      </div>
    </nav>
  )
}
