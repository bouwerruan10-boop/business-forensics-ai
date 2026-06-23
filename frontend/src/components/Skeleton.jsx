// Lightweight skeleton/shimmer for loading states (replaces frozen-looking text).
export default function Skeleton({ lines = 3, className = '' }) {
  return (
    <div className={`animate-pulse space-y-2.5 ${className}`} aria-busy="true" aria-live="polite">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-3 rounded bg-white/10" style={{ width: `${92 - i * 14}%` }} />
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  )
}
