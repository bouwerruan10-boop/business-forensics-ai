"""Hardening regression: report-builder endpoints must survive hostile persisted
report data (non-dict, wrong types, inf/nan figures, malformed flag lists)
without crashing or emitting invalid JSON."""
import json
import pytest

from services.tcs_status import build_tcs_status
from services.audit_risk import build_audit_risk
from services.compliance_calendar import build_compliance_calendar
from services.ratio_diagnostics import build_diagnostics
from services.action_constraints import annotate

_BUILDERS = [build_tcs_status, build_audit_risk, build_compliance_calendar,
             build_diagnostics, annotate]

_HOSTILE = [
    None, "string", 123, [], {"__proto__": 1},
    {"annual_revenue": "1e400", "headcount": float("inf"), "vat_registered": {"x": 1}, "entity_type": ["pty"]},
    {"annual_revenue": float("nan"), "headcount": -5, "cipc_number": 9999, "tax_year_end": 12345},
    {"annual_revenue": "R 1,000,000 <script>", "entity_type": "Pty" * 10000},
    {"tax_risk_flags": {"available": True, "flags": "notalist"}},
    {"tax_risk_flags": {"available": True, "flags": [{"severity": None}, {}, "x"]}},
    {"financial_figures": {"revenue": float("inf")}},
]


@pytest.mark.parametrize("builder", _BUILDERS)
@pytest.mark.parametrize("report", _HOSTILE)
def test_report_builder_survives_hostile_input(builder, report):
    result = builder(report)
    assert isinstance(result, dict)
    json.dumps(result, allow_nan=False)   # never inf/nan -> always valid JSON


def test_infinite_headcount_does_not_overflow():
    # the original crash: int(_n(inf)) -> OverflowError
    assert build_tcs_status({"entity_type": "Pty Ltd", "headcount": float("inf")})["available"] is True
    assert build_compliance_calendar({"entity_type": "Pty Ltd", "headcount": float("inf")})["available"] in (True, False)


def test_audit_risk_ignores_non_dict_flags():
    # non-dict junk entries ("junk", None) are skipped; the one high flag counts
    r = build_audit_risk({"tax_risk_flags": {"available": True, "flags": [{"severity": "high"}, "junk", None]}})
    assert r["score"] == 28
