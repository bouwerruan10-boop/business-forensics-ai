import { useState } from 'react'

export default function AskImara({ report, analysisId }) {
  const [open, setOpen] = useState(false)
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  if (!analysisId) return null

  const score = report?.imara_score
  const suggestions = [
    score != null ? `Why is my score ${score}?` : 'Why is my score what it is?',
    'What should I fix first?',
    'Where can I save money?',
    'Am I bankable?',
  ]

  async function ask(q) {
    const question = (q || input).trim()
    if (!question || loading) return
    setMsgs((m) => [...m, { role: 'user', text: question }])
    setInput('')
    setLoading(true)
    try {
      const { askImara } = await import('../api/client')
      const r = await askImara(analysisId, question)
      setMsgs((m) => [...m, { role: 'imara', text: r.answer || 'No answer.' }])
    } catch (e) {
      setMsgs((m) => [...m, { role: 'imara', text: 'Sorry, I could not answer right now.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col items-end">
      {open && (
        <div className="mb-3 w-[min(92vw,380px)] h-[70vh] max-h-[560px] flex flex-col bg-navy-card border border-gold/25 rounded-2xl shadow-2xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
            <div className="text-white text-sm font-semibold">&#10022; Ask Imara</div>
            <button onClick={() => setOpen(false)} className="text-slate-400 hover:text-white text-xl leading-none" aria-label="Close">&times;</button>
          </div>
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {msgs.length === 0 && (
              <div className="text-slate-400 text-xs">
                <p className="mb-2">Ask anything about this analysis. I only use the numbers in your report.</p>
                <div className="flex flex-wrap gap-1.5">
                  {suggestions.map((s, i) => (
                    <button key={i} onClick={() => ask(s)} className="text-[11px] text-slate-200 bg-white/[0.05] border border-white/10 rounded-full px-2.5 py-1 hover:bg-white/10">{s}</button>
                  ))}
                </div>
              </div>
            )}
            {msgs.map((m, i) => (
              <div key={i} className={m.role === 'user' ? 'text-right' : ''}>
                <div className={`inline-block text-sm rounded-2xl px-3 py-2 max-w-[85%] leading-relaxed ${m.role === 'user' ? 'bg-gold text-[#0D1B2A]' : 'bg-white/[0.06] text-slate-200'}`}>{m.text}</div>
              </div>
            ))}
            {loading && <div className="text-slate-500 text-xs">Imara is thinking&hellip;</div>}
          </div>
          <div className="p-3 border-t border-white/10 flex gap-2">
            <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && ask()}
              placeholder="Ask about this report&hellip;"
              className="flex-1 bg-white/[0.05] border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-gold/40" />
            <button onClick={() => ask()} disabled={loading} className="bg-gold text-[#0D1B2A] text-sm font-semibold rounded-lg px-3 py-2 disabled:opacity-50">Send</button>
          </div>
          <div className="px-4 pb-2 text-[10px] text-slate-600">Decision-support, grounded in your report. Not financial advice.</div>
        </div>
      )}
      <button onClick={() => setOpen((o) => !o)} className="flex items-center gap-2 bg-gold text-[#0D1B2A] font-semibold text-sm rounded-full px-4 py-3 shadow-lg hover:brightness-110 transition">
        &#10022; Ask Imara
      </button>
    </div>
  )
}
