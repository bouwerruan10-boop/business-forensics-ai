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


def test_db_persistence_status_classifies_tiers(monkeypatch, tmp_path):
    import importlib, services.database as d
    # explicit override
    monkeypatch.setenv("BF_DB_PATH", str(tmp_path / "x.db"))
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)
    importlib.reload(d)
    s = d.db_persistence_status()
    assert s["tier"] == "BF_DB_PATH override" and s["persistent_across_redeploys"] is True
    # railway volume
    monkeypatch.delenv("BF_DB_PATH", raising=False)
    vol = tmp_path / "vol"; vol.mkdir()
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(vol))
    importlib.reload(d)
    s = d.db_persistence_status()
    assert s["tier"] == "Railway persistent volume" and s["persistent_across_redeploys"] is True
    assert str(d.get_db_path()) == str(vol / "analyses.db")
    # restore default module state for other tests
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)
    importlib.reload(d)


def test_calibration_metrics_present_and_sane():
    import math, random
    from services.score_calibration import calibrate
    random.seed(11)
    pairs = []
    for _ in range(300):
        sc = random.randint(0, 100)
        true_pd = 1 / (1 + math.exp(-(2 * (0.5 - sc / 100)) * 3))
        pairs.append({"imara_score": sc, "label": 1 if random.random() < true_pd else 0})
    r = calibrate(pairs, min_n=50)
    assert r["calibrated"] is True and "calibration" in r
    c = r["calibration"]
    assert abs(c["calibration_in_the_large"]["difference"]) < 0.08
    assert 0.6 < c["calibration_slope"] < 1.5
    assert c["brier_skill_score"] > 0
    assert len(c["reliability_curve"]) >= 2


def test_calibration_hostile_inputs_no_crash():
    import json
    from services.score_calibration import calibrate, calibration_metrics
    for p in ([], [{"imara_score": 50, "label": 1}] * 60, [{"imara_score": None, "label": 1}]):
        json.dumps(calibrate(p, min_n=50))
    json.dumps(calibration_metrics([0, 100] * 40, [1, 0] * 40, a=-5.0, b=2.0))


def test_upload_type_allowlist():
    import pytest
    from fastapi import HTTPException
    import main
    main._check_upload_type("statement.pdf")      # ok
    main._check_upload_type("books.XLSX")          # case-insensitive ok
    for bad in ("malware.exe", "archive.zip", "script.sh", "noext", ""):
        with pytest.raises(HTTPException) as ei:
            main._check_upload_type(bad)
        assert ei.value.status_code == 400


def test_add_owner_column_rejects_unknown_table():
    import pytest
    from services.database import _add_owner_column, _get_conn
    conn = _get_conn()
    try:
        with pytest.raises(ValueError):
            _add_owner_column(conn, "analyses; DROP TABLE analyses")
    finally:
        conn.close()


def test_gzip_compression_large_json_not_tiny():
    """Large JSON report is gzipped (the win); tiny responses + non-gzip clients are not
    (minimum_size honoured because GZip is the innermost middleware). Body integrity preserved."""
    import main
    from fastapi.testclient import TestClient
    big = {"analysis_id": "gztest", "imara_score": 55,
           "findings": [{"i": i, "d": "x" * 400} for i in range(120)]}
    main.analyses["gztest"] = big
    try:
        with TestClient(main.app) as c:
            r = c.get("/api/report/gztest", headers={"Accept-Encoding": "gzip"})
            assert r.headers.get("content-encoding") == "gzip"
            assert r.json()["imara_score"] == 55 and len(r.json()["findings"]) == 120
            h = c.get("/api/health", headers={"Accept-Encoding": "gzip"})
            assert h.headers.get("content-encoding") is None  # tiny -> not compressed
            n = c.get("/api/report/gztest", headers={"Accept-Encoding": "identity"})
            assert n.headers.get("content-encoding") is None  # client opted out
    finally:
        main.analyses.pop("gztest", None)


def test_request_body_size_cap():
    """Oversized JSON body to a public endpoint is rejected (413) before parsing —
    closes the unauthenticated huge-body memory-exhaustion vector."""
    import main
    from fastapi.testclient import TestClient
    try:
        with TestClient(main.app) as c:
            big = {"income_types": ["employment"], "junk": "A" * (2 * 1024 * 1024 + 1000)}
            assert c.post("/api/tax/relocation", json=big).status_code == 413
            assert c.post("/api/tax/relocation", json={"income_types": ["employment"]}).status_code != 413
    finally:
        main.limiter.reset()


def test_public_tax_endpoint_rate_limited():
    """The public, unauthenticated /api/tax/relocation is rate-limited (default 30/hour)."""
    import main
    from fastapi.testclient import TestClient
    prev = getattr(main.limiter, "enabled", True)
    main.limiter.enabled = True   # conftest disables it globally for tests; need it ON here
    main.limiter.reset()
    try:
        with TestClient(main.app) as c:
            codes = [c.post("/api/tax/relocation", json={}).status_code for _ in range(34)]
        assert 429 in codes, "expected a 429 once the per-IP limit is exceeded"
        assert codes.count(200) <= 31
    finally:
        main.limiter.reset()
        main.limiter.enabled = prev
