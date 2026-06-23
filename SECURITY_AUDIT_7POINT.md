# Imara Security Audit — the 7-point "don't get hacked" checklist

Audited 2026-06-23 against the checklist (ranked least→most important) and cross-referenced to the
**OWASP API Security Top 10 (2023)**. Evidence is cited file:line. Verdict up front:

> **Imara is already strong on 6 of the 7 points.** The one real gap is the one you ranked #1 —
> **authorization (BOLA)** — and even that is *benign in the current single-operator setup* but becomes
> **critical the moment Imara serves more than one user/tenant** (the documented pivot direction).

| # (your rank) | Point | OWASP | Verdict |
|---|---|---|---|
| 7 | Safer defaults (least-priv, tokens, HTTPS) | API8 Misconfig | ✅ Strong |
| 6 | Logging & monitoring | Observability | ✅ Strong |
| 5 | Audit your packages | API10 Unsafe Consumption | ✅ Good (1 dev-only npm advisory) |
| 4 | No secrets in the frontend | Secrets mgmt | ✅ Safe |
| 3 | Treat all client input as untrusted | API3/injection | ✅ Strong (2 minor hardenings) |
| 2 | Authentication (no dodgy JWT) | API2 Broken Auth | ✅ Strong (2 medium hardenings) |
| 1 | **Authorization (does this user own this record?)** | **API1 BOLA** | ⚠️ **Latent CRITICAL — fix before multi-user** |

---

## 7 — Default to safer settings ✅ Strong

- **CORS** is locked to the Vercel frontend + localhost (+ a preview-deploy regex), **not** `allow_origins=['*']` (`main.py` CORS middleware).
- **Security headers** on every response: `Strict-Transport-Security` (HSTS), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, `Cache-Control: no-store` (`main.py` headers middleware).
- **API docs hidden** by default (`/docs`, `/redoc`, `/openapi.json` → 404 unless `EXPOSE_DOCS`).
- **HTTPS** is enforced by Railway (backend) and Vercel (frontend) at the platform edge; HSTS tells browsers to refuse plain HTTP.
- **Least privilege:** the Anthropic key lives only in the backend; the frontend holds no privileged token.
- Constant-time (`hmac.compare_digest`) comparisons for every key/password/secret.

No action required.

## 6 — Logging & monitoring ✅ Strong

- **Structured logging** (`structlog` + stdlib) with a per-request `request_id` and `analysis_id` bound to every line (`obs.py`, `main.py` request-logging middleware) — JSON in production.
- **Error monitoring**: Sentry wired, activates on `SENTRY_DSN`, with `send_default_pii=False`.
- **Tamper-evident audit log**: hash-chained decision records (`prev_hash`/`record_hash`) with a chain-verify endpoint — governance/AI-Act evidence.
- **No stack traces leak to clients** — failures return a generic message; the trace is logged server-side only.

No action required. (Optional: confirm `SENTRY_DSN` is set in production so you actually capture errors.)

## 5 — Audit your packages ✅ Good

Actual scans run this session:

- **Python (`pip-audit`): _No known vulnerabilities_.** Deps are current (FastAPI, pydantic v2, anthropic, etc.).
- **Node (`npm audit`): 3 findings (2 moderate, 1 high) — ALL in the dev toolchain** (`esbuild` → `vite` → `vite-plugin-pwa`). The esbuild advisory (GHSA-67mh-4wv8-2f99) only affects the local **dev server**; it has **no effect on the production build** Vercel serves (static assets, no esbuild dev server in prod).
- **HTTP client:** the frontend uses the browser's native `fetch`, **not axios** — so there's no axios CVE surface (your "google Axios" hint: axios is a popular HTTP library that has had several CVEs; Imara avoids that dependency entirely).

Action (low priority): bump Vite to a current major when convenient to clear the dev-only advisories (`npm audit fix --force` → vite 8; breaking, test the build). Add `pip-audit` + `npm audit` to CI so this is continuous.

## 4 — No secrets in the frontend ✅ Safe

- The only `import.meta.env.VITE_*` vars are `VITE_API_URL` (the backend URL — not a secret) and an optional `VITE_API_KEY` used for the X-API-Key header. **Anything `VITE_`-prefixed is baked into the public JS bundle**, so it must never hold a real secret — confirmed it doesn't.
- `ANTHROPIC_API_KEY` is referenced **only** in the backend (`config.py`), never in `frontend/`.

Action (note): if you ever set `VITE_API_KEY`, treat it as public — only use a low-privilege, rate-limited key there, never the Anthropic key or an admin key.

## 3 — Treat all client input as untrusted ✅ Strong

- **Validation:** request bodies use Pydantic models (`LoginRequest`, `AskRequest`, `ActionSimRequest`, `OutcomeIn`).
- **SQL injection:** all data queries are **parameterized** (`?` placeholders) — no f-string/format SQL on user input. (One internal `PRAGMA table_info({table})` uses `.format()`, but `table` is a hardcoded constant, never user input — low risk, worth tidying.)
- **Uploads:** capped at ≤40 files, ≤25 MB/file, ≤150 MB total, rejected early; files are parsed **in memory** and never written to disk under a user-supplied name, so there's no path-traversal vector.
- **Prompt injection:** a deterministic **input sanitizer** defangs injection directives + redacts PII before any agent sees uploaded text, and the "Ask Imara" endpoint has scope + system-prompt-extraction guards.
- **Output:** `SafeJSONResponse` sanitises every response (this is what made the hostile-input pressure tests return valid JSON).

