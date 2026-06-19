import { useEffect, useState } from 'react'
import { ArrowUp } from 'lucide-react'

// Sticky scroll-spy report navigation (desktop). Uses IntersectionObserver to
// highlight the section currently in view — shorter/faster than scroll listeners.
export default function SectionNav({ items = [] }) {
  const [active, setActive] = useState(items[0]?.id)

  useEffect(() => {
    if (!items.length) return
    const obs = new IntersectionObserver(
      entries => {
        entries.forEach(e => { if (e.isIntersecting) setActive(e.target.id) })
      },
      { rootMargin: '-20% 0px -70% 0px', threshold: 0 }
    )
    items.forEach(it => {
      const el = document.getElementById(it.id)
      if (el) obs.observe(el)
    })
    return () => obs.disconnect()
  }, [items])

  const go = id => {
    const el = document.getElementById(id)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  if (!items.length) return null

  return (
    <nav aria-label="Report sections" className="hidden xl:block w-52 shrink-0">
      <div className="sticky top-20">
        <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold mb-2 px-2">On this page</div>
        <ul className="space-y-0.5">
          {items.map(it => (
            <li key={it.id}>
              <button
                type="button"
                onClick={() => go(it.id)}
                aria-current={active === it.id ? 'true' : undefined}
                className={`w-full text-left text-sm px-2 py-1.5 rounded-lg border-l-2 transition-colors ${
                  active === it.id
                    ? 'border-gold text-gold bg-gold/5'
                    : 'border-transparent text-slate-400 hover:text-white hover:border-white/20'
                }`}
              >
                {it.label}
              </button>
            </li>
          ))}
        </ul>
        <button
          type="button"
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="mt-3 inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-gold px-2"
        >
          <ArrowUp size={13} aria-hidden="true" /> Back to top
        </button>
      </div>
    </nav>
  )
}
