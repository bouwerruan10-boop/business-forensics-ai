# Imara — Future-Proofing Plan
*Imara is operator-run/consulting today. This plan adds the cheap architectural seams now so a later pivot to mass distribution (B2C self-serve + B2B lenders) is a feature-add, not a rewrite. Principle: build the expensive-to-retrofit seams, defer the machinery (avoid YAGNI).*

## Why now (research)
- **Tenancy must be decided before the data model is finalised** — "migrating to a different model means restructuring the data layer — among the most expensive engineering efforts a SaaS company can undertake" ([SaaS multi-tenant 2025](https://zenn.dev/shineos/articles/saas-multi-tenant-architecture-2025?locale=en)). The recommended early pattern is **shared schema + a tenant/owner column (Pool)**; every read must be filterable by it. So we add the `owner` column and route data access through one place **now**, while there is only one tenant ("operator").
- **API versioning from day one** — for <50 enterprise clients, **URI path versioning (`/api/v1`)** is the pragmatic choice; design for change (optional fields, room to grow) so most evolution doesn't need a new version ([Speakeasy](https://www.speakeasy.com/api-design/versioning), [Userlens](https://userlens.io/blog/api-versioning-strategies-for-b2b-saas)). So we expose the B2B product surface — the **Imara Score** — as a versioned, documented contract now (dormant until the pivot).

## Phase 0 — seams to build NOW (operator-run, non-breaking) ← this cycle
1. **Ownership/tenant seam (Pool pattern).** Add `owner TEXT DEFAULT 'operator'` to `analyses` and `shares` (idempotent ALTER-COLUMN migration at startup). `create_analysis` records the owner; list/get accept an **optional** owner filter (unused today). One tenant ("operator") now; multi-tenant later is "set the filter", not "restructure the DB".
2. **Auth principal abstraction.** New `auth.py` with `Principal` + a `get_principal(request)` FastAPI dependency that returns the operator today and can resolve an API key / JWT → tenant later. Endpoints attach `principal.id` as `owner`. Swapping the resolver later never touches endpoint code.
3. **Config / feature flags** (`config.py`): `MULTI_TENANT=false`, `PUBLIC_API=false`. Behaviour is config-driven; the public surfaces stay dormant until flipped.
4. **Versioned, documented Imara Score contract.** `GET /api/v1/score/{analysis_id}` returns a stable schema (`schema_version`, `score`, `band`, `label`, `components[]`, `confidence`, `completeness`, `generated_at`) — the exact thing a B2B lender consumes. Gated behind `PUBLIC_API` (returns 404 until enabled). A `score_contract(report)` serialiser is the single source of that shape.
5. **Usage/cost tracking.** Persist a per-analysis usage summary (agents run, runtime, model) — billing-ready and useful for ops now; built from data the pipeline already produces.

## Phase 1 — ON PIVOT: multi-tenancy (do not build yet)
Implement `get_principal` to resolve API keys/JWT → tenant; enforce the `owner` filter on **every** query (pool-pattern isolation; consider a query helper that injects it so it can't be forgotten); per-user accounts/sessions; per-tenant rate limits.

## Phase 2 — ON PIVOT: B2B lender API
Flip `PUBLIC_API` on; issue per-tenant API keys; publish OpenAPI docs for the `/api/v1` Score + analysis-submit endpoints; add bulk submission and white-label report theming. The contract + versioning from Phase 0 make this additive.

## Phase 3 — ON PIVOT: B2C self-serve
Signup/login + billing (e.g. Stripe) metered off the Phase-0 usage records; self-serve onboarding; the intake wizard already exists.

## What this cycle deliberately does NOT do
Real login/signup, billing, full RBAC, OAuth, schema-per-tenant — all wait for the pivot decision. Phase 0 is invisible in operator mode and fully backward-compatible, verified by tests.
