"""Tests for the future-proofing builds: model fallback chain + decision audit log."""
from pathlib import Path
import pytest
import agents.base_agent as ba


class _Resp:
    def __init__(self, text):
        self.content = [type("C", (), {"text": text})()]
        self.usage = type("U", (), {"input_tokens": 1, "output_tokens": 1})()


def test_model_fallback_on_unavailable(monkeypatch):
    tried = []

    class NotFound(Exception):
        status_code = 404

    class FC:
        class messages:
            @staticmethod
            def create(model, **k):
                tried.append(model)
                if model == "primary":
                    raise NotFound("model not found / deprecated")
                return _Resp("ok:" + model)

    monkeypatch.setattr(ba, "client", FC)
    monkeypatch.setattr(ba, "MODEL", "primary")
    monkeypatch.setattr(ba, "MODEL_FALLBACKS", ["fb1", "fb2"])

    class A(ba.BaseAgent):
        system_prompt = "x"

    assert A()._call_claude("hi") == "ok:fb1"
    assert tried == ["primary", "fb1"]   # stopped at first working fallback


def test_auth_error_does_not_burn_fallbacks(monkeypatch):
    tried = []

    class Auth(Exception):
        status_code = 401

    class FC:
        class messages:
            @staticmethod
            def create(model, **k):
                tried.append(model)
                raise Auth("invalid api key")

    monkeypatch.setattr(ba, "client", FC)
    monkeypatch.setattr(ba, "MODEL", "primary")
    monkeypatch.setattr(ba, "MODEL_FALLBACKS", ["fb1"])

    class A(ba.BaseAgent):
        system_prompt = "x"

    with pytest.raises(Auth):
        A()._call_claude("hi")
    assert tried == ["primary"]   # non-model error raises immediately


def test_audit_chain_and_tamper_evidence(tmp_path, monkeypatch):
    import services.database as db
    from services.audit_log import build_audit_record
    monkeypatch.setattr(db, "_DB_PATH", Path(str(tmp_path / "audit.db")))
    db.init_db()
    s1 = db.append_audit(build_audit_record({"analysis_id": "a1", "imara_score": 48, "financial_figures": {"revenue": 1_000_000}}, "d1"))
    s2 = db.append_audit(build_audit_record({"analysis_id": "a2", "imara_score": 71, "financial_figures": {"revenue": 5_000_000}}, "d2"))
    assert s2["prev_hash"] == s1["record_hash"]          # chained
    assert db.verify_audit_chain()["intact"] is True
    rows = db.get_audit("a1")
    assert rows and rows[0]["imara_score"] == 48 and rows[0]["figures_hash"]
    # tamper a stored row -> chain must report broken
    import sqlite3
    con = sqlite3.connect(str(tmp_path / "audit.db"))
    con.execute("UPDATE decision_audit SET record_json = record_json || 'X' WHERE analysis_id='a1'")
    con.commit(); con.close()
    assert db.verify_audit_chain()["intact"] is False


def test_audit_record_never_stores_raw_documents():
    from services.audit_log import build_audit_record
    rec = build_audit_record({"analysis_id": "x", "financial_figures": {"revenue": 123}},
                             "SECRET RAW BANK STATEMENT TEXT")
    assert "SECRET RAW BANK STATEMENT" not in str(rec)   # only hashes stored (POPIA)
    assert rec["inputs_hash"] and rec["figures_hash"]
    assert rec["models"]["model"] and "fallbacks" in rec["models"]


def test_audit_record_json_safe_with_nonfinite():
    """A report with NaN/inf score/figures must still yield a strict-JSON-safe audit record."""
    import json, math
    from services.audit_log import build_audit_record
    for rep in ({"imara_score": float("nan"), "imara_completeness": float("inf"),
                 "financial_figures": {"revenue": float("inf")}},
                {"imara_score": 1e400, "business_name": "X"}):
        rec = build_audit_record(rep, "inputs")
        json.dumps(rec, allow_nan=False)   # raises if a non-finite leaked through


def test_finite_safe_recursive():
    import json
    from services.jsonsafe import finite_safe
    out = finite_safe({"a": float("nan"), "b": [1, float("inf"), {"c": float("-inf")}],
                       "d": "ok", "e": 3.14, "f": None, "g": True})
    json.dumps(out, allow_nan=False)   # strict-safe
    assert out == {"a": None, "b": [1, None, {"c": None}], "d": "ok", "e": 3.14, "f": None, "g": True}


def test_safe_json_response_strips_nonfinite():
    """The default response class makes EVERY endpoint finite-safe (root-cause guard)."""
    import json
    import main
    r = main.SafeJSONResponse(content={"x": float("nan"), "y": [float("inf")], "z": 1.5})
    assert json.loads(r.body.decode()) == {"x": None, "y": [None], "z": 1.5}
