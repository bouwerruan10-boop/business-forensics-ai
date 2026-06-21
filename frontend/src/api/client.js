// In dev, VITE_API_URL is empty and Vite proxies /api -> localhost:8000.
// In production, VITE_API_URL points at the Railway backend (cross-origin).
const API_ROOT = import.meta.env.VITE_API_URL || ''
const BASE = `${API_ROOT}/api`

// Optional API-key gate: only sent when VITE_API_KEY is configured. The backend
// enforces it only when API_SECRET_KEY is set, so this stays backward-compatible.
function authHeaders() {
  const key = import.meta.env.VITE_API_KEY
  return key ? { 'X-API-Key': key } : {}
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
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function pollStatus(analysisId) {
  const res = await fetch(`${BASE}/status/${analysisId}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getReport(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export function getPdfUrl(analysisId) {
  return `${BASE}/report/${analysisId}/pdf`
}

export async function simulate(analysisId, variable, changePercent, scenario) {
  const res = await fetch(`${BASE}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({
      analysis_id: analysisId,
      variable,
      change_percent: changePercent,
      scenario,
    }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getActions(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/actions`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function simulateActions(analysisId, actions, scenario = 'expected') {
  const res = await fetch(`${BASE}/simulate/actions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ analysis_id: analysisId, actions, scenario }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getLevers(analysisId, scenario = 'expected') {
  const res = await fetch(`${BASE}/report/${analysisId}/levers?scenario=${scenario}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function monteCarlo(analysisId, actions) {
  const res = await fetch(`${BASE}/simulate/montecarlo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ analysis_id: analysisId, actions }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getReasons(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/reasons`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getMacro(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/macro`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getLenderView(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/lender-view`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getNormalization(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}/normalization`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getOptimize(analysisId, scenario = 'expected', maxActions = 3, objective = 'imara') {
  const q = `scenario=${scenario}&max_actions=${maxActions}&objective=${objective}`
  const res = await fetch(`${BASE}/report/${analysisId}/optimize?${q}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await res.text())
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
