import { useState } from 'react'
import { login } from '../api/client'

export default function Login({ onAuthed }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError(null); setBusy(true)
    try {
      await login(password)
      onAuthed()
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-navy font-sans flex items-center justify-center px-4">
      <form onSubmit={submit} className="w-full max-w-sm bg-navy-card border border-white/[0.08] rounded-2xl p-7">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-gold text-2xl font-bold">Imara</span>
        </div>
        <p className="text-slate-400 text-sm mb-6">Operator sign-in</p>

        <label className="block text-[11px] uppercase tracking-wider text-slate-400 mb-1.5" htmlFor="op-password">
          Password
        </label>
        <input
          id="op-password"
          type="password"
          autoFocus
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full bg-white/[0.04] border border-white/15 rounded-lg px-3 py-2 text-white text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/50 mb-4"
          placeholder="Enter operator password"
        />

        {error && (
          <div className="bg-red-500/10 border border-red-500/25 rounded-lg px-3 py-2 text-red-300 text-xs mb-4" role="alert">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={busy || !password}
          className="w-full bg-gold/90 hover:bg-gold disabled:opacity-50 disabled:cursor-not-allowed text-navy font-semibold rounded-lg px-3 py-2 text-sm transition-colors"
        >
          {busy ? 'Signing in…' : 'Sign in'}
        </button>

        <p className="text-slate-600 text-[11px] mt-5 leading-relaxed">
          This protects access to client analyses. Shared report links you've issued remain accessible to clients without sign-in.
        </p>
      </form>
    </div>
  )
}
