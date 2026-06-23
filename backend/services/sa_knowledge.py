"""
SA Compliance Knowledge Base + deterministic retriever (RAG grounding).

A curated, citation-tagged corpus of the key South African tax & company-law
provisions Imara's SA agents reason about. Grounding the agents in authoritative,
dated text (which they must cite) cuts hallucination and yields real citations
(Act number + section) instead of parametric recall — the highest-leverage
accuracy/trust lever for the most legally-sensitive part of the product.

Retrieval is deterministic keyword-relevance (no embeddings dependency, fully
testable). Each entry carries an `as_of` date so the corpus can be maintained as
law changes. Embeddings / sqlite-vec are a later upgrade if the corpus grows.
"""
import re

# Each: id, domain, topic, keywords, text (authoritative statement), citation, as_of
KNOWLEDGE_BASE = [
    # ── Tax ────────────────────────────────────────────────────────────────
    {"id": "vat_threshold", "domain": "tax", "topic": "VAT registration",
     "keywords": ["vat", "registration", "turnover", "threshold", "supplies", "vendor"],
     "text": "VAT registration is COMPULSORY once taxable supplies exceed R1,000,000 in any consecutive 12-month period; voluntary registration is allowed from R50,000.",
     "citation": "VAT Act 89 of 1991, s23", "as_of": "2024"},
    {"id": "vat201", "domain": "tax", "topic": "VAT returns",
     "keywords": ["vat", "vat201", "return", "submission", "deadline", "penalty", "late"],
     "text": "VAT201 returns and payment are due by the 25th (or last business day for eFiling) of the month following the tax period; late submission attracts a 10% penalty plus interest.",
     "citation": "VAT Act 89 of 1991", "as_of": "2024"},
    {"id": "provisional_tax", "domain": "tax", "topic": "Provisional tax",
     "keywords": ["provisional", "irp6", "estimate", "80%", "underestimation", "penalty"],
     "text": "Provisional tax (IRP6): the 1st estimate is due 6 months into the year of assessment and the 2nd by year-end. For taxable income over R1m the 2nd estimate must be at least 80% of the actual liability (the '80% rule') or a 20% underestimation penalty applies.",
     "citation": "Income Tax Act 58 of 1962, Fourth Schedule", "as_of": "2024"},
    {"id": "sbc", "domain": "tax", "topic": "Small Business Corporation",
     "keywords": ["sbc", "small business corporation", "section 12e", "rate", "turnover", "cit"],
     "text": "Small Business Corporation (SBC) reduced corporate tax rates apply where gross income is under R20m, no more than 20% of receipts are investment/personal-service income, and shareholders hold no other companies.",
     "citation": "Income Tax Act 58 of 1962, s12E", "as_of": "2024"},
    {"id": "emp201", "domain": "tax", "topic": "Payroll taxes",
     "keywords": ["paye", "emp201", "emp501", "sdl", "uif", "payroll", "eti", "employees"],
     "text": "EMP201 (PAYE/SDL/UIF) is due monthly by the 7th, with an EMP501 reconciliation twice a year. SDL is 1% of payroll (exempt if annual payroll is under R500,000); UIF is 2% (1% employer + 1% employee). The Employment Tax Incentive (ETI) applies to qualifying employees aged 18-29 earning under R6,500/month.",
     "citation": "Income Tax Act 58 of 1962 Fourth Schedule; SDL Act 9 of 1999; UIF Contributions Act 4 of 2002", "as_of": "2024"},
    {"id": "it14", "domain": "tax", "topic": "Corporate income tax return",
     "keywords": ["it14", "itr14", "income tax", "return", "company", "annual"],
     "text": "The corporate income tax return (ITR14) must be filed within 12 months of the company's financial year-end.",
     "citation": "Income Tax Act 58 of 1962", "as_of": "2024"},
    {"id": "tax_clearance", "domain": "tax", "topic": "Tax clearance / TCS",
     "keywords": ["tax clearance", "tcc", "tcs", "tender", "good standing", "government", "compliance status"],
     "text": "A valid Tax Compliance Status (TCS) PIN — formerly the Tax Clearance Certificate — is mandatory to bid on government tenders and many large contracts.",
     "citation": "Tax Administration Act 28 of 2011", "as_of": "2024"},
    {"id": "sars_debt", "domain": "tax", "topic": "SARS debt & interest",
     "keywords": ["sars", "debt", "interest", "outstanding", "penalty", "arrangement"],
     "text": "Interest accrues on outstanding SARS debt at the prescribed rate; payment arrangements and suspension of debt may be requested. Outstanding returns block a clean compliance status.",
     "citation": "Tax Administration Act 28 of 2011", "as_of": "2024"},

    # ── Corporate law / compliance ─────────────────────────────────────────
    {"id": "cipc_annual_return", "domain": "legal", "topic": "CIPC annual return",
     "keywords": ["cipc", "annual return", "cor30.1", "deregistration", "filing", "company"],
     "text": "Every company must file an annual return with CIPC within 30 business days after the anniversary of its incorporation; persistent failure leads to deregistration.",
     "citation": "Companies Act 71 of 2008, s33", "as_of": "2024"},
    {"id": "director_duties", "domain": "legal", "topic": "Director duties & liability",
     "keywords": ["director", "duties", "fiduciary", "liability", "good faith", "care", "section 76"],
     "text": "Directors owe statutory duties — good faith, proper purpose, and the degree of care, skill and diligence of a reasonably diligent person — and can be held personally liable for breach.",
     "citation": "Companies Act 71 of 2008, s76 and s77", "as_of": "2024"},
    {"id": "moi", "domain": "legal", "topic": "Memorandum of Incorporation",
     "keywords": ["moi", "memorandum", "incorporation", "constitution", "shareholder"],
     "text": "Every company must have a Memorandum of Incorporation (MOI); where the MOI is silent, the default rules in the Companies Act and Regulations apply.",
     "citation": "Companies Act 71 of 2008, s15", "as_of": "2024"},
    {"id": "pis_audit", "domain": "legal", "topic": "Audit / Public Interest Score",
     "keywords": ["audit", "public interest score", "pis", "financial statements", "review", "afs"],
     "text": "A company's Public Interest Score (PIS) determines whether its annual financial statements must be audited or independently reviewed and the applicable financial-reporting standard.",
     "citation": "Companies Act 71 of 2008; Companies Regulations 26 and 28", "as_of": "2024"},
    {"id": "beneficial_ownership", "domain": "legal", "topic": "Beneficial ownership register",
     "keywords": ["beneficial ownership", "register", "cipc", "disclosure", "transparency"],
     "text": "Companies must file and maintain a beneficial ownership register with CIPC; non-filing is a compliance breach and blocks certain CIPC transactions.",
     "citation": "Companies Act 71 of 2008 as amended by the General Laws (Anti-Money Laundering) Amendment Act 22 of 2022", "as_of": "2024"},
    {"id": "bbbee", "domain": "legal", "topic": "BBBEE level & thresholds",
     "keywords": ["bbbee", "b-bbee", "level", "eme", "qse", "black ownership", "exempt micro"],
     "text": "An Exempt Micro Enterprise (EME) has annual turnover under R10m and is automatically Level 4 (Level 2 if 51%+ black-owned, Level 1 if 100%). A Qualifying Small Enterprise (QSE) is R10m-R50m; above R50m is a Generic enterprise with a full scorecard.",
     "citation": "B-BBEE Act 53 of 2003 and the Codes of Good Practice", "as_of": "2024"},
    {"id": "popia", "domain": "legal", "topic": "POPIA data protection",
     "keywords": ["popia", "data", "privacy", "information officer", "personal information", "breach"],
     "text": "POPIA requires lawful processing under 8 conditions, the appointment of an Information Officer registered with the Information Regulator, and notification of data breaches.",
     "citation": "Protection of Personal Information Act 4 of 2013", "as_of": "2024"},
    {"id": "labour", "domain": "legal", "topic": "Labour law (LRA/BCEA)",
     "keywords": ["labour", "employment", "contract", "dismissal", "ccma", "lra", "bcea", "staff"],
     "text": "Employees must have written particulars of employment; unfair dismissal and unfair labour practices fall under the LRA with CCMA jurisdiction, and the BCEA sets minimum conditions of employment.",
     "citation": "Labour Relations Act 66 of 1995; Basic Conditions of Employment Act 75 of 1997", "as_of": "2024"},
    {"id": "cpa_nca", "domain": "legal", "topic": "Consumer & credit law",
     "keywords": ["cpa", "consumer", "nca", "credit", "agreement", "registration"],
     "text": "The Consumer Protection Act governs consumer transactions; the National Credit Act requires credit providers to register and regulates credit agreements.",
     "citation": "Consumer Protection Act 68 of 2008; National Credit Act 34 of 2005", "as_of": "2024"},
]

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text):
    return set(_WORD.findall((text or "").lower()))


