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


def test_docs_and_openapi_disabled_in_prod_by_default():
    # EXPOSE_DOCS defaults false -> schema/UI hidden (enumeration-surface reduction)
    with TestClient(main.app) as c:
        assert c.get("/docs").status_code == 404
        assert c.get("/redoc").status_code == 404
        assert c.get("/openapi.json").status_code == 404


def test_cors_rejects_foreign_vercel_allows_project_only():
    with TestClient(main.app) as c:
        foreign = c.get("/api/health", headers={"Origin": "https://evil-site.vercel.app"})
        assert foreign.headers.get("access-control-allow-origin") is None
        proj = c.get("/api/health", headers={"Origin": "https://business-forensics-ai-abc123.vercel.app"})
        assert proj.headers.get("access-control-allow-origin") == "https://business-forensics-ai-abc123.vercel.app"
