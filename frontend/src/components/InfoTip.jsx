import { Info } from 'lucide-react'

// Accessible "explain this" affordance: a real button with an aria-label (read by
// screen readers) and a native title (hover tooltip for sighted/mouse users).
export default function InfoTip({ label, text, className = '' }) {
  return (
    <button
      type="button"
      aria-label={`${label}: ${text}`}
      title={text}
      className={`inline-flex items-center justify-center w-4 h-4 rounded-full text-slate-500 hover:text-gold focus-visible:text-gold align-middle ${className}`}
    >
      <Info size={13} aria-hidden="true" />
    </button>
  )
}
