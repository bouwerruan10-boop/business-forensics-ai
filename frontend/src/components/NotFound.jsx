// Custom in-SPA 404 for unrecognised hash routes (instead of silently showing the home form).
export default function NotFound({ onHome }) {
  return (
    <div className="min-h-screen bg-navy flex items-center justify-center px-6 font-sans">
      <div className="max-w-md w-full rounded-2xl border border-white/10 bg-white/[0.03] p-8 text-center">
        <div className="text-gold text-3xl mb-3 font-bold">404</div>
        <h1 className="text-white text-lg font-bold mb-2">Page not found</h1>
        <p className="text-slate-400 text-sm mb-6">That link doesn’t exist or has expired.</p>
        <button
          type="button"
          onClick={onHome}
          className="rounded-lg px-4 py-2 text-sm font-semibold bg-gold text-navy hover:bg-gold/90 transition-colors"
        >
          Go to Imara
        </button>
      </div>
    </div>
  )
}
