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
