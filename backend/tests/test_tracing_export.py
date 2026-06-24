"""Langfuse export seam (v1.96): must be no-op-safe, never raise, and never
require the SDK. Privacy: the seam only ever sees token counts, so there is no
prompt text to leak — these tests lock the 'never breaks an analysis' contract."""

import services.tracing as tr


def _reset():
    tr._reset_lf_client_for_tests()


def test_new_ledger_stores_analysis_id():
    led = tr.new_ledger("abc-123")
    assert led.analysis_id == "abc-123"
    assert tr.current_ledger() is led


def test_new_ledger_default_id_is_none():
    led = tr.new_ledger()
    assert led.analysis_id is None


def test_flush_tracing_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("TRACING_ENABLED", raising=False)
    _reset()
    assert tr.flush_tracing() is None  # no raise


def test_record_call_never_raises_with_tracing_on_and_no_sdk(monkeypatch):
    # tracing_enabled() true, but langfuse SDK absent -> export must no-op silently.
    monkeypatch.setenv("TRACING_ENABLED", "1")
    _reset()
    tr.new_ledger("run-1")
    tr.record_call("FinancialAgent", "claude-sonnet-4-6", 1000, 500, 1200)  # must not raise
    # ledger still recorded the call locally regardless of export
    assert tr.current_ledger().summary()["calls"] == 1


def test_export_swallows_a_broken_client(monkeypatch):
    monkeypatch.setenv("TRACING_ENABLED", "1")
    _reset()

    class _Boom:
        def trace(self, **k): raise RuntimeError("trace boom")
        def generation(self, **k): raise RuntimeError("gen boom")

    monkeypatch.setattr(tr, "_lf_client", lambda: _Boom())
    tr.new_ledger("run-2")
    tr.record_call("AuditorAgent", "claude-haiku-4-5-20251001", 10, 20, 5)  # must not raise
    tr.flush_tracing()  # must not raise
    assert tr.current_ledger().summary()["calls"] == 1


def test_export_uses_per_analysis_trace_when_available(monkeypatch):
    monkeypatch.setenv("TRACING_ENABLED", "1")
    _reset()
    seen = {"trace_kwargs": None, "gens": 0}

    class _Trace:
        def generation(self, **k):
            seen["gens"] += 1

    class _Client:
        def trace(self, **k):
            seen["trace_kwargs"] = k
            return _Trace()
        def generation(self, **k):
            seen["gens"] += 1
        def flush(self):
            pass

    monkeypatch.setattr(tr, "_lf_client", lambda: _Client())
    tr.new_ledger("analysis-xyz")
    tr.record_call("CEO", "claude-sonnet-4-6", 100, 50, 300)
    tr.record_call("CEO", "claude-sonnet-4-6", 80, 40, 250)
    # one trace created (id == analysis_id), reused for both generations
    assert seen["trace_kwargs"]["id"] == "analysis-xyz"
    assert seen["gens"] == 2
    tr.flush_tracing()
