# Imara — Security Posture Assessment & Hardening Roadmap

**Date:** 22 June 2026
**Scope:** the whole stack — LLM/AI layer, FastAPI backend, React/Vercel frontend, SQLite-on-Railway data, secrets, supply chain, and POPIA obligations.
**Method:** research cycle across OWASP Top 10 for LLM Applications (2025), OWASP web/API + FastAPI hardening, secrets-management, POPIA s19 / Condition 7, and software-supply-chain best practice, then mapped to Imara's **actual, verified** code and config.

> **Honest headline:** Imara is already **security-forward** — far more than a typical vibe-built app. The deterministic-first DNA neutralises the #1 AI risk (prompt injection) for everything that matters (the numbers and the Score), access control and an audit chain are shipped, and the recent hardening passes closed the input-boundary crashes. This assessment finds **no critical hole**, a handful of **real, mostly cheap gaps**, and several **scale/pivot-gated** items. The quick wins were implemented in this session (see P0).

---

## 1. What we're protecting, and from what

- **Assets:** client financial documents + extracted figures (personal/financial info under POPIA), the Imara Score and reports, the audit chain, the operator/admin credentials, and the Anthropic API key (a cost + data conduit).
- **Threats:** prompt injection via uploaded documents; broken access control over client reports; a data breach of the financials DB; denial-of-service / cost-blowup on the LLM endpoints; secret leakage; and supply-chain (vulnerable dependency / AI-generated-code defect).

---

## 2. Posture by domain  (✅ done · ◑ partial · ⛔ gap)

### OWASP Top 10 for LLM Applications (2025)
| Risk | Status | Notes |
|---|---|---|
| LLM01 Prompt Injection | ✅ (numbers) / ◑ (prose) | **Deterministic-first**: all figures/ratios/Score are computed in code, so injected text in a document can never move them. `input_guard` sanitises + PII-redacts; `Ask Imara` has a pre-LLM scope guard. Residual: a narrative *sentence* could still be nudged by indirect injection — but faithfulness + prose verifiers cross-check narration against the computed facts. |
| LLM05 Improper Output Handling | ✅ | LLM output is never executed; it only narrates. Faithfulness (numeric) + prose (qualitative) verifiers validate it; structured-outputs guarantee schema. The v1.41 non-dict-synthesis guard hardened this path. |
| LLM06 Excessive Agency | ✅ | Agents have **no tools and take no actions** — no email, no DB writes, no external calls on the model's say-so. Output is a report a human reads. Lowest-risk by design. |
| LLM04/10 Unbounded Consumption / Cost / DoS | ✅ | slowapi rate-limit; `Ask Imara` caps (500-char Q, 600 tokens, Haiku); 25 MB upload cap + 40-file cap; parser is time-bounded; per-analysis token/cost ledger. |
| LLM02 Sensitive Info Disclosure | ◑ | PII redacted pre-LLM; cross-border transfer to the US API disclosed + consented. Gaps: **at-rest DB encryption unverified**; document text does leave SA (s72 — needs the attorney sign-off already flagged). |
| LLM03 Supply chain (models/data) | ✅/N-A | No fine-tuning, no vector store, deterministic retrieval over a dated SA-law corpus. Dependency supply chain → below. |

### OWASP Web / API + FastAPI
| Control | Status | Notes |
|---|---|---|
| A01 Broken Access Control | ✅ | Operator login **active**; admin-key gate on `/api/admin/*`; expiring/revocable share tokens; unguessable UUID4 IDs. (No per-user RBAC — operator mode by design; seam shipped for the pivot.) |
| A03 Injection | ✅ | Deterministic core immune; SQLite via parameterised queries; `input_guard` over free text. |
| Security headers | ✅ **(added this session)** | HSTS, X-Content-Type-Options, X-Frame-Options=DENY, Referrer-Policy, Permissions-Policy now on every response. |
| CORS | ◑ | Restricted to the Vercel origin + localhost (not wildcard) — good. Minor: the `*.vercel.app` regex is a touch broad; tighten to the exact host at the pivot. |
| Error-message leakage | ✅ **(fixed this session)** | The PDF endpoint leaked the raw exception string; now logs internally + returns a generic message. |
| Auth strength / MFA | ◑ | Single operator password (bcrypt-style token). No MFA — proportionate at single-operator scale; **add MFA at the multi-user pivot.** |
| `/docs` + `/openapi.json` exposure | ◑ | Open in prod (schema/route enumeration). Routes are gated, so low impact; disable or gate at the pivot. |
| Rate limiting | ✅ | slowapi, X-Forwarded-For keyed; dedicated `/ask` cap. |

