import { Component } from 'react'

// App-level error boundary: a render error in any component shows a friendly fallback
// (with reset + reload) instead of a blank white screen. Sentry-ready: when @sentry/react
// is added later, window.Sentry.captureException is called automatically.
export default class ErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    if (typeof window !== 'undefined' && window.Sentry && window.Sentry.captureException) {
      try { window.Sentry.captureException(error, { extra: info }) } catch { /* ignore */ }
    }
    try { console.error('Imara render error:', error, info && info.componentStack) } catch { /* ignore */ }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen bg-navy flex items-center justify-center px-6 font-sans">
          <div className="max-w-md w-full rounded-2xl border border-white/10 bg-white/[0.03] p-8 text-center">
            <div className="text-gold text-3xl mb-3" aria-hidden="true">&#9888;</div>
            <h1 className="text-white text-lg font-bold mb-2">Something went wrong</h1>
            <p className="text-slate-400 text-sm mb-6">
              An unexpected error interrupted the page. Your data is safe — try again, or reload.
            </p>
            <div className="flex gap-2 justify-center">
              <button
                type="button"
                onClick={() => this.setState({ error: null })}
                className="rounded-lg px-4 py-2 text-sm font-semibold bg-gold text-navy hover:bg-gold/90 transition-colors"
              >
                Try again
              </button>
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="rounded-lg px-4 py-2 text-sm font-semibold border border-white/15 text-slate-300 hover:text-white hover:border-white/30 transition-colors"
              >
                Reload page
              </button>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
