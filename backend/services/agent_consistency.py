"""
agent_consistency.py - deterministic cross-agent consistency / corroboration.

When several independent specialist agents flag the SAME underlying issue, that
issue is more credible - a real confidence signal a credit committee values
("three specialists independently flagged customer concentration"). Conversely,
when agents rate the same topic at very different severities, that divergence is
worth surfacing for reconciliation.

This is the deterministic counterpart to an LLM "critic pass": it needs no extra
model call and cannot hallucinate. It only reads the findings the agents already
produced. Nothing here changes the Imara Score.
"""

# (topic label, keyword triggers). A finding maps to a topic if any keyword appears
# in its title + category + detail (lower-cased).
TOPIC_RULES = [
    ("Revenue / customer concentration",
     ["concentrat", "single customer", "top customer", "customer dependen", "key client", "key-person"]),
    ("Margins / profitability",
     ["gross margin", "margin compress", "profitab", "ebitda", "loss-making", "loss making",
      "operating margin", "net margin", "pricing inadequa"]),
    ("Cash flow / working capital",
     ["cash flow", "working capital", "liquidity", "debtor day", "receivable", "current ratio",
      "cash conversion", "creditor day", "cash trapped"]),
    ("Leverage / debt service",
     ["gearing", "leverage", "debt-to-equity", "debt to equity", "dscr", "debt service",
      "interest cover", "solvency", "overdraft", "over-indebt"]),
    ("Tax compliance",
     ["vat", "sars", "paye", "provisional tax", "emp201", "tax clearance", "income tax", "irp6", "sdl"]),
    ("Legal / governance",
     ["companies act", "cipc", "popia", "bbbee", "b-bbee", "annual return", "director", " moi",
      "governance", "shareholder agreement", "public interest score"]),
    ("Fraud / internal controls",
     ["fraud", "segregation of duties", "duplicate payment", "benford", "ghost", "anomaly",
      "internal control", "approval bypass", "related party", "related-party"]),
    ("Inventory / procurement",
     ["inventory", "stock holding", "supplier concentration", "procurement", "overpay",
      "payables", "purchase price", "maverick spend"]),
    ("Workforce / HR",
     ["turnover", "absentee", "overtime", "labour cost", "payroll", "headcount",
      "staff productivity", "revenue per employee"]),
    ("Pricing / sales",
     ["discount", "win rate", "deal size", "pipeline", "upsell", "cross-sell", "sales productivity"]),
]

_SEVRANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _topics_for(text):
    t = (text or "").lower()
    return [name for name, kws in TOPIC_RULES if any(k in t for k in kws)]


def analyze_consistency(findings):
    findings = [f for f in (findings or []) if isinstance(f, dict)]
    by_topic = {}
    for f in findings:
        text = " ".join(str(f.get(k, "")) for k in ("title", "category", "detail"))
        agent = str(f.get("agent") or "Unknown").strip() or "Unknown"
        sev = str(f.get("severity") or "").lower()
        for topic in _topics_for(text):
            e = by_topic.setdefault(topic, {"agents": [], "severities": [], "titles": []})
            if agent not in e["agents"]:
                e["agents"].append(agent)
            e["severities"].append(sev)
            if f.get("title"):
                e["titles"].append(str(f["title"]))

    corroborated, diverging = [], []
    for topic, e in by_topic.items():
        if len(e["agents"]) < 2:
            continue
        ranks = [_SEVRANK.get(s, 0) for s in e["severities"] if s]
        top_sev = max(e["severities"], key=lambda s: _SEVRANK.get(s, 0)) if e["severities"] else ""
        corroborated.append({
            "topic": topic,
            "agents": e["agents"],
            "agent_count": len(e["agents"]),
            "severity": top_sev,
            "finding_count": len(e["severities"]),
            "titles": e["titles"][:4],
        })
        if ranks and max(ranks) >= 3 and min(ranks) <= 1:
            diverging.append({
                "topic": topic,
                "agents": e["agents"],
                "highest": [k for k, v in _SEVRANK.items() if v == max(ranks)][0],
                "lowest": [k for k, v in _SEVRANK.items() if v == min(ranks)][0],
            })

    corroborated.sort(key=lambda c: (-c["agent_count"], -_SEVRANK.get(c["severity"], 0)))

    if corroborated:
        summary = "{} issue area{} independently flagged by 2+ specialist agents (corroborated)".format(
            len(corroborated), "" if len(corroborated) == 1 else "s")
        if diverging:
            summary += "; {} show a severity divergence to reconcile".format(len(diverging))
        summary += "."
    else:
        summary = "No issue area was independently flagged by two or more agents."

    return {
        "available": bool(corroborated),
        "corroborated": corroborated,
        "diverging": diverging,
        "topics_touched": len(by_topic),
        "summary": summary,
    }


def consistency_block(findings):
    """Compact text block for the CEO synthesis to weave corroboration into the narrative."""
    res = analyze_consistency(findings)
    if not res["available"]:
        return ""
    lines = ["CROSS-AGENT CORROBORATION (deterministic; use to weight confidence - issues flagged by "
             "MULTIPLE independent agents are the most credible; do not invent corroboration beyond this list):"]
    for c in res["corroborated"][:6]:
        lines.append("- {} - flagged by {} agents ({}); top severity {}".format(
            c["topic"], c["agent_count"], ", ".join(c["agents"][:4]), c["severity"] or "n/a"))
    for d in res["diverging"][:3]:
        lines.append("- DIVERGENCE on {}: agents range from {} to {} - reconcile.".format(
            d["topic"], d["lowest"], d["highest"]))
    return "\n".join(lines)
