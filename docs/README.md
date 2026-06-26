# Imara — Documentation Index

This `docs/` tree holds all non-code project documentation. Operational entry docs
(`CLAUDE.md`, `README.md`, `HANDOFF.md`, `SESSION_STATE.md`, `IMARA_IMPROVEMENT_ROADMAP.md`,
`MODEL_CARD.md`, `START.md`) remain at the **repo root** by design.

> Convention: new docs go in the subfolder matching their kind (plan / research / audit /
> runbook / gtm / prompt / report). The repo root stays lean — code, build/deploy config,
> operational scripts, and the few "read me first" entry docs only.

---

## docs/plans/ — design & implementation plans
Forward-looking "here's what we'll build / how" documents.
- `IMARA_IMPROVEMENT_ROADMAP.md` is **not** here — it lives at the repo root as the canonical living plan.
- Simulator: `IMARA_SIMULATION_PLAN.md`, `IMARA_SIMULATION_V2.md`, `IMARA_SIMULATOR_IMPROVEMENT_PLAN.md`
- UI: `IMARA_UI_FIX_PLAN.md`, `IMARA_UI_IMPROVEMENT_PLAN.md`
- Scope/strategy: `IMARA_DEEP_IMPROVEMENT_PLAN.md`, `IMARA_FUTUREPROOF_PLAN.md`, `IMARA_NEXT_STEPS.md`, `IMARA_NEXT_STRATEGY.md`, `IMPLEMENTATION_PLAN.md`, `IMPROVEMENT_PLAN.md`
- Domain: `IMARA_HARDENING_PLAN.md`, `IMARA_LENDER_VIEW_PLAN.md`, `IMARA_RESPONSIBLE_SCORE_PLAN.md`, `IMARA_VALIDATION_PLAN.md`, `IMARA_ECONOMICS_AGENT_PLAN.md` (future macro-economics agent)

## docs/research/ — research, feasibility & analysis
Evidence gathered before building (the "research before building" discipline).
- `ECOSYSTEM_FIT_ANALYSIS.md` (motivated Sentry+Langfuse), `IMARA_IMPROVEMENT_RESEARCH.md`
- `IMARA_AGENTS_AND_REDDIT_RESEARCH.md`, `IMARA_PER_AGENT_ANALYSIS_AND_RESEARCH.md`, `IMARA_VERIFIER_SWARM_RESEARCH.md`
- `IMARA_FUNDING_LANDSCAPE_RESEARCH.md`, `IMARA_PROFESSIONAL_LANDSCAPE_RESEARCH.md`
- `RESEARCH_CYCLE_ENGINE_FEASIBILITY.md`, `IMARA_SIMULATION_FEASIBILITY.md`
- Tax: `TAX_ME_IF_YOU_CAN_RESEARCH.md`, `TAX_PLANNER_INPUTS_RESEARCH.md`

## docs/audits/ — point-in-time audits & assessments
- `SECURITY_AUDIT_7POINT.md`, `IMARA_SECURITY_ASSESSMENT.md`
- `PERFORMANCE_AUDIT_5POINT.md`, `FRONTEND_RESILIENCE_AUDIT_5POINT.md`

## docs/runbooks/ — operational runbooks
- `DB_PERSISTENCE_RUNBOOK.md`, `BACKUP_RESTORE.md`, `SECURITY_HARDENING_RUNBOOK.md`, `IMARA_DEPLOYMENT_NOTES.md`

## docs/gtm/ — go-to-market, channel & pilot
- `IMARA_ACCOUNTANT_CHANNEL_KIT.md`, `IMARA_LENDER_CHANNEL_KIT.md`, `IMARA_GTM_OUTREACH_KIT.md`
- `IMARA_PILOT_PROTOCOL.md`, `IMARA_PILOT_ONBOARDING_AND_AGREEMENT.md`, `PILOT_PLAYBOOK.md`
- `IMARA_Accountant_Shortlist.csv`

## docs/prompts/ — saved working prompts
- `PROMPT_FOR_CLAUDE_CODE.md`, `CONTINUE_PROMPT.md`, `FRONTEND_PROMPT.md`, `DEPLOY_PROMPT.md`, `LIVE_TEST_PROMPT.md`

## docs/reports/ — generated client/investor outputs (git-ignored PDFs)
- `Imara_Investor_Report.pdf` + `Imara_Investor_Report_Accessible.html`
- `Imara_Capabilities_Report.pdf`, `IMARA_Design_Partner_Onepager.pdf`, `Imara_Explained_Simply.pdf`, `Imara_Agents_and_Reddit_Research.pdf`
- `assets/` — preview PNGs

## legal/ (repo root, not under docs/) — legal instruments & IP
- Drafts: operator agreement, privacy policy, compliance pack readme
- IP analysis: `IMARA_CODE_CONFIDENTIALITY.md`, `IMARA_TRADEMARK_RISK_BRIEF.md`

---

_Reorganised 2026-06-26. Earlier doc-to-doc links that pointed at the old repo-root paths
may now be stale; the files themselves are all preserved under the folders above._
