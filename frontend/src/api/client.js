// In dev, VITE_API_URL is empty and Vite proxies /api -> localhost:8000.
// In production, VITE_API_URL points at the Railway backend (cross-origin).
const API_ROOT = import.meta.env.VITE_API_URL || ''
const BASE = `${API_ROOT}/api`

// Optional API-key gate: only sent when VITE_API_KEY is configured. The backend
// enforces it only when API_SECRET_KEY is set, so this stays backward-compatible.
const TOKEN_KEY = 'imara_operator_token'
export function getToken() { try { return sessionStorage.getItem(TOKEN_KEY) || '' } catch { return '' } }
export function setToken(t) { try { t ? sessionStorage.setItem(TOKEN_KEY, t) : sessionStorage.removeItem(TOKEN_KEY) } catch { /* ignore */ } }
export function logout() { setToken('') }

function authHeaders() {
  const h = {}
  const key = import.meta.env.VITE_API_KEY
  if (key) h['X-API-Key'] = key
  const tok = getToken()
  if (tok) h['Authorization'] = `Bearer ${tok}`
  return h
}

// Turn a non-OK response into a human-readable Error, never raw HTML / server text
// (avoids dumping stack-trace-ish strings into the UI; surfaces the backend's detail).
async function _friendlyError(res) {
  if (res.status === 429) return new Error('Rate limit reached - too many analyses in a short time. Please wait a little and try again.')
  if (res.status === 401) return new Error('Your session has expired or the key is invalid. Please sign in again.')
  if (res.status === 413) return new Error('Upload too large. Please reduce the file sizes and try again.')
  if (res.status >= 500) return new Error('The server hit an error. Please try again shortly.')
  let detail = ''
  try { const j = await res.json(); detail = j && j.detail ? j.detail : '' } catch { /* response was not JSON */ }
  return new Error(detail || `Request failed (${res.status}).`)
}

export async function getHealth() {
  const res = await fetch(`${BASE}/health`)
  if (!res.ok) throw new Error('health check failed')
  return res.json()
}

export async function login(password) {
  const res = await fetch(`${BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  })
  if (!res.ok) {
    const e = await res.json().catch(() => ({}))
    throw new Error(e.detail || 'Login failed')
  }
  const data = await res.json()
  if (data.token) setToken(data.token)
  return data
}

export async function uploadFiles(files, profile = {}) {
  const form = new FormData()
  for (const f of files) form.append('files', f)

  if (profile.company_name)   form.append('company_name',   profile.company_name)
  if (profile.industry_key)   form.append('industry_key',   profile.industry_key)
  if (profile.annual_revenue) form.append('annual_revenue', String(profile.annual_revenue))
  if (profile.headcount)      form.append('headcount',      String(profile.headcount))
  if (profile.currency)       form.append('currency',       profile.currency)
  if (profile.country)        form.append('country',        profile.country)
  if (profile.primary_concern) form.append('primary_concern', profile.primary_concern)
  if (profile.consent)        form.append('consent',        String(profile.consent))
  if (profile.consent_at)     form.append('consent_at',     profile.consent_at)

  if (profile.entity_type)       form.append('entity_type',       profile.entity_type)
  if (profile.cipc_number)       form.append('cipc_number',       profile.cipc_number)
  if (profile.vat_registered)    form.append('vat_registered',    profile.vat_registered)
  if (profile.vat_number)        form.append('vat_number',        profile.vat_number)
  if (profile.tax_year_end)      form.append('tax_year_end',      profile.tax_year_end)
  if (profile.years_in_business) form.append('years_in_business', profile.years_in_business)
  if (profile.bbbee_level)       form.append('bbbee_level',       profile.bbbee_level)
  if (profile.banking_partner)   form.append('banking_partner',   profile.banking_partner)
  if (profile.report_audience)   form.append('report_audience',   profile.report_audience)

  form.append('file_categories', profile.file_categories || '[]')

  const res = await fetch(`${BASE}/analyze`, { method: 'POST', body: form, headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function pollStatus(analysisId) {
  const res = await fetch(`${BASE}/status/${analysisId}`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function getReport(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export function getPdfUrl(analysisId) {
  return `${BASE}/report/${analysisId}/pdf`
}

export async function getActions(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/actions`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function simulateActions(analysisId, actions, scenario = 'expected') {
  const res = await fetch(`${BASE}/simulate/actions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ analysis_id: analysisId, actions, scenario }),
  })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function getLevers(analysisId, scenario = 'expected') {
  const res = await fetch(`${BASE}/report/${analysisId}/levers?scenario=${scenario}`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function monteCarlo(analysisId, actions) {
  const res = await fetch(`${BASE}/simulate/montecarlo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ analysis_id: analysisId, actions }),
  })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function getReasons(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/reasons`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function getMacro(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/macro`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function getCashflow(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/cashflow`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function getLenderView(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/lender-view`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function getNormalization(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/normalization`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function getCreditMemo(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/credit-memo`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function getWorkingCapital(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/working-capital`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export function getBankReadyPackUrl(analysisId) {
  return `${BASE}/report/${analysisId}/bank-ready-pack`
}

export async function getFundingFit(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/funding-fit`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function getOwnerRisk(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/owner-risk`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function getFunderGates(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/funder-gates`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function getInsuranceCession(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/insurance-cession`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function getOptimize(analysisId, scenario = 'expected', maxActions = 3, objective = 'imara') {
  const q = `scenario=${scenario}&max_actions=${maxActions}&objective=${objective}`
  const res = await fetch(`${BASE}/report/${analysisId}/optimize?${q}`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function askImara(analysisId, question) {
  const res = await fetch(`${BASE}/report/${analysisId}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ analysis_id: analysisId, question }),
  })
  if (!res.ok) throw new Error('ask failed')
  return res.json()
}

// Tax Me If You Can — relocation / tax-efficiency first pass. Public POST endpoint;
// returns destinations, stay_and_optimise levers, sequencing, guardrails + disclaimers.
export async function getTaxRelocation(payload) {
  const res = await fetch(`${BASE}/tax/relocation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(payload || {}),
  })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

// SA income / VAT / ETI assessment from IRP5-style inputs. Public POST endpoint;
// returns { income_tax, vat, eti, disclaimer } (sections present only when supplied).
export async function getTaxIncome(payload) {
  const res = await fetch(`${BASE}/tax/income`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(payload || {}),
  })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function getRatioDiagnostics(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/ratio-diagnostics`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}

export async function getActionConstraints(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/action-constraints`, { headers: authHeaders() })
  if (!res.ok) throw await _friendlyError(res)
  return res.json()
}
