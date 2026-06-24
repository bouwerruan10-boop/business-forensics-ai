import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import * as Sentry from '@sentry/react'
import './index.css'
import App from './App.jsx'
import ErrorBoundary from './components/ErrorBoundary'

// Error monitoring (opt-in). Activates only when VITE_SENTRY_DSN is set at build
// time (Vercel env); otherwise this is a no-op and nothing is sent. We expose the
// initialised client on window.Sentry so the existing ErrorBoundary can report
// React render errors. sendDefaultPii is false - no PII, and beforeSend drops any
// captured request body as a second guard (Imara handles confidential financials).
const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN
if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: import.meta.env.VITE_SENTRY_ENV || 'production',
    sendDefaultPii: false,
    tracesSampleRate: 0,
    beforeSend(event) {
      if (event.request) { delete event.request.data; delete event.request.cookies }
      return event
    },
  })
  if (typeof window !== 'undefined') window.Sentry = Sentry
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
