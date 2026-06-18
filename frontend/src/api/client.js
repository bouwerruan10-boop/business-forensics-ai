const BASE = '/api'

export async function uploadFiles(files, profile = {}) {
  const form = new FormData()
  for (const f of files) form.append('files', f)
  // Attach business profile fields so backend agents have full context
  if (profile.company_name) form.append('company_name', profile.company_name)
  if (profile.industry_key) form.append('industry_key', profile.industry_key)
  if (profile.annual_revenue) form.append('annual_revenue', String(profile.annual_revenue))
  if (profile.headcount) form.append('headcount', String(profile.headcount))
  if (profile.currency) form.append('currency', profile.currency)
  if (profile.country) form.append('country', profile.country)
  if (profile.primary_concern) form.append('primary_concern', profile.primary_concern)

  const res = await fetch(`${BASE}/analyze`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function pollStatus(analysisId) {
  const res = await fetch(`${BASE}/status/${analysisId}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getReport(analysisId) {
  const res = await fetch(`${BASE}/report/${analysisId}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export function getPdfUrl(analysisId) {
  return `${BASE}/report/${analysisId}/pdf`
}

export async function simulate(analysisId, variable, changePercent, scenario) {
  const res = await fetch(`${BASE}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
