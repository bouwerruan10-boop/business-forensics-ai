# Imara — POPIA Compliance Pack (cover note)

**What this is:** three POPIA-grounded **drafts** I prepared so your attorney has a 90%-complete starting point instead of a blank page — they cut legal time and cost, but they are **not legal advice and must be reviewed by an SA admitted attorney before use.**

| File | What it covers | Who reads it |
|---|---|---|
| `IMARA_PRIVACY_POLICY_DRAFT.md` | What data Imara collects, why, the AI/cross-border processing, security, retention, rights (POPIA s18) | Public — publish on the site / share with clients |
| `IMARA_TERMS_OF_USE_DRAFT.md` | Acceptable use + the decision-support-not-advice / not-an-NCA-decision / not-FAIS shield | Anyone who uses Imara |
| `IMARA_OPERATOR_AGREEMENT_DRAFT.md` | The POPIA **s21** operator (data-processing) agreement Imara signs with each client | Each design-partner / client |

## Why this is the right next step (per the roadmap)
The bottleneck is **distribution** — getting Imara in front of a design partner. The moment a lender or accountant runs **real client financials** through Imara, you're processing third-party personal information under POPIA (fines to **R10M**). You cannot responsibly do the pilot without these in place, so this directly unblocks Tier 0.

## Action list (yours / your attorney's)
1. **Fill the placeholders** — registered entity name, CIPC reg no., address, Information Officer name/contact, dates.
2. **Register the Information Officer** with the **Information Regulator** (the CEO/operator is the default IO and registration is mandatory before processing — don't skip this).
3. **⚠ Resolve the Anthropic cross-border (s72) basis** — this is the one genuinely material item. Client document text is sent to the Anthropic API in the US. Your attorney must confirm and record the lawful transfer basis (adequate-protection contract terms / necessity for the contract / consent). Until then, lead with the deterministic outputs and the PII redaction that's already built in.
4. **Attorney review** of all three documents, then publish the Privacy Policy + Terms, and use the Operator Agreement with every pilot partner.
5. (Optional, I can build it) wire a **consent capture + Information-Officer contact** into the intake form, and a **retention/auto-delete** job, so the technical posture matches the documents.

*Prepared [date]. Drafts only — not legal advice.*
