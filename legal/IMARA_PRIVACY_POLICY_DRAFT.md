# Imara — Privacy Policy (DRAFT)

> **⚠ DRAFT — not legal advice.** This is a POPIA-grounded starting template prepared to save you drafting time. It **must be reviewed and finalised by a South African admitted attorney** before you publish or rely on it. Fill every `[bracketed]` placeholder. See `IMARA_COMPLIANCE_PACK_README.md` for the action list.

**Last updated:** [date] · **Applies to:** the Imara business-bankability analysis service ("Imara", "we", "us").

---

## 1. Who we are
Imara is operated by **[Registered entity name]** (registration no. **[CIPC reg no.]**), of **[registered address]** ("the Responsible Party").

**Information Officer (POPIA):** **[Ruan Bouwer]**, **[email]**, **[phone]**.
*(POPIA action: the Information Officer must be registered with the Information Regulator before processing begins — see the cover README.)*

## 2. Our two roles under POPIA
- **As Responsible Party** — for the personal information you give us *about yourself / your business contacts* (your account and contact details, usage data). This policy governs that processing.
- **As Operator** — when you upload business documents that contain other people's personal information (e.g. your employees, directors, or customers in financials, bank statements, HR or tax records), **we process that information on your behalf and on your instruction.** That processing is governed by our **Operator Agreement** (POPIA s21) — you remain the Responsible Party for it.

## 3. What we collect
- **Account & contact data:** your name, email, business name, entity type, and the profile details you enter.
- **Uploaded documents:** financials, bank statements, tax/legal/HR records and business plans you submit — which **may contain personal information of third parties**.
- **Technical/usage data:** request and analysis identifiers, timestamps, and operational logs.

## 4. Why we process it (purpose & lawful basis)
We process your information **solely to produce the bankability analysis you request** — performance of our agreement with you, and our legitimate interest in providing and improving the service. **We do not sell your data, and we do not use your data to train AI models.**

## 5. AI processing and cross-border transfer *(read this carefully)*
To generate the narrative parts of your report, Imara sends relevant document text to the **Anthropic Claude API**, which processes it on servers **outside South Africa (in the United States)**. This is a **cross-border transfer of personal information under POPIA section 72.**
- Before text is sent, Imara **automatically redacts** obvious personal identifiers it detects (e-mail addresses, South African ID numbers, card numbers).
- The **deterministic financial calculations and the Imara Score are computed locally** — the AI only narrates.
- **[⚠ Attorney to confirm the lawful basis for the s72 transfer]** — e.g. that Anthropic is bound by contractual terms providing an adequate level of protection, and/or that the transfer is necessary for performance of your contract, and/or your consent. State the chosen basis here once confirmed.

## 6. Who we share it with
- **Anthropic** (AI processing — see §5).
- **Hosting providers** (Railway, Vercel) that store and serve the service.
- **Market-research lookup** (e.g. Serper) — limited to your *business name/brand* for a public web scan; **never your client financials**.
- We do **not** sell or rent personal information.

## 7. How we secure it
HTTPS encryption in transit; deterministic input sanitisation and PII redaction before AI processing; a **hash-chained, tamper-evident audit log** of every analysis decision; operator authentication on the report surface; and request rate-limiting. **[Confirm at-rest encryption / backup security with your attorney + hosting setup.]**

## 8. How long we keep it
We keep personal information **only as long as necessary** to provide the analysis and meet legal obligations (POPIA s14). Records of any data breach are kept for **at least two years**. You may request deletion (see §9), subject to any law that requires retention.

## 9. Your rights as a data subject
You may **access, correct, or delete** your personal information, **object** to processing, and **lodge a complaint** with the Information Regulator. To exercise any right, contact our Information Officer (§1). We respond within the timeframes POPIA requires.

## 10. Data breaches
Where we have reasonable grounds to believe personal information has been accessed or acquired by an unauthorised person, we will notify the **Information Regulator** and the affected **data subjects as soon as reasonably possible** (POPIA has **no materiality threshold**). Where we act as Operator, we will notify you (the Responsible Party) immediately.

## 11. Contact
**Information Officer:** [name] · [email] · [phone].
**Information Regulator (South Africa):** Email enquiries@inforegulator.org.za · complaints POPIAComplaints@inforegulator.org.za · [verify current contact details].

---
*DRAFT prepared [date]. Not legal advice. Have an SA attorney review before use.*
