"""Operator authentication: token logic + the gate middleware (backward-compatible)."""
import json


def test_token_roundtrip(monkeypatch):
    import auth
    monkeypatch.setattr(auth, "AUTH_SECRET", "s3cr3t")
    t = auth.issue_token(sub="operator")
    p = auth.verify_token(t)
    assert p and p["sub"] == "operator" and p["kind"] == "operator"
    # tampered signature / payload -> rejected
    assert auth.verify_token(t[:-1] + ("x" if t[-1] != "x" else "y")) is None
    assert auth.verify_token("garbage") is None
    assert auth.verify_token("") is None


def test_token_expiry_and_wrong_secret(monkeypatch):
    import auth
    monkeypatch.setattr(auth, "AUTH_SECRET", "s3cr3t")
    body = auth._b64e(json.dumps({"sub": "x", "kind": "operator", "exp": 1}).encode())
    expired = body + "." + auth._sign(body)
    assert auth.verify_token(expired) is None                 # exp in 1970
    good = auth.issue_token()
    monkeypatch.setattr(auth, "AUTH_SECRET", "different")      # signed with old secret
    assert auth.verify_token(good) is None                    # signature no longer valid


def test_get_principal_open_when_disabled(monkeypatch):
    import auth
    monkeypatch.setattr(auth, "AUTH_ENABLED", False)
    # no request inspection needed when disabled
    pr = auth.get_principal(request=None)  # type: ignore
    assert pr.id == "operator"


def _enable(monkeypatch):
    import config, auth
    monkeypatch.setattr(config, "AUTH_ENABLED", True)
    monkeypatch.setattr(config, "OPERATOR_PASSWORD", "pw-123")
    monkeypatch.setattr(auth, "AUTH_ENABLED", True)
    monkeypatch.setattr(auth, "AUTH_SECRET", "test-secret")


def test_gate_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("BF_DB_PATH", str(tmp_path / "auth.db"))
    _enable(monkeypatch)
    import main
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        assert c.get("/api/health").json()["auth_required"] is True
        assert c.post("/api/login", json={"password": "wrong"}).status_code == 401
        r = c.post("/api/login", json={"password": "pw-123"})
        assert r.status_code == 200 and r.json().get("token")
        H = {"Authorization": "Bearer " + r.json()["token"]}
        # canonical report gated without token, allowed (404 not found) with token
        assert c.get("/api/report/nope-id").status_code == 401
        assert c.get("/api/report/nope-id", headers=H).status_code == 404
        # analyze gated
        assert c.post("/api/analyze", files={"files": ("f.csv", b"Item,Amount\nRevenue,1\n", "text/csv")},
                      data={"company_name": "x", "file_categories": "[]"}).status_code == 401
        # public surfaces stay open (never 401)
        assert c.get("/api/report/demo-001").status_code != 401
        assert c.get("/api/shared/zzz").status_code != 401      # 410/404, not blocked
        assert c.get("/api/health").status_code == 200


def test_gate_disabled_is_backward_compatible(monkeypatch, tmp_path):
    monkeypatch.setenv("BF_DB_PATH", str(tmp_path / "open.db"))
    import config, auth
    monkeypatch.setattr(config, "AUTH_ENABLED", False)
    monkeypatch.setattr(auth, "AUTH_ENABLED", False)
    import main
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        assert c.get("/api/health").json()["auth_required"] is False
        assert c.get("/api/report/nope-id").status_code == 404   # open
        assert c.post("/api/login", json={"password": "x"}).json() == {"auth_required": False}