Action (low): explicitly reject non-document upload types (`.exe`/`.zip`/etc.) and quote the PRAGMA identifier — both are belt-and-braces, not live holes.

## 2 — Authentication ✅ Strong (2 medium hardenings)

The token is a custom HMAC-SHA256 signed token (`auth.py`), and it avoids the classic JWT traps:

- **Signed + verified** with `hmac.compare_digest` (constant-time) — no signature-skip.
- **No `alg:none` / algorithm-confusion** risk (the format has no attacker-controlled `alg` header).
- **Expiry enforced** (`exp`, default 12h); missing `exp` → rejected.
- Operator gate is **fail-closed** when `OPERATOR_PASSWORD` is set; login password compared in constant time.

Hardenings:

- **(Medium) Set `AUTH_SECRET` explicitly in production.** If unset it's *derived* from the operator password; setting an independent random `AUTH_SECRET` decouples token-forgery resistance from password strength.
- **(Medium) Rate-limit `/api/login`.** Today the global limiter covers `/api/analyze` and `/ask` but not login, so password guessing is unthrottled. Add e.g. `5/minute` per IP.

## 1 — Authorization (BOLA) ⚠️ Latent CRITICAL — the one to fix

This is OWASP **API1:2023 Broken Object Level Authorization** — ~40% of API attacks, and the cause of the Optus breach (predictable IDs + no per-record owner check).

**The finding:** the `analyses` table has an `owner` column, but the read paths **don't enforce it**:

- `GET /api/report/{analysis_id}` and its ~25 sub-resources call `get_report(analysis_id)` →
  `SELECT report_json FROM analyses WHERE id = ?` — **no `AND owner = ?`** (`database.py` `get_report`).
- `POST /api/report/{analysis_id}/share` checks the analysis *exists*, not that the caller *owns* it.

**Why it's not exploitable today:** there is exactly **one** operator, so "any operator can read any report" = "the operator reads their own reports." Analysis IDs are UUIDv4 (unguessable), and the operator gate still requires a valid token. Share tokens are 128-bit and safe.

**Why it's critical the moment you add a second user/tenant** (your B2C + lender pivot): with owner unenforced, any logged-in user who obtains/guesses another tenant's `analysis_id` could read their full financial report. The plumbing (`owner` column, `get_analysis(owner=…)` already supports the filter) is there — it's just **not wired into the read paths**.

**Fix (cheap, backward-compatible):** thread the authenticated principal into the report/share reads and add `AND owner = ?`. Existing rows default to `owner='operator'` and the single operator's principal is `'operator'`, so the filter matches everything today — zero behaviour change now, full isolation the day you go multi-user. Add two regression tests: "user A cannot read user B's report" and "user A cannot share user B's analysis."

---

## Prioritised remediation

| Priority | Item | Effort | Note |
|---|---|---|---|
| **P0** | Enforce `owner` on all report reads + share-create (BOLA) + 2 tests | Small | Backward-compatible; the future-proofing seam you wanted |
| P1 | Rate-limit `/api/login` (e.g. 5/min/IP) | Tiny | Closes password brute-force |
| P1 | Set an independent `AUTH_SECRET` in Railway env | Config | Decouple token forgery from password |
| P2 | Bump Vite (clears dev-only npm advisories) + add `pip-audit`/`npm audit` to CI | Small | Continuous supply-chain checks |
| P3 | Reject non-document upload types; quote the PRAGMA identifier | Tiny | Belt-and-braces |

**Bottom line:** the foundations are genuinely solid — strong auth, locked CORS, full headers, parameterised SQL, prompt-injection guards, clean dependency scans, no frontend secrets. The single thing that deserves action before any multi-user/tenant launch is **enforcing object-level ownership (BOLA)**, which is small and backward-compatible to add now.

---

## Update — remediation shipped (2026-06-23, v1.83)

- **P0 (BOLA) — DONE.** Object-level ownership now enforced centrally in the operator-gate middleware for all path-id routes, `require_owned()` on the body-id simulate POSTs, share-create owner-scoped. Backward-compatible; a meta-test fails CI if a new report/status route escapes the gate. (`test_bola_authz.py`, 5 tests.)
- **P1 — DONE.** `/api/login` rate-limited to 5/min (verified 429); startup warns when `AUTH_SECRET` is derived rather than set.
- **P2/P3 — open:** bump Vite + add pip-audit/npm audit to CI; upload-type allowlist; quote the internal PRAGMA identifier.

## Update — P2/P3 closeout (2026-06-23, v1.84)

- **P2 — DONE.** `npm audit` added to frontend CI (production deps near-gated; full audit advisory). `pip-audit` already gated the backend. **Vite major bump deferred** (the advisories are dev-toolchain only / no production impact — Vercel serves static assets; gating `--omit=dev` proves prod deps clean).
- **P3 — DONE.** Upload-type allowlist rejects non-document files; `_add_owner_column` is injection-proof (table allowlist + quoted identifier + parameterised pragma).
- **All 7 points are now addressed.** Remaining: optional Vite 5→8 bump (deferred by design, dev-only advisory).
