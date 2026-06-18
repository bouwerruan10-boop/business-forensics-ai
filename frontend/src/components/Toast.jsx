export default function Toast({ toast }) {
  if (!toast) return null
  const isError = toast.type === 'error'
  return (
    <div className={`
      fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-2xl text-sm font-medium fade-in
      border flex items-center gap-2
      ${isError
        ? 'bg-red-900/80 border-red-500/40 text-red-200'
        : 'bg-navy-card border-gold/30 text-white'
      }
    `}>
      <span>{isError ? '✕' : '✓'}</span>
      {toast.message}
    </div>
  )
}
