"""
Stable, versioned Imara Score output contract — the surface a B2B lender consumes.

Kept separate and versioned (schema_version) so the public /api/v1/score endpoint has
one source of truth that can evolve via optional fields without breaking integrators.
"""
from datetime import datetime, timezone
from services.governance import decision_support_notice

SCORE_SCHEMA_VERSION = "1.0"


def score_contract(report: dict, analysis_id: str | None = None) -> dict:
    return {
        "schema_version": SCORE_SCHEMA_VERSION,
        "analysis_id": analysis_id or report.get("analysis_id"),
        "business_name": report.get("business_name"),
        "industry": report.get("industry"),
        "currency": report.get("currency"),
        "imara_score": report.get("imara_score"),
        "band": report.get("imara_band"),
        "label": report.get("imara_label"),
        "confidence": report.get("imara_confidence"),
        "completeness": report.get("imara_completeness"),
        "components": report.get("imara_components") or [],
        "use_constraints": decision_support_notice(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def usage_summary(report: dict) -> dict:
    """Per-analysis usage — billing-ready (metering) and useful for ops now."""
    timings = report.get("agent_timings") or []
    return {
        "agents_run": len(timings),
        "runtime_seconds": report.get("total_runtime_seconds"),
        "financial_extraction_source": report.get("financial_extraction_source"),
        "agent_timings": timings,
        "llm_usage": report.get("llm_usage"),
    }
