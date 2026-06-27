"""
sars_guidance.py - deterministic SARS-process guidance reference.

Pure data + getters; the LLM narrates/selects, it never invents the facts. These
are the SARS interactions an SME actually faces - verification, audit, the
Voluntary Disclosure Programme, record-keeping, and the two debt-relief levers -
each as a structured card: what it is, the statutory response deadline, concrete
do's and don'ts, and the citation. Pairs with services/sars_dispute.py (the
objection/appeal clock) and services/tcs_status.py (the compliance pillars).

Decision-support / awareness, not legal advice. Re-verify the response periods
and the VDP scope against the current TAA + SARS guides each year.
"""

# Each card: key, title, situation, what_it_is, deadline, do[], dont[], citation.
_GUIDANCE = (
    {
        "key": "verification",
        "title": "SARS verification",
        "situation": "SARS asks you to support figures on a return (a request for relevant material).",
        "what_it_is": ("A desk check that the amounts you declared are supported. Narrower than an "
                       "audit - usually one return / a few line items."),
        "deadline": "Submit the requested material by the date on the letter - typically 21 business days.",
        "do": [
            "Upload exactly what was asked via eFiling, clearly labelled, within the period.",
            "Reconcile the documents to the declared figures before you send them.",
            "Ask for an extension in writing before the deadline if you genuinely need more time.",
        ],
        "dont": [
            "Ignore it - non-response leads to a revised (usually higher) assessment.",
            "Send a disorganised dump - it invites a full audit.",
        ],
        "citation": "Tax Administration Act 28/2011 s46 (request for relevant material).",
    },
    {
        "key": "audit",
        "title": "SARS audit",
        "situation": "SARS notifies you it is auditing your tax affairs.",
        "what_it_is": ("A deeper examination across returns/periods. SARS must give you the scope, keep "
                       "you updated, and issue a findings letter BEFORE assessing."),
        "deadline": "Respond to the audit findings letter within 21 business days before SARS finalises the assessment.",
        "do": [
            "Respond to the findings letter point by point with evidence - this is your chance before assessment.",
            "Keep a single organised record of every document and every SARS communication.",
            "Bring in a tax practitioner early where amounts are material.",
        ],
        "dont": [
            "Volunteer material outside the audit scope unprompted.",
            "Miss the findings-letter window - after assessment you are into the formal dispute route (objection).",
        ],
        "citation": "Tax Administration Act 28/2011 s40-42 (audit) + s96 (assessment).",
    },
    {
        "key": "vdp",
        "title": "Voluntary Disclosure Programme (VDP)",
        "situation": "You discover an error/omission in a past return BEFORE SARS notifies an audit.",
        "what_it_is": ("A formal route to regularise a default. A valid VDP remits the understatement "
                       "penalty (up to 100%) and avoids criminal prosecution - you still pay the tax and "
                       "interest."),
        "deadline": "Apply via eFiling BEFORE any audit/verification notification - voluntariness is the core requirement.",
        "do": [
            "Apply before SARS contacts you - that is what makes it 'voluntary'.",
            "Make a full and complete disclosure of the default.",
            "Use it to cap penalty exposure on a known historical mistake.",
        ],
        "dont": [
            "Apply after SARS has already notified an audit/verification of that issue - it is then invalid.",
            "Make a partial disclosure - it voids the relief.",
        ],
        "citation": "Tax Administration Act 28/2011 s225-233 (VDP).",
    },
    {
        "key": "record_keeping",
        "title": "Record-keeping",
        "situation": "How long, and in what form, you must keep tax records.",
        "what_it_is": "The statutory retention rules that underpin every verification, audit and objection.",
        "deadline": ("Keep records for 5 years from the date the return was submitted; longer if an audit, "
                     "objection or appeal is in progress (until it concludes), and indefinitely where no "
                     "return was submitted."),
        "do": [
            "Retain records in an acceptable form (original or a reliable electronic copy) and accessible.",
            "Keep the full 5 years even for periods you think are 'closed'.",
            "Extend retention while any dispute on that period is open.",
        ],
        "dont": [
            "Discard records at 5 years if a dispute or audit is still running.",
            "Rely on a third party (e.g. a former bookkeeper) to hold your only copy.",
        ],
        "citation": "Tax Administration Act 28/2011 s29-32 (record retention).",
    },
    {
        "key": "suspension_of_payment",
        "title": "Suspension of payment ('pay now, argue later')",
        "situation": "You are disputing an assessment but SARS still expects payment.",
        "what_it_is": ("Lodging an objection does NOT automatically suspend the debt (s164). You can request "
                       "a suspension of payment while the dispute runs; SARS decides on stated factors."),
        "deadline": "Request the suspension as soon as you dispute - ideally with the objection - to pause collection.",
        "do": [
            "Submit a written suspension request setting out the dispute and your compliance history.",
            "Keep other taxes fully compliant - it strengthens the request.",
        ],
        "dont": [
            "Assume the objection itself stops collection - it does not; SARS can collect until suspension is granted.",
        ],
        "citation": "Tax Administration Act 28/2011 s164 (payment pending objection/appeal).",
    },
    {
        "key": "payment_arrangement",
        "title": "Deferral / payment arrangement",
        "situation": "You owe tax you cannot settle in a single payment.",
        "what_it_is": ("A formal instalment payment agreement for an outstanding tax debt - keeps you in good "
                       "standing and protects the TCS debt pillar while you pay it down."),
        "deadline": "Arrange before the debt goes to collection; engage SARS early.",
        "do": [
            "Propose a realistic instalment plan backed by cash-flow evidence.",
            "Honour every instalment - default can cancel the arrangement and revive full collection.",
            "Use it to keep the TCS 'debt' pillar from blocking tenders/finance.",
        ],
        "dont": [
            "Let the debt sit unaddressed - interest (s89) and collection steps accrue.",
        ],
        "citation": "Tax Administration Act 28/2011 s167-168 (instalment payment agreement).",
    },
    {
        "key": "dta",
        "title": "Double-tax agreement (DTA) relief",
        "situation": "The same income is taxable in SA and another country.",
        "what_it_is": ("A treaty between SA and another country that decides which one taxes the income and "
                       "gives relief (exemption or a foreign-tax credit) so it is not taxed twice. A DTA "
                       "'tie-breaker' can also settle dual residency."),
        "deadline": "Claim the relief in the relevant year's return; keep proof of foreign tax paid.",
        "do": [
            "Check whether a DTA exists with the other country before assuming double tax.",
            "Keep evidence of foreign tax paid to support a s6quat foreign-tax credit.",
            "Use the tie-breaker test where two countries both claim you as resident.",
        ],
        "dont": [
            "Assume a DTA overrides SA's s9H exit charge - it generally does not.",
            "Claim a credit without documentary proof of the foreign tax.",
        ],
        "citation": "Income Tax Act 58/1962 s6quat (foreign-tax credit) + the relevant bilateral DTA.",
    },
    {
        "key": "cfc",
        "title": "Controlled foreign company (CFC)",
        "situation": "SA residents hold more than 50% of a foreign company.",
        "what_it_is": ("Anti-deferral rules that can attribute a CFC's net income to its SA shareholders and "
                       "tax it in SA even if no dividend is paid - unless an exemption (e.g. the foreign "
                       "business establishment exemption) applies."),
        "deadline": "Disclose CFC interests in the annual return for each year of assessment.",
        "do": [
            "Identify any foreign company that is more than 50% SA-held.",
            "Test whether the foreign-business-establishment (genuine substance) exemption applies.",
            "Disclose the CFC and its imputed income correctly.",
        ],
        "dont": [
            "Assume offshore profits are untaxed in SA until distributed - the CFC rules can impute them now.",
        ],
        "citation": "Income Tax Act 58/1962 s9D (controlled foreign company).",
    },
    {
        "key": "crs",
        "title": "Automatic exchange of information (CRS)",
        "situation": "You hold foreign bank/investment accounts.",
        "what_it_is": ("Under the OECD Common Reporting Standard, foreign financial institutions report SA "
                       "residents' account balances and income to SARS automatically. SARS already sees most "
                       "offshore accounts - non-disclosure is high-risk."),
        "deadline": "Declare all foreign accounts and income every year; regularise past omissions via VDP.",
        "do": [
            "Declare all foreign accounts, interest, dividends and gains in your SA return.",
            "Use the VDP to regularise any historical non-disclosure before SARS acts.",
        ],
        "dont": [
            "Assume an offshore account is invisible to SARS - CRS data flows automatically.",
        ],
        "citation": "OECD Common Reporting Standard (CRS); Tax Administration Act reporting rules.",
    },
)


def sars_process_guidance(topic=None) -> dict:
    """Return SARS-process guidance cards. If `topic` matches a card key, return
    just that one; otherwise return all. Pure / deterministic."""
    if topic:
        t = str(topic).strip().lower()
        card = next((c for c in _GUIDANCE if c["key"] == t), None)
        if card is None:
            return {"available": False, "reason": "Unknown topic.",
                    "topics": [c["key"] for c in _GUIDANCE]}
        return {"available": True, "as_of": "SA 2026 (TAA 28/2011)", "card": card,
                "disclaimer": "Decision-support / awareness, not legal advice; confirm with a tax practitioner."}
    return {
        "available": True,
        "as_of": "SA 2026 (TAA 28/2011)",
        "cards": list(_GUIDANCE),
        "count": len(_GUIDANCE),
        "note": ("How to handle the SARS interactions an SME actually faces - response deadlines and "
                 "do's/don'ts, each cited to the Tax Administration Act. Pairs with the dispute-deadline "
                 "calculator and the TCS readiness check."),
        "disclaimer": "Decision-support / awareness, not legal advice; confirm with a tax practitioner.",
    }
