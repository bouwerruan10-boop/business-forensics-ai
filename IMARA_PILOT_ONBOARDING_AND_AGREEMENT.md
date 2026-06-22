# Imara — Design-Partner Pilot: Onboarding Checklist + Agreement Template

**Date:** 22 June 2026
**Use:** once a design partner (accountant firm or lender) says yes, this runs them from "signed" to "generating outcomes." Part A is the operational checklist; Part B is a plain-language agreement template.

> ⚠️ **Part B is a TEMPLATE, not legal advice.** Have a South African attorney review and finalise it before signing — especially the POPIA / data-protection and liability clauses. It processes real client financial data, so this matters.

---

## Part A — Onboarding checklist (per signed partner)

**Step 0 — Pre-reqs cleared (before any real client data flows)**
- [ ] At-rest encryption confirmed on the Railway data volume (POPIA).
- [ ] Information Officer registered with the Information Regulator.
- [ ] API/admin keys rotated; `OPERATOR_PASSWORD` set; frontend CSP live.
- [ ] Attorney sign-off on the POPIA pack + the cross-border (US AI) transfer + this agreement.

**Step 1 — Kickoff call (30 min)**
- [ ] Agree scope: cohort size, what "useful" means, weekly cadence.
- [ ] Agree **success metrics + a go/yellow/kill gate** (see `IMARA_PILOT_PROTOCOL.md`).
- [ ] Walk a live sample Imara report (use the accessible HTML report).

**Step 2 — Sign the agreement** (Part B, attorney-finalised).

**Step 3 — POPIA + access setup**
- [ ] Partner confirms its mechanism for **client consent + right to share** each SME's data.
- [ ] Imara intake consent checkbox + cross-border notice active; `REQUIRE_CONSENT` on.
- [ ] Partner operator credentials issued; share-link policy agreed (prefer revocable/expiring share tokens over the raw canonical URL).

**Step 4 — Select the pilot cohort**
- [ ] *Accountant:* pick 5–15 SME clients (mix of healthy + struggling).
- [ ] *Lender:* assemble a retrospective batch of recent applications — **include declines** — plus their decisions and (where available) repayment outcomes.

**Step 5 — Run + record**
- [ ] Run each through Imara; record which client maps to which analysis_id.
- [ ] Capture each client's baseline (so improvement is measurable).

**Step 6 — Weekly review cadence**
- [ ] Per report, capture **face-validity feedback**: is the verdict right? findings useful? would you act on / fund this? (This is the interim evidence while outcomes accrue.)

**Step 7 — Outcome capture (the whole point)**
- [ ] Log real outcomes as they happen into the `outcomes` table (funded/declined; later repaid/defaulted; or client improved/closed). Aim for ≥30–50 labelled outcomes over time.

**Step 8 — Mid-pilot gate (~week 6)**
- [ ] Review against the go/yellow/kill criteria; adjust or stop.

**Step 9 — Wrap (week 8–12)**
- [ ] Results readout (predictive lift vs the partner's baseline + willingness to pay/embed).
- [ ] Decide: continue / commercial terms / white-label — or stop and apply the learnings.
- [ ] On request or end-of-pilot: return or delete the partner's data per the agreement.

---

## Part B — Design-Partner Pilot Agreement (TEMPLATE — not legal advice)

**This Design-Partner Pilot Agreement** ("Agreement") is entered into on **[date]** between:
- **[Imara entity / Ruan trading name], registration [●]** ("Imara"); and
- **[Partner firm], registration [●]** ("Partner").

**1. Purpose.** A free, time-limited pilot in which the Partner uses the Imara platform to analyse a defined set of its clients' / applicants' business data, and provides feedback, so both parties can assess fit and Imara can validate its outputs against real-world outcomes.

**2. Term.** [8–12] weeks from the effective date. Either party may end this Agreement on **[7] days' written notice**, for any reason.

**3. Scope.**
- *Imara* provides: access to the platform, onboarding support, and the analysis reports; and will use reasonable measures to keep the Partner's and its clients' data secure.
- *Partner* provides: a defined cohort of client/applicant data it is **lawfully entitled to share**, and good-faith feedback (and, where available, outcome data).

**4. Fees.** **None.** The pilot is free. Neither party owes the other fees during the Term.

**5. Data protection (POPIA).**
- The Partner is the **responsible party** for its clients' personal information and warrants it has obtained the necessary **consent and right to share** that data for this pilot.
- Imara acts as an **operator** (POPIA s21) processing that data only to provide the analysis, under the Partner's authorisation.
- Imara applies reasonable technical safeguards (PII redaction before any AI step, encryption in transit, access controls, a tamper-evident audit log).
- **Cross-border processing:** the Partner acknowledges that document text is processed by an AI service located outside South Africa (currently the United States), after PII redaction, and consents on the basis disclosed to data subjects.
- On request or at the end of the Term, Imara will **return or delete** the Partner's data, save for de-identified/aggregated data per clause 7.
- Each party will notify the other without undue delay of any security compromise affecting the pilot data.

**6. Confidentiality.** Each party keeps the other's non-public information (including the pilot data, Imara's methods/outputs, and commercial terms) confidential, and uses it only for the pilot. Survives termination.

**7. Intellectual property & learnings.** Imara owns the platform and all software, models, and report formats. The Partner (and its clients) retain ownership of their underlying data. Imara may use **de-identified, aggregated** learnings and — with the Partner's permission — **labelled outcome data** to validate and improve the Imara Score and product.

**8. Feedback licence.** The Partner grants Imara a non-exclusive, royalty-free licence to use feedback it provides to improve the product.

**9. Decision-support; no advice; no warranty.** Imara is **decision-support only**. Its outputs are **indicative** and are **not** financial, credit, tax, or legal advice, **not** a credit decision under the National Credit Act, and **not** a substitute for the Partner's own professional judgment and sign-off. The platform is provided **"as is"** during the pilot, without warranties, and the Partner remains responsible for any decision it takes.

**10. Limitation of liability.** To the maximum extent permitted by law, neither party is liable for indirect or consequential loss; each party's aggregate liability under this Agreement is limited to **[ZAR ● / a nominal amount]**, reflecting that the pilot is provided free of charge. *(Attorney to set.)*

**11. Termination.** On termination, access ends and clause 5 (data return/deletion), 6 (confidentiality), 7 (IP), and 9 (no-advice) survive.

**12. Governing law.** The laws of the Republic of South Africa; the parties submit to the South African courts.

**Signed:**
Imara: __________________  Date: ________
Partner: ________________  Date: ________

---

*This is a plain-language template to accelerate the conversation with a design partner. It is NOT legal advice and is NOT ready to sign as-is — a South African attorney must review and finalise it (particularly clauses 5, 9, and 10) before use. Pairs with `IMARA_PILOT_PROTOCOL.md` (success metrics + go/kill gates) and the channel kits (accountant / lender).*
