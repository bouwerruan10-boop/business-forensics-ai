"""Opt-in backend consent enforcement on /api/analyze (POPIA defense-in-depth).
Only the REJECTION path is tested here — it returns 400 BEFORE any background
task spawns, so it stays fully isolated. The accepted-with-consent path is
already covered by test_integration_noapi (which sends consent='true')."""
import io, json
import pytest
import config as cfg
import agents.base_agent as ba


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BF_DB_PATH", str(tmp_path / "c.db"))
    monkeypatch.setattr(ba, "client", None)
    monkeypatch.setattr(cfg, "REQUIRE_CONSENT", True)
    from fastapi.testclient import TestClient
    import main
    with TestClient(main.app) as c:
        yield c


def _post(c, data_extra):
    data = {"company_name": "X", "file_categories": json.dumps(["financial"]), **data_extra}
    return c.post("/api/analyze",
                  files={"files": ("f.csv", io.BytesIO(b"Item,Amount\nRevenue,100\n"), "text/csv")},
                  data=data)


def test_rejected_when_consent_absent(client):
    r = _post(client, {})
    assert r.status_code == 400 and "consent" in r.json()["detail"].lower()


def test_rejected_when_consent_falsey(client):
    r = _post(client, {"consent": "false"})
    assert r.status_code == 400
