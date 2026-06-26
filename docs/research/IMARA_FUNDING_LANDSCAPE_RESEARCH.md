# Imara — SA Funding Landscape Research Cycle (2026-06-21)
*A research cycle to find Imara's genuine next step. It redirected the prior priority: the open-banking ingestion adapter is NOT the right next build. The confirmed whitespace is an evidence-grounded, lender-agnostic readiness + which-path layer — and the buildable increment is a deterministic Funding-Fit recommender (built alongside this doc).*

## 1. What I researched
The SA open-banking ingestion path (Stitch, Mono), the SA SME-lending competitive landscape (Lula, Bridgement, Merchant Capital, marketplaces), and existing SME funding-readiness tools — plus owner/advisor sentiment on Reddit.

## 2. The priority redirect — why the open-banking adapter is NOT next
The last cycle recommended building an open-banking ingestion adapter. This cycle says: not yet, and here's why.

- **Stitch — SA's open-banking leader — pivoted from data-aggregation to payments.** Account-data linking is now a secondary feature, not a product they push. There is no strong SA-SME *data-aggregation* API to build Imara's ingestion on. ([Stitch — Wikipedia](https://en.wikipedia.org/wiki/Stitch_Money))
- **Mono** (the other option) was just **acquired by Flutterwave** and is Nigeria-focused. ([TechCrunch](https://techcrunch.com/2026/01/05/flutterwave-buys-nigerias-mono-in-rare-african-fintech-exit/))
- **Bank-feed / accounting-integration underwriting is already owned by the lenders.** Bridgement is "the only SA lender fully integrated with Xero/Sage/QuickBooks" + bank feeds, with ~5-hour average approvals (63-min record). Lula decides in 24h on AI + alternative data. So an adapter would be *harder* than assumed AND *non-differentiating* — table-stakes the alt-lenders already have. ([Bridgement](https://www.dailymaverick.co.za/article/2025-12-18-bridgement-puts-business-loans-on-standby-fast-flexible-feefree-funding/), [Lula](https://launchbaseafrica.com/2026/02/04/south-africas-lula-bags-21m-to-double-down-on-sme-lending/))

**Conclusion:** revisit open-banking ingestion only if a specific channel partner requires it. It is neither a foundation that exists nor a differentiator.

## 3. The confirmed whitespace
Three incumbent categories exist in SA — and none do what Imara does:

1. **Loan marketplaces** (FundingHub: 30+ lenders, one 5-min application; LoansFind) — they *match and compare offers*, but never tell you *where you stand* or *how to become fundable*. ([FundingHub](https://www.fundinghub.co.za/))
2. **Alt-lenders** (Lula, Bridgement, Merchant Capital) — fast, but only answer "can you get *our* product," and mostly for short-term working capital.
3. **Funding-readiness tools** (Edge Growth, SME Snapshot, Global Compact SA, MTN SME Hub) — and the key finding: **they're subjective self-assessment questionnaires/checklists.** Edge Growth's is literally a PDF form; SME Snapshot is a 5-area qualitative checklist. ([Edge Growth](https://edgegrowth.com/edge-growth-funding-readiness-tool/), [SME Snapshot](https://disruptafrica.com/2025/10/30/sas-sme-snapshot-launches-enhanced-platform-to-help-smes-access-funding-grow/))

**Nobody computes an evidence-grounded, lender-grade readiness verdict from the firm's *actual* financials and bank statements.** That is exactly Imara (deterministic ratios, Altman Z″, bank-conduct signals, reason codes, the Bank-Ready Pack). The differentiation: *computed, not self-reported; lender-agnostic, not product-specific; full-picture, not a single short-term-advance yes/no.*

Reddit confirms the demand and the confusion: owners are lost in the funnel ("how do I get funding", "I've fallen for scams"), can't evaluate offers ("prime + 10.75% over 60 months — are they drilling me?"), and the accountant/advisor/deal-maker intermediary role is real.

## 4. The standardised SA eligibility floors (used by the recommender)
Commercial lenders broadly require: **≥12 months trading**, **>R1m annual turnover**, **CIPC-registered**. Below these, the realistic path is development funding (SEFA/IDC/NEF) or "fix-first."

## 5. The buildable next step — Funding-Fit / Which-Path recommender
Imara already answers *where do I stand* (Score) → *why* (reason codes / lender-view) → *what to fix* (Bank-Ready Pack). The missing piece is **which path fits me.** `services/funding_fit.py` (built alongside this doc) deterministically maps the firm's profile — turnover, trading months, CIPC status, cash-flow conduct, adjusted EBITDA, receivables, sector — to the right funding **archetype**, each with a fit level, the reasons, what's still needed, and the caveat:

- Revenue-based / turnover advance · Unsecured working-capital facility · Invoice discounting / debtor finance · Bank term loan · Asset / equipment finance · Development / government funding (SEFA/IDC/NEF) · plus a **"strengthen-first" gate** when the floors aren't met or bank conduct is weak.

Framed as **objective information about funding TYPES** (FAIS s1(3)(a) — not a recommendation that any specific product/provider is suitable; not a credit decision; not an Imara Score input). It completes Imara's arc and differentiates it from marketplaces (which only match), lenders (which only sell their own product), and questionnaire tools (which are self-reported).

## 6. Honest caveats
Distribution remains the real bottleneck (the accountant/advisor channel + the design-partner pilot — Ruan-led). This recommender is the product piece that makes that channel pitch land; it is not, by itself, distribution. Funding-archetype fit is indicative and dated; eligibility floors are market-typical, not lender-specific.
