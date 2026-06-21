"""
Decision audit log — per-analysis, append-only, hash-chained record of HOW each
Imara Score was produced. This is the artifact regulated lenders and the 2026
governance wave (EU AI Act data-governance/technical-documentation; SA COFI
conduct) expect: what inputs -> what score -> which model + engine versions ->
when, tamper-evident via a SHA-256 hash chain.

Raw documents are NEVER stored — only their SHA-256 hashes (POPIA-friendly).
Deterministic; never fatal to an analysis.
"""
import hashlib
import json
import math
from datetime import datetime, timezone

from config import MODEL, PARSE_MODEL, MODEL_FALLBACKS, IMARA_ENGINE_VERSION
from services.score_contract import SCORE_SCHEMA_VERSION

__all__ = ["build_audit_record", "record_decision", "AUDIT_SCHEMA_VERSION"]

AUDIT_SCHEMA_VERSION = "1.0"
_INPUT_FIELDS = ("uploaded_financial_text", "uploaded_bank_text", "uploaded_tax_text",
                 "uploaded_legal_text", "uploaded_hr_text", "uploaded_plan_text")


def _h(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _finite(v):
    """Keep the record strict-JSON safe: drop non-finite numbers (NaN/inf); pass others through."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v if math.isfinite(v) else None
    return v


def build_audit_record(report: dict, inputs_text: str = "") -> dict:
    report = report or {}
    figs = report.get("financial_figures")
    figs = figs if isinstance(figs, dict) else {}
    findings = report.get("all_findings_ranked")
    return {
        "audit_schema_version": AUDIT_SCHEMA_VERSION,
        "score_schema_version": SCORE_SCHEMA_VERSION,
        "engine_version": IMARA_ENGINE_VERSION,
        "analysis_id": report.get("analysis_id"),
        "business_name": report.get("business_name"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "imara_score": _finite(report.get("imara_score")),
        "imara_band": report.get("imara_band"),
        "imara_confidence": report.get("imara_confidence"),
        "imara_completeness": _finite(report.get("imara_completeness")),
        "financial_extraction_source": report.get("financial_extraction_source"),
        "figures_hash": _h(json.dumps(figs, sort_keys=True, default=str)),
        "inputs_hash": _h(inputs_text),
        "finding_count": (len(findings) if isinstance(findings, list) else None),
        "models": {"model": MODEL, "parse_model": PARSE_MODEL, "fallbacks": list(MODEL_FALLBACKS)},
    }


def record_decision(report: dict, memory=None) -> dict:
    """Build + append the hash-chained audit record. Returns the stamp to surface on the report."""
    inputs_text = ""
    if memory is not None:
        inputs_text = "\n".join(str(getattr(memory, f, "") or "") for f in _INPUT_FIELDS)
    rec = build_audit_record(report, inputs_text)
    from services.database import append_audit
    stamp = append_audit(rec)
    return {
        "record_hash": stamp["record_hash"],
        "prev_hash": stamp.get("prev_hash"),
        "generated_at": rec["generated_at"],
        "engine_version": rec["engine_version"],
        "models": rec["models"],
        "figures_hash": rec["figures_hash"],
        "inputs_hash": rec["inputs_hash"],
    }
