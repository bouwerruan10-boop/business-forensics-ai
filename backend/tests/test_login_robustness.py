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


def test_clean_secret_strips_surrounding_quotes():
    """config._clean_secret: a host env value pasted with surrounding quotes (a common
    Railway artifact) must normalise to the bare password, not a quoted one (else exact-match
    auth gives a false 'Invalid password'). Inner quotes are preserved."""
    cs = cfg._clean_secret
    assert cs('"hunter2"') == "hunter2"          # double-quoted paste
    assert cs("'hunter2'") == "hunter2"          # single-quoted paste
    assert cs('  "hunter2"  ') == "hunter2"      # quotes + outer whitespace
    assert cs('"hunter2"\n') == "hunter2"        # quotes + trailing newline
    assert cs("plain") == "plain"                # untouched
    assert cs('pa"ss') == 'pa"ss'                # inner quote preserved
    assert cs("'mismatched\"") == "'mismatched\""  # non-matching pair: left as-is
    assert cs('"') == '"'                        # single lone quote: not a pair
    assert cs("") == ""                          # empty stays empty
