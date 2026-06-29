"""Shared test configuration.

Disable the per-IP rate limiter during tests: several no-API end-to-end tests each
POST /api/analyze from the same TestClient IP, which otherwise exhausts the default
3/hour budget and makes them 429 each other (order-dependent flakiness). No test
asserts rate-limiting behaviour, so disabling it for the suite is safe.
"""
import pytest


@pytest.fixture(autouse=True)
def _disable_rate_limit():
    try:
        import main
        prev = getattr(main.limiter, "enabled", True)
        main.limiter.enabled = False
        yield
        main.limiter.enabled = prev
    except Exception:
        yield


@pytest.fixture(autouse=True)
def _neutralize_ambient_auth(monkeypatch):
    """Make the suite independent of a developer's local backend/.env auth settings.

    Once OPERATOR_PASSWORD is set in .env (operator login activated), the gate is ON for
    the whole process, so every endpoint test that doesn't authenticate would 401. Force
    auth OFF by default here. The gate reads config.AUTH_ENABLED and get_principal reads
    auth.AUTH_ENABLED, so both are cleared. The auth tests opt back IN via their own
    monkeypatch on the same stack (applied after this, restored before this), so they stay
    correct — and the suite is now green whether or not .env has a password.
    """
    for mod, attr, val in (("config", "AUTH_ENABLED", False), ("config", "OPERATOR_PASSWORD", ""),
                           ("auth", "AUTH_ENABLED", False)):
        try:
            monkeypatch.setattr(__import__(mod), attr, val, raising=False)
        except Exception:
            pass
    yield
