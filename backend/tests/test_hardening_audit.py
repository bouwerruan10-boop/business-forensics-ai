"""Regression tests for the end-to-end hardening pass (v1.50): constant-time key
compares, charts None-guard, and that the client-facing error path is generic."""
import os
import importlib
import pytest
from fastapi import HTTPException
from starlette.requests import Request


def _req(headers):
    scope = {"type": "http", "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()]}
    return Request(scope)


def test_api_and_admin_key_compare(monkeypatch):
    monkeypatch.setenv("API_SECRET_KEY", "sekret")
    monkeypatch.setenv("ADMIN_API_KEY", "adm")
    monkeypatch.setenv("MOCK_MODE", "true")
    import main
    importlib.reload(main)
    # correct keys pass
    main.verify_api_key(_req({"x-api-key": "sekret"}))
    main.verify_admin_key(_req({"x-admin-key": "adm"}))
    # wrong / missing keys 401
    for hdr, val in [("x-api-key", "wrong"), ("x-api-key", "")]:
        with pytest.raises(HTTPException):
            main.verify_api_key(_req({hdr: val}))
    for hdr, val in [("x-admin-key", "bad"), ("x-admin-key", "")]:
        with pytest.raises(HTTPException):
            main.verify_admin_key(_req({hdr: val}))


def test_severity_donut_tolerates_none_and_empty():
    from services.charts import severity_donut
    for arg in (None, [], [{"severity": "high"}]):
        out = severity_donut(arg)
        assert isinstance(out, (bytes, bytearray)) and len(out) > 0


def test_status_error_message_is_generic_not_raw(monkeypatch):
    """The background-task failure path must store a GENERIC client message (no raw
    exception text) and set status=error even if save_error is unavailable."""
    monkeypatch.setenv("MOCK_MODE", "true")
    import main
    importlib.reload(main)
    src = __import__("inspect").getsource(main._run_analysis)
    assert "Analysis failed. Please try again" in src
    # status flips to error BEFORE save_error is attempted (ordering), and save_error is guarded
    assert src.index('["status"] = "error"') < src.index("save_error(analysis_id, _generic)")
    assert "str(e)" not in src.split("except Exception as e:")[-1].split("finally:")[0]  # raw exc not surfaced


def test_upload_rejects_empty_and_oversize(monkeypatch):
    """/api/analyze must reject empty (400) and per-file oversize (413) uploads at the door."""
    monkeypatch.setenv("MOCK_MODE", "true")
    import logging
    logging.disable(logging.CRITICAL)
    import main
    importlib.reload(main)
    from fastapi.testclient import TestClient
    c = TestClient(main.app)
    empty = c.post("/api/analyze", files=[("files", ("e.csv", b"", "text/csv"))],
                   data={"file_categories": '["financial"]'})
    assert empty.status_code == 400 and "empty" in empty.json()["detail"].lower()
    big = b"a" * (main.MAX_UPLOAD_FILE_BYTES + 1024)
    over = c.post("/api/analyze", files=[("files", ("b.csv", big, "text/csv"))],
                  data={"file_categories": '["financial"]'})
    assert over.status_code == 413 and "per-file" in over.json()["detail"].lower()
    logging.disable(logging.NOTSET)
