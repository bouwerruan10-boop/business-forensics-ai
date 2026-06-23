"""Regression: the operator gate must NEVER block CORS preflight (OPTIONS).

Bug (found via a live test): with OPERATOR_PASSWORD set, _operator_gate ran as the
outermost middleware and 401'd the browser's OPTIONS preflight to /api/analyze —
so the real POST never fired ("Failed to fetch" / 503). Preflight carries no
Authorization header by design, so it must pass through to CORS; the gate still
protects the real (token-bearing) request.
"""
from fastapi.testclient import TestClient

ORIGIN = "https://business-forensics-ai.vercel.app"


def test_preflight_not_gated_but_real_request_is(monkeypatch):
    import config
    monkeypatch.setattr(config, "AUTH_ENABLED", True)  # operator gate active
    import main
    with TestClient(main.app) as c:
        # CORS preflight must pass (was 401 before the fix)
        pre = c.options("/api/analyze", headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        })
        assert pre.status_code == 200, pre.status_code
        assert pre.headers.get("access-control-allow-origin") == ORIGIN

        # The real request stays gated without a valid operator token
        post = c.post("/api/analyze", headers={"Origin": ORIGIN},
                      files={"files": ("f.csv", b"Item,Amount\nRevenue,100\n", "text/csv")},
                      data={"company_name": "Gate Test", "consent": "true"})
        assert post.status_code == 401, post.status_code


def test_gate_401_carries_cors_headers_so_browser_can_read_it(monkeypatch):
    """Regression: the operator-gate's 401 short-circuits BEFORE CORSMiddleware, so it must
    echo CORS headers itself. Without them the browser can't read the 401 and shows a
    misleading 'Failed to fetch' (mistaken for a 503/outage) instead of the frontend's
    'session expired, sign in again' message. (Diagnosed from Railway logs: every
    POST /api/analyze was a 401, never a crash.)"""
    import config
    monkeypatch.setattr(config, "AUTH_ENABLED", True)
    import main
    with TestClient(main.app) as c:
        # Allowed origin, no token -> 401 that the browser CAN read (CORS echoed)
        r = c.post("/api/analyze", headers={"Origin": ORIGIN},
                   files={"files": ("f.csv", b"Item,Amount\nRevenue,100\n", "text/csv")},
                   data={"company_name": "Gate Test", "consent": "true"})
        assert r.status_code == 401, r.status_code
        assert r.headers.get("access-control-allow-origin") == ORIGIN
        assert r.headers.get("access-control-allow-credentials") == "true"

        # A non-allowed origin gets no CORS echo (still 401, just not readable cross-origin)
        r2 = c.post("/api/analyze", headers={"Origin": "https://evil.example.com"},
                    files={"files": ("f.csv", b"Item,Amount\nRevenue,100\n", "text/csv")},
                    data={"company_name": "Gate Test", "consent": "true"})
        assert r2.status_code == 401, r2.status_code
        assert r2.headers.get("access-control-allow-origin") is None
