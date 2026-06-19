const BASE = '/api'

export async function uploadFiles(files, profile = {}) {
  const form = new FormData()
  for (const f of files) form.append('files', f)

  // Core profile fields
  if (profile.company_name)   form.append('company_name',   profile.company_name)
  if (profile.industry_key)   form.append('industry_key',   profile.industry_key)
  if (profile.annual_revenue) form.append('annual_revenue', String(profile.annual_revenue))
  if (profile.headcount)      form.append('headcount',      String(profile.headcount))
  if (profile.currency)       form.append('currency',       profile.currency)
  if (profile.country)        form.append('country',        profile.country)
  if (profile.primary_concern) form.append('primary_concern', profile.primary_concern)

  // SA-specific fields
  if (profile.entity_type)       form.append('entity_type',       profile.entity_type)
  if (profile.cipc_number)       form.append('cipc_number',       profile.cipc_number)
  if (profile.vat_registered)    form.append('vat_registered',    profile.vat_registered)
  if (profile.vat_number)        form.append('vat_number',        profile.vat_number)
  if (profile.tax_year_end)      form.append('tax_year_end',      profile.tax_year_end)
  if (profile.years_in_business) form.append('years_in_business', profile.years_in_business)
  if (profile.bbbee_level)       form.append('bbbee_level',       profile.bbbee_level)
  if (profile.banking_partner)   form.append('banking_partner',   profile.banking_partner)
  if (profile.report_audience)   form.append('report_audience',   profile.report_audience)

  // File category labels (JSON array matching files[] order)
  form.append('file_categories', profile.file_categories || '[]')

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
