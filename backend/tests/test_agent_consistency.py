"""Tests for the deterministic cross-agent consistency / corroboration detector."""
from services.agent_consistency import analyze_consistency, consistency_block

_FINDINGS = [
    {"agent": "Financial Forensics Agent", "category": "Concentration", "severity": "high",
     "title": "Customer concentration risk", "detail": "Top customer is 45% of revenue."},
    {"agent": "Sales Agent", "category": "Risk", "severity": "critical",
     "title": "Revenue concentration", "detail": "Single customer dependency threatens revenue."},
    {"agent": "Strategy Agent", "category": "Risk", "severity": "medium",
     "title": "Key client dependency", "detail": "Customer concentration limits valuation."},
    {"agent": "Auditor Agent", "category": "Controls", "severity": "low",
     "title": "Minor segregation of duties gap", "detail": "One approver; low fraud risk."},
    {"agent": "Fraud & Anomaly Detection Agent", "category": "Fraud", "severity": "critical",
     "title": "Segregation of duties failure", "detail": "Same person authorises and pays."},
    {"agent": "SA Tax Compliance Agent", "category": "Tax", "severity": "high",
     "title": "VAT registration overdue", "detail": "Turnover exceeds threshold."},
]


def test_corroboration_requires_two_distinct_agents():
    r = analyze_consistency(_FINDINGS)
    topics = {c["topic"]: c for c in r["corroborated"]}
    assert "Revenue / customer concentration" in topics
    assert topics["Revenue / customer concentration"]["agent_count"] == 3
    assert topics["Revenue / customer concentration"]["severity"] == "critical"   # max severity wins
    # the lone VAT finding (one agent) is NOT corroborated
    assert all("Tax" not in t for t in topics)


def test_same_agent_twice_does_not_corroborate():
    dup = [
        {"agent": "Financial Forensics Agent", "severity": "high", "title": "High debtor days", "detail": "working capital"},
        {"agent": "Financial Forensics Agent", "severity": "high", "title": "Cash flow strain", "detail": "liquidity"},
    ]
    assert analyze_consistency(dup)["available"] is False    # only one distinct agent


def test_severity_divergence_flagged():
    r = analyze_consistency(_FINDINGS)
    div = [d["topic"] for d in r["diverging"]]
    assert "Fraud / internal controls" in div                # low (Auditor) vs critical (Fraud)


def test_sorting_by_agent_count():
    r = analyze_consistency(_FINDINGS)
    counts = [c["agent_count"] for c in r["corroborated"]]
    assert counts == sorted(counts, reverse=True)


def test_robust_to_junk():
    assert analyze_consistency([None, "x", 5, {}, {"title": None, "severity": 1, "agent": None}])["available"] is False
    assert analyze_consistency(None)["available"] is False


def test_consistency_block_text():
    b = consistency_block(_FINDINGS)
    assert "CROSS-AGENT CORROBORATION" in b
    assert "Revenue / customer concentration" in b
    assert "3 agents" in b
