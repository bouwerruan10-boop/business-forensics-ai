# Imara Performance Audit — the 5-point "feels like molasses at scale" checklist

Audited 2026-06-23 against the code. **Framing:** this checklist targets a high-frequency, server-rendered CRUD app. Imara is a different shape — a **static SPA on a CDN** with an **async, LLM-bound analysis pipeline** and **low write frequency** (one analysis per submission, which is a multi-minute job). So most points are already handled by the architecture; **one is a real, easy win.**

| # | Point | Imara today | Verdict |
|---|---|---|---|
| 1 | JSON goes over the wire uncompressed | **No gzip/brotli middleware** | ⚠️ **Real win — add compression** |
| 2 | DB writes one row at a time | Single inserts, but findings bundled in-memory + tiny write volume | ✅ N/A at this scale |
| 3 | Single dependency bottleneck | Yes = the Anthropic LLM pipeline — by design, already async + parallelized | ✅ Identified & mitigated |
| 4 | Every action waits on backend before UI updates | Long analysis is async + polling; fast calls are server-computed | ✅ Handled where it matters |
| 5 | Front end rebuilds HTML per visitor | Static Vite SPA on Vercel CDN (no SSR) | ✅ N/A |

## 1 — Uncompressed JSON ⚠️ the one real fix
The only middleware on the backend is CORS — **no `GZipMiddleware`, no brotli**. The largest responses are `GET /api/report/{id}` (the full report dict, ~150–500 KB uncompressed) and the HTML report export. Text/JSON like this compresses ~80–90%, so a 300 KB report → ~30–40 KB over the wire. This is the highest-leverage, lowest-risk performance change available.
**Fix:** add `GZipMiddleware` (built-in, zero new dependency, `minimum_size≈500`), or `starlette-compress` for brotli+gzip content-negotiation (brotli ~18–24% smaller than gzip on JSON-heavy payloads). Either is a few lines + a test. Recommend gzip now (simplest); brotli later if payloads grow.

## 2 — Row-at-a-time writes ✅ N/A at Imara's write volume
Writes ARE single-insert-per-commit (`create_analysis`, `save_report`, `record_outcome`, the hash-chained `append_audit`). **But the trap this point warns about is already avoided:** findings are accumulated **in memory** (`shared_memory.add_finding` → `.append()`) and persisted as **one report-JSON blob**, not one row per finding. And the write frequency is tiny — one analysis row per submission (a multi-minute LLM job), one audit row per analysis, outcomes only when ops record them. There's no hot insert loop, so `executemany`/batching would optimize nothing measurable. Revisit only if outcome ingestion ever becomes high-frequency.

## 3 — Single dependency bottleneck ✅ identified & already mitigated
The dominant latency is unambiguously the **Anthropic API** — ~25–40 Claude calls per analysis (~11 min). That's inherent to an LLM analysis product, not a defect. It's already mitigated two ways: (a) the analysis runs as a **background task** and the frontend **polls `/api/status/{id}`**, so the user is never blocked on one long request; (b) agents are **parallelized** across a ThreadPoolExecutor in waves (`agents/parallel.py`). The interactive endpoints (report fetch, simulate, ask) are fast/deterministic. So the bottleneck is known and architecturally contained — there's no hidden single dependency to discover.

## 4 — UI waits on backend ✅ handled where it matters
The case that actually matters — the multi-minute analysis — is **non-blocking**: submit → get `analysis_id` → live progress screen polling status (`AnalysisProgress.jsx`). The fast interactive features (Action Simulator, Ask) show loading states and wait for the server, but their results are **server-computed** (a Monte-Carlo simulation or an LLM answer can't be optimistically predicted client-side), so optimistic UI doesn't genuinely apply. No blocking anti-pattern.

## 5 — Per-visitor HTML rebuild ✅ N/A
The frontend is a **static Vite SPA** built to `dist/` and served from **Vercel's CDN** (`vercel.json`: framework vite, SPA rewrite to `/index.html`, no SSR/Next server). It is **not** rebuilt per visitor — it's cached static assets at the edge. The backend's `/api/report/{id}/html` is a **downloadable report export** (a one-off artifact per analysis), not the site shell — so it's not per-visitor rendering.

## Prioritised actions
| Priority | Item | Effort | Note |
|---|---|---|---|
| **P1** | Add gzip (or brotli) response compression | Tiny | The one real win; ~80–90% smaller report payloads |
| — | DB batching (#2), optimistic UI (#4), SSR/CDN (#5) | — | Not needed — already handled by the architecture |
| Future | Revisit brotli + batched outcome ingestion | — | Only if payloads/write-frequency grow at the multi-user pivot |

**Bottom line:** Imara is already well-shaped for scale on 4 of 5 points (async pipeline, parallel agents, in-memory finding accumulation, static CDN SPA). The single concrete improvement is **enabling response compression** — a few lines for a large bandwidth/latency win on report payloads.

## Update — compression shipped (2026-06-23, v1.87)

- **P1 (#1) — DONE.** Added built-in `GZipMiddleware` (zero dependency) as the **innermost** middleware so it sees the route response WITH its `Content-Length` (the three `@app.middleware` BaseHTTPMiddleware layers strip Content-Length, which otherwise forces compression of every response). Verified: large JSON reports → `Content-Encoding: gzip` (~80-90% smaller; a synthetic 79 KB report → ~1 KB), tiny responses (e.g. the 2s `/api/status` polls, `/api/health`) and non-gzip clients are NOT compressed (minimum_size=500 honoured), body integrity preserved. +1 regression test.
- **Known minor trade-off:** the built-in middleware has no content-type filter, so the rare PDF download endpoint also gets gzipped (already-compressed → ~0% gain, negligible CPU at Imara's low PDF-download frequency). If binary-download volume ever grows, switch to `starlette-compress` (content-type-aware + brotli/zstd) — noted as the future upgrade.
- **#2–#5 unchanged: not needed** (already handled by Imara's architecture).
