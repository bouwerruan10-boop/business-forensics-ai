"""Auth: operator login must tolerate stray whitespace (the trailing-newline-in-env gotcha that
caused false 'Invalid password') and non-ASCII passwords (old str compare_digest raised on those)."""
import config as cfg
import main
from fastapi.testclient import TestClient


def _login(pw):
    with TestClient(main.app) as c:
        return c.post("/api/login", json={"password": pw})


def test_login_tolerates_whitespace_and_unicode(monkeypatch):
    monkeypatch.setattr(cfg, "AUTH_ENABLED", True)
    monkeypatch.setattr(cfg, "OPERATOR_PASSWORD", "SecretéPass!")   # already-stripped stored value, incl. non-ASCII
    assert _login("SecretéPass!").status_code == 200
    assert _login(" SecretéPass! ").status_code == 200             # leading/trailing space tolerated
    assert _login("SecretéPass!\n").status_code == 200             # trailing newline tolerated
    assert "token" in _login("SecretéPass!").json()
    assert _login("wrong").status_code == 401
    assert _login("").status_code == 401
