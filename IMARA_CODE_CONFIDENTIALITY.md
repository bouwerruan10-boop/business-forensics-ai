# Imara — Code Confidentiality & Anti-Copy Policy

**Owner:** Ruan Bouwer · **Status:** living policy · **Last updated:** 2026-06-22

Goal: make it as hard as realistically possible for anyone — a user, a partner, a
contractor, or an attacker — to copy Imara's idea, code, or methodology.

---

## 1. The one principle that does 90% of the work

**Never give anyone the code. Give them access to the hosted service.**

Imara is hosted SaaS: the backend (agents, Imara Score, deterministic engines,
prompts, the SA legislation/rates corpus, AHP weights) runs ONLY on our server
(Railway). A user — including a pilot partner — receives the web UI and JSON API
responses, **not** the Python. As long as Imara stays SaaS, the valuable code is
structurally unreachable.

**Rule:** "give Imara to someone to use" ALWAYS means a login / API access to the
hosted instance. It NEVER means handing over the repository, a Docker image, a
build artifact, or an on-prem deployment. (See §6 for the on-prem exception.)

Reality check: code that runs on someone else's machine can always be extracted
(Python `.pyc` decompiles; a Docker image's contents are fully recoverable). The
only robust protection is to not ship it.

---

## 2. Threat model — who can copy what

| "Given to someone" | Can they get the code? | Control |
|---|---|---|
| Login to the hosted app (correct) | No — backend never leaves the server | This policy |
| Frontend JS in their browser | The UI bundle yes; backend no | Minified, source-maps off, zero logic/secrets in it |
| Teammate / contractor with repo or Railway/Vercel access | Yes — the real theft vector | Least-privilege access + NDA/IP assignment (§4, §5) |
| A Docker image / on-prem build we hand over | Yes, fully | Don't (§6) |
| API probing to reconstruct prompts/logic | Partially | Extraction guard + rate limits + prompts-as-public (§3) |

---

## 3. Technical controls (status)

- **Repo private** on GitHub. ✅
- **Secrets env-only**, never in code; `.env` git-ignored and untracked; no backend
  secret in the shipped frontend bundle (verified). ✅
- **Frontend**: Vite minifies; **source maps OFF** in prod (verified — no `.map` in
  the build). Note `VITE_API_KEY` ships in the browser bundle and is therefore NOT a
  secret — the real gate is the operator-password login + bearer token. ✅
- **Secret-scanning CI gate**: `gitleaks` runs on every push/PR (`.github/workflows/
  ci.yml`, `.gitleaks.toml`) and blocks a commit that contains a key. ✅
- **API prompt/logic-extraction guard**: Ask Imara refuses (and logs) attempts to
  reveal the system prompt, the model, the rules, or "how Imara works internally"
  (`services/ask.py::extraction_attempt`); prompts carry no secrets and the API never
  echoes them; analysis is rate-limited. ✅
- **TODO (GitHub UI, owner)**: enable 2FA, **branch protection** on `main`, GitHub
  native **secret scanning + push protection**, and restrict collaborators / Railway
  & Vercel team members to least privilege. Revoke access immediately on offboarding.

---

## 4. Legal controls — the strongest, most durable layer

Treat the source as a **trade secret** (protection lasts indefinitely while it stays
secret — unlike a patent). To hold up, we must show "reasonable measures":

- **NDA + IP-assignment** signed by anyone who touches the code (contractor,
  collaborator, partner, investor) BEFORE access. Template:
  `legal/IMARA_NDA_AND_IP_ASSIGNMENT_TEMPLATE.md`.
- **Terms of Use** for the hosted service prohibiting reverse-engineering, scraping,
  copying, and competitive reconstruction. Draft: `legal/IMARA_TERMS_OF_USE_DRAFT.md`.
- **Proprietary `LICENSE`** at the repo root (All Rights Reserved; explicitly NOT
  open source).
- This **crown-jewels inventory** (§7) — evidence of what we protect and that we
  identified it.
- Copyright is automatic; assert it with notices. Consider a provisional patent only
  for a genuinely novel method (trade secret is usually better for software).

> These documents are TEMPLATES — have a qualified South African attorney review them
> before use. They are not legal advice.

---

## 5. Access discipline (the real-world leak vector)

- GitHub: private; least-privilege collaborators; 2FA + branch protection; secret
  scanning + push protection; signed commits where practical; audit access quarterly.
- Railway/Vercel: lock team membership to need-to-know. The **Railway Console is a
  shell into the running container (full source + env)** — treat that access as
  crown-jewel-level.
- Offboarding: revoke GitHub + Railway + Vercel + key access the same day.
- Devices: full-disk encryption; no source on unmanaged machines.

---

## 6. The on-prem exception (avoid it)

If a partner DEMANDS self-hosting (e.g. a bank that won't let data leave its network),
the code runs on their machine and **cannot be made uncopyable** — we can only raise
the cost and rely on the contract. In order of preference:
1. **Hybrid / thin-client** — ship a thin connector; keep the scoring engine + agents
   as a remote call to OUR server, so the crown jewels never leave our infra.
2. Compile the crown-jewel modules to native binaries (Nuitka / Cython) + obfuscate +
   licence keys with phone-home (defeatable, but raises the bar) + a strong contract.
3. Confidential containers / TEEs (heavy; rarely worth it).
**Default: refuse on-prem; if forced, do (1) plus a heavy NDA/licence.**

---

## 7. Crown-jewels inventory (what we treat as trade secret)

- The **Imara Score** methodology, component weights, and AHP derivation.
- The **multi-agent pipeline** design and orchestration (CEO + specialists + SA + macro).
- The **deterministic engines**: financial ratios, tax optimiser, GAAR/SARS risk,
  macro sensitivity, distress (Z''), bank-signals, supplier benchmarking, simulation.
- All **agent system prompts** and `FINDING_RULES`.
- The curated **SA legislation/rates corpus** (`sa_knowledge`, `sa_rates`) and the
  supplier catalog.
- **Evaluation/golden sets**, judge labels, and validation/calibration harness.
- Deployment scripts, build config, and this documentation.

---

## 8. Honest limits
- Anything shipped to a browser or run off our infra is ultimately copyable — protection
  is about cost and law, not impossibility.
- Trade-secret protection ends the instant the secret leaks — so §4 and §5 are what keep
  it alive. The architecture (§1) is what makes leaks unlikely in the first place.
