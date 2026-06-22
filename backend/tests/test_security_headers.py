"""Security: baseline OWASP secure-headers must be present on every response."""
from fastapi.testclient import TestClient
import main


def test_security_headers_present_on_responses():
    with TestClient(main.app) as c:
        r = c.get("/api/health")
        assert r.headers.get("X-Content-Type-Options") == "nosniff"
        assert r.headers.get("X-Frame-Options") == "DENY"
        assert r.headers.get("Referrer-Policy") == "no-referrer"
        assert "geolocation=()" in (r.headers.get("Permissions-Policy") or "")
        assert "max-age=" in (r.headers.get("Strict-Transport-Security") or "")