### Secrets
| Control | Status | Notes |
|---|---|---|
| No hardcoded keys / `.env` gitignored | ✅ | Keys in Railway env; `backend/.env`, `.env`, `*.env` all gitignored — no secret in git. |
| Rotation | ⛔ | No rotation schedule; keys are long-lived. **Rotate the Anthropic + admin keys, set a 90-day reminder.** |
| Secret-scanning in CI | ⛔ | No gitleaks/trufflehog gate. Cheap to add. |

### POPIA s19 / Condition 7 (Security Safeguards)
| Requirement | Status | Notes |
|---|---|---|
| Reasonable technical + organisational measures | ◑→good | input guard, hash-chained audit log, consent capture, retention purge, decision-support framing. |
| Encryption in transit | ✅ | Railway + Vercel enforce HTTPS/TLS. |
| Encryption at rest | ⛔ **verify** | SQLite on the Railway volume holds client financials. **Confirm Railway volume encryption, or move to SQLCipher / an encrypted store.** Top POPIA gap. |
| Access control | ✅ | operator + admin gates. |
| Backups | ✅ | opt-in scheduled, off-volume, restore documented. |
| Information Officer registered | ⛔ | **Mandatory** — Ruan to register with the Information Regulator. |
| Periodic penetration test | ⛔ | None yet (King IV / POPIA expectation at scale). |

### Software supply chain
| Control | Status | Notes |
|---|---|---|
| Dependency CVE scanning | ✅ **(added this session)** | `pip-audit` runs in CI (advisory); promote to a gate once clean. |
| Automated update PRs | ✅ **(added this session)** | `.github/dependabot.yml` for pip + npm + actions, weekly. |
| AI-generated-code review | ✅ | Dormant AI PR-review action (v1.36) covers logic/security on PRs. |
| Pinning / lockfile | ◑ | `requirements.txt` uses `>=` floors, not `==`/hashes. **Pin + add a lockfile** for reproducible, tamper-resistant builds. |

---

## 3. Prioritised hardening roadmap

### P0 — implemented in this session ✅
- **Security-response headers** middleware (HSTS, nosniff, X-Frame-Options, Referrer-Policy, Permissions-Policy) + a regression test.
- **Dependency CVE scanning** (`pip-audit`) in CI + **Dependabot** config (pip/npm/actions).
- **Error-message leak fix** (PDF endpoint no longer returns the raw exception).

### P0 — remaining, cheap, do now (Ruan-led config)
1. **Verify / enable at-rest encryption** of the Railway volume holding the financials DB (or adopt SQLCipher). *The single most important POPIA gap.*
2. **Register the Information Officer** with the Information Regulator (POPIA-mandatory) and get the attorney's sign-off on the drafted POPIA pack + the s72 cross-border transfer to the US API.
3. **Rotate the Anthropic + admin keys** and set a 90-day rotation reminder.
4. **Add a Content-Security-Policy on the frontend** via Vercel headers config (CSP belongs on the HTML-serving layer, not the JSON API).

### P1 — buildable soon (I can do)
- Pin dependencies + lockfile; promote `pip-audit` from advisory to a CI gate once clean.
- Add **secret-scanning** (gitleaks) to CI as a hard gate.
- ✅ **(done v1.43)** Disabled `/docs` + `/redoc` + `/openapi.json` in production (gated behind `EXPOSE_DOCS`, default off).
- ✅ **(done v1.43)** Tightened the CORS regex to this project's Vercel deploys only (`business-forensics-ai-*.vercel.app`), not any `*.vercel.app` site.
- A hard per-analysis token/cost budget (belt-and-braces over the existing caps).

### P2 — scale / pivot-gated (don't build before needed)
- **MFA** + per-user **RBAC** / per-tenant data scoping (the `owner` seam is shipped) — at the multi-user pivot.
- External **penetration test** + a documented incident-response runbook.
- **WAF / Cloudflare** in front for DDoS + bot management at volume.
- **SBOM** artifact in CI (`trivy`/CycloneDX) for instant zero-day blast-radius lookup.
- A managed **secrets manager** (Vault / Railway secrets API) over plain env vars.

---

## 4. The one-line verdict

Imara has **no critical security hole**, an unusually strong AI-risk posture (deterministic-first kills prompt injection for the numbers, and the agents have no agency to abuse), and now hardened headers + dependency scanning. The remaining must-dos are **operational, not architectural**: encrypt the data at rest, register the Information Officer, rotate keys, and put a CSP on the frontend — all before a pilot puts real client financials through it.

---

*Sources: OWASP Top 10 for LLM Applications 2025 (genai.owasp.org); OWASP Secure Headers Project + Cheat Sheets; FastAPI security docs + production-hardening guides; API-key rotation / secrets-management best practice (GitGuardian, AWS); POPIA s19 / Condition 7 security-safeguard guidance (Scytale, SecOps, compliance guides); Python supply-chain + pip-audit / Dependabot / SBOM guidance (PyPA, bernat.tech). This is a security risk-scoping document, not a penetration test or legal advice; a formal pen-test + attorney review are recommended before scale.*
