"""BOLA / object-level authorization (OWASP API1) regression tests.

Proves a tenant cannot reach another tenant's records, that the require_owned()
helper enforces ownership, and a meta-test that EVERY record-scoped report/status
route is covered by the middleware id-extractor (so BOLA can't silently return).
"""
import uuid
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import config
import auth
import main
from auth import Principal, issue_token
from services.database import create_analysis, save_report, delete_analysis


@pytest.fixture
def auth_on(monkeypatch):
    """Turn operator/tenant auth ON with a deterministic test secret."""
    monkeypatch.setattr(config, "AUTH_ENABLED", True)
    monkeypatch.setattr(auth, "AUTH_ENABLED", True)
    monkeypatch.setattr(auth, "AUTH_SECRET", "test-secret-bola-123")
    yield


def _mk(owner):
    aid = str(uuid.uuid4())
    create_analysis(aid, {"company_name": owner, "industry_key": "general"}, owner=owner)
    save_report(aid, {"imara_score": 55, "company": owner})
    return aid


def test_middleware_blocks_cross_tenant_read(auth_on):
    a = _mk("tenantA")
    b = _mk("tenantB")
    try:
        tokA = issue_token(sub="tenantA")
        hA = {"Authorization": "Bearer " + tokA}
        with TestClient(main.app) as c:
            # owns it -> 200
            assert c.get("/api/report/" + a, headers=hA).status_code == 200
            assert c.get("/api/report/" + a + "/credit", headers=hA).status_code == 200
            # someone else's -> 404 (BOLA blocked, existence not leaked)
            assert c.get("/api/report/" + b, headers=hA).status_code == 404
            assert c.get("/api/report/" + b + "/credit", headers=hA).status_code == 404
            assert c.get("/api/status/" + b, headers=hA).status_code == 404
            # no token -> 401
            assert c.get("/api/report/" + a).status_code == 401
    finally:
        delete_analysis(a); delete_analysis(b)


def test_simulate_body_id_ownership(auth_on):
    a = _mk("tenantA")
    b = _mk("tenantB")
    try:
        hA = {"Authorization": "Bearer " + issue_token(sub="tenantA")}
        with TestClient(main.app) as c:
            assert c.post("/api/simulate/actions",
                          json={"analysis_id": b, "actions": []}, headers=hA).status_code == 404
            assert c.post("/api/simulate/montecarlo",
                          json={"analysis_id": b, "actions": []}, headers=hA).status_code == 404
            # own analysis works
            assert c.post("/api/simulate/actions",
                          json={"analysis_id": a, "actions": []}, headers=hA).status_code == 200
    finally:
        delete_analysis(a); delete_analysis(b)


def test_require_owned_helper(auth_on):
    a = _mk("tenantA")
    try:
        main.require_owned(a, Principal(id="tenantA"))          # owner -> no raise
        main.require_owned("demo-001", Principal(id="tenantX"))  # demo exempt
        with pytest.raises(HTTPException) as ei:
            main.require_owned(a, Principal(id="tenantB"))       # wrong owner -> 404
        assert ei.value.status_code == 404
    finally:
        delete_analysis(a)


def test_require_owned_noop_when_auth_disabled(monkeypatch):
    monkeypatch.setattr(config, "AUTH_ENABLED", False)
    a = _mk("tenantA")
    try:
        main.require_owned(a, Principal(id="anyone"))  # single-operator: no raise
    finally:
        delete_analysis(a)


def test_no_record_endpoint_escapes_ownership_gate():
    """META-GUARD: every /api/report/{analysis_id} and /api/status/{analysis_id} route
    must yield an id from _path_analysis_id, i.e. the middleware WILL owner-gate it.
    Fails if someone adds a record route the extractor doesn't recognise."""
    dummy = str(uuid.uuid4())
    missed = []
    for r in main.app.routes:
        path = getattr(r, "path", "")
        if "{analysis_id}" in path and (path.startswith("/api/report/") or path.startswith("/api/status/")):
            concrete = path.replace("{analysis_id}", dummy)
            if main._path_analysis_id(concrete) != dummy:
                missed.append(path)
    assert not missed, "record routes not covered by ownership middleware: " + repr(missed)


def test_admin_requires_operator_token(auth_on):
    """Admin endpoints must NOT be world-open: with auth on, an operator token is
    required (previously /api/admin/* was exempt from the gate -> open when ADMIN_API_KEY unset)."""
    with TestClient(main.app) as c:
        assert c.get("/api/admin/analyses").status_code == 401           # no token -> blocked
        h = {"Authorization": "Bearer " + issue_token(sub="operator")}
        assert c.get("/api/admin/analyses", headers=h).status_code != 401  # operator token -> allowed
        assert c.get("/api/v1/model-card").status_code == 200             # public /v1 still open
