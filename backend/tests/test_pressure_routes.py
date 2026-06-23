"""Route-table pressure regression (v1.72): every report endpoint must survive an
edge (all-zero) report AND an all-NaN / wrong-typed report with NO 500 and valid JSON.
Locks the deterministic-service hardening so the NaN/wrong-type crash class can't return."""
import os
import tempfile

os.environ.setdefault("BF_DB_PATH", os.path.join(tempfile.gettempdir(), "bf_pressure.db"))
os.environ.setdefault("MOCK_MODE", "true")

from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402

_EDGE = {"analysis_id": "edge_t", "financial_figures": {"revenue": 0, "cogs": 0, "equity": 0},
         "imara_components": []}
_NAN = {"analysis_id": "nan_t", "annual_revenue": float("nan"), "headcount": float("nan"),
        "financial_figures": {"revenue": float("nan"), "cogs": float("inf"),
                              "equity": float("nan"), "total_assets": float("nan")},
        "normalization": {"loan_account_flag": {"flagged": True}, "add_backs": [float("inf")]},
        "lender_view": {"decline_risk": float("nan")}, "imara_components": "bad",
        "imara_score": float("nan"), "financial_fundamentals_score": float("nan")}


def _get_routes():
    return [r.path for r in main.app.routes
            if getattr(r, "methods", None) and "GET" in r.methods and "{analysis_id}" in r.path]


def test_all_report_routes_survive_edge_and_nan_reports():
    main.analyses["edge_t"] = _EDGE
    main.analyses["nan_t"] = _NAN
    routes = _get_routes()
    assert len(routes) >= 20  # sanity: we really are sweeping the table
    failures = []
    with TestClient(main.app) as c:
        for aid in ("edge_t", "nan_t"):
            for path in routes:
                resp = c.get(path.replace("{analysis_id}", aid))
                if resp.status_code >= 500:
                    failures.append((path, aid, resp.status_code))
                if "application/json" in resp.headers.get("content-type", ""):
                    resp.json()  # raises if invalid JSON (e.g. NaN leaked)
    assert not failures, "5xx on: " + repr(failures)


def test_simulation_post_endpoints_survive_nan_report():
    main.analyses["nan_t"] = _NAN
    main.analyses["edge_t"] = _EDGE
    bad = []
    with TestClient(main.app) as c:
        for ep, body in [
            ("/api/simulate/montecarlo", {"analysis_id": "nan_t"}),
            ("/api/simulate/montecarlo", {"analysis_id": "nan_t", "actions": ["junk", 123]}),
            ("/api/simulate/actions", {"analysis_id": "nan_t", "actions": [{"id": "x", "intensity": 1}]}),
            ("/api/simulate/actions", {"analysis_id": "edge_t", "actions": ["junk"]}),
        ]:
            r = c.post(ep, json=body)
            if r.status_code >= 500:
                bad.append((ep, r.status_code))
    assert not bad, "5xx on: " + repr(bad)