def retrieve(query: str, domain: str | None = None, k: int = 8) -> list:
    """Deterministic keyword-relevance retrieval over the curated corpus."""
    q = _tokens(query)
    scored = []
    for e in KNOWLEDGE_BASE:
        if domain and e["domain"] != domain:
            continue
        kw = set(w.lower() for w in e["keywords"])
        text_tokens = _tokens(e["text"] + " " + e["topic"])
        score = 2 * len(q & kw) + len(q & text_tokens)
        scored.append((score, e))
    # Stable: by score desc, then corpus order (id) for determinism.
    scored.sort(key=lambda x: (-x[0], KNOWLEDGE_BASE.index(x[1])))
    return [e for score, e in scored[:k]]


def _profile_query(memory, domain: str) -> str:
    """Build a relevance query from the business profile + the review's scope."""
    parts = [
        getattr(memory, "industry", "") or getattr(memory, "industry_key", ""),
        getattr(memory, "entity_type", ""), getattr(memory, "primary_concern", ""),
        getattr(memory, "years_in_business", ""),
    ]
    if domain == "tax":
        parts += ["vat registration return provisional tax it14 emp201 paye sbc tax clearance sars"]
        if getattr(memory, "vat_registered", "") in ("yes", "pending"):
            parts.append("vat vendor")
        if getattr(memory, "headcount", 0):
            parts.append("paye emp201 payroll uif sdl eti employees")
    else:
        parts += ["cipc annual return director duties moi bbbee popia beneficial ownership audit labour"]
        if getattr(memory, "bbbee_level", ""):
            parts.append("bbbee level eme qse black ownership")
    return " ".join(p for p in parts if p)


def retrieve_grounding(memory, domain: str, k: int = 8) -> str:
    """Return an authoritative-provisions block to inject into an SA agent prompt."""
    hits = retrieve(_profile_query(memory, domain), domain=domain, k=k)
    if not hits:
        return ""
    lines = [
        "AUTHORITATIVE SA PROVISIONS (current as of 2025/26 — cite these by Act and section; "
        "do not state law that contradicts them, and flag where a provision may have changed):"
    ]
    for e in hits:
        lines.append("- {} [{}]".format(e["text"], e["citation"]))
    return "\n".join(lines)
