"""
Observability seam — per-analysis LLM usage ledger + Langfuse export.

Real token/cost capture for every Claude call, attributed to the analysis that
made it (correct even when several analyses run concurrently), plus a
no-op-by-default Langfuse exporter that activates only when LANGFUSE_* keys are
set. Nothing here changes analysis behaviour; export stays dormant until
configured and can never break a run (every export path swallows errors).

PRIVACY BY CONSTRUCTION: this seam only ever receives a span name, the model id,
token COUNTS and latency — never prompt or completion text. So enabling Langfuse
exports cost/latency/usage telemetry only; no client financial-document content
can leave to a third party through this path.

Design: the ledger lives in a contextvars.ContextVar so it is per-analysis. The
parallel pipeline propagates it into worker threads with contextvars.copy_context
(see agents/parallel.py), so every wave/agent records into the right ledger. A
Langfuse trace is created lazily per analysis (keyed by analysis_id) and reused
for that analysis's generations, so the dashboard groups calls per report.
"""
import contextvars
import os
import threading

# USD per 1,000,000 tokens (input, output). Estimates — override via env
# IMARA_PRICE_<MODELKEY>="in,out" if Anthropic pricing changes.
MODEL_PRICES = {
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
}
_DEFAULT_PRICE = (3.0, 15.0)


def _price_for(model: str):
    env = os.environ.get("IMARA_PRICE_" + model.replace("-", "_").upper())
    if env:
        try:
            a, b = env.split(",")
            return float(a), float(b)
        except Exception:
            pass
    return MODEL_PRICES.get(model, _DEFAULT_PRICE)


def cost_usd(model: str, in_tok: int, out_tok: int) -> float:
    pin, pout = _price_for(model)
    return round((in_tok / 1e6) * pin + (out_tok / 1e6) * pout, 6)


class UsageLedger:
    """Thread-safe accumulator of LLM calls for ONE analysis."""

    def __init__(self, analysis_id=None):
        self._lock = threading.Lock()
        self.calls = []
        self.analysis_id = analysis_id
        # Lazily-created Langfuse trace handle for this analysis (export path only).
        self._lf_trace = None
        self._lf_trace_tried = False

    def record(self, span: str, model: str, in_tok: int, out_tok: int, ms: int):
        entry = {
            "span": span, "model": model,
            "input_tokens": int(in_tok or 0), "output_tokens": int(out_tok or 0),
            "ms": int(ms or 0), "cost_usd": cost_usd(model, in_tok or 0, out_tok or 0),
        }
        with self._lock:
            self.calls.append(entry)

    def summary(self) -> dict:
        with self._lock:
            calls = list(self.calls)
        by_model, tin, tout, tcost, tms = {}, 0, 0, 0.0, 0
        for c in calls:
            m = by_model.setdefault(c["model"], {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
            m["calls"] += 1
            m["input_tokens"] += c["input_tokens"]
            m["output_tokens"] += c["output_tokens"]
            m["cost_usd"] = round(m["cost_usd"] + c["cost_usd"], 6)
            tin += c["input_tokens"]; tout += c["output_tokens"]
            tcost += c["cost_usd"]; tms += c["ms"]
        return {
            "calls": len(calls), "input_tokens": tin, "output_tokens": tout,
            "est_cost_usd": round(tcost, 4), "total_call_ms": tms, "by_model": by_model,
        }


_LEDGER: "contextvars.ContextVar[UsageLedger | None]" = contextvars.ContextVar("imara_usage_ledger", default=None)


def new_ledger(analysis_id=None) -> UsageLedger:
    """Open a fresh ledger for the current analysis context."""
    ledger = UsageLedger(analysis_id=analysis_id)
    _LEDGER.set(ledger)
    return ledger


def current_ledger():
    return _LEDGER.get()


def tracing_enabled() -> bool:
    return bool(os.environ.get("LANGFUSE_PUBLIC_KEY") or os.environ.get("TRACING_ENABLED"))


# -- Langfuse client singleton (lazy, version-tolerant, no-op safe) -------------
_LF_CLIENT = None
_LF_TRIED = False
_LF_LOCK = threading.Lock()


def _lf_client():
    """Return a cached Langfuse client, or None if the SDK/keys are unavailable.
    Created once; reused across calls. Never raises."""
    global _LF_CLIENT, _LF_TRIED
    if _LF_TRIED:
        return _LF_CLIENT
    with _LF_LOCK:
        if _LF_TRIED:
            return _LF_CLIENT
        _LF_TRIED = True
        try:
            from langfuse import Langfuse  # optional dependency
            # Reads LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST from env.
            _LF_CLIENT = Langfuse()
        except Exception:
            _LF_CLIENT = None
    return _LF_CLIENT


def _reset_lf_client_for_tests():
    """Test helper: forget the cached client so env changes take effect."""
    global _LF_CLIENT, _LF_TRIED
    _LF_CLIENT = None
    _LF_TRIED = False


def record_call(span: str, model: str, in_tok: int, out_tok: int, ms: int):
    """Record one LLM call into the active analysis ledger (if any) and, when
    tracing is enabled, best-effort export metadata to Langfuse. Never raises."""
    ledger = _LEDGER.get()
    if ledger is not None:
        ledger.record(span, model, in_tok, out_tok, ms)
    if tracing_enabled():
        _maybe_export(ledger, span, model, in_tok, out_tok, ms)


def _trace_for(ledger, client):
    """Lazily create/reuse a per-analysis Langfuse trace (Langfuse v2 SDK shape).
    Returns None on any incompatibility so the caller emits a flat generation."""
    if ledger is None:
        return None
    if ledger._lf_trace is not None or ledger._lf_trace_tried:
        return ledger._lf_trace
    ledger._lf_trace_tried = True
    try:
        ledger._lf_trace = client.trace(name="imara_analysis", id=ledger.analysis_id or None)
    except Exception:
        ledger._lf_trace = None
    return ledger._lf_trace


def _maybe_export(ledger, span, model, in_tok, out_tok, ms):
    """Best-effort, metadata-only export to Langfuse. NEVER raises.

    Emits one generation per LLM call (token usage + latency + estimated cost),
    grouped under a per-analysis trace when the SDK supports it. No prompt or
    completion text is available at this seam, so nothing sensitive is sent."""
    try:
        client = _lf_client()
        if client is None:
            return
        usage = {"input": int(in_tok or 0), "output": int(out_tok or 0)}
        meta = {"latency_ms": int(ms or 0), "cost_usd": cost_usd(model, in_tok or 0, out_tok or 0)}
        parent = _trace_for(ledger, client)
        target = parent if parent is not None else client
        target.generation(name=span, model=model, usage=usage, metadata=meta)
    except Exception:
        return


def flush_tracing():
    """Best-effort flush of buffered Langfuse events. NEVER raises. Call at the
    end of an analysis so a short-lived worker thread doesn't exit before the
    async exporter has sent."""
    if not tracing_enabled():
        return
    try:
        client = _lf_client()
        if client is not None:
            client.flush()
    except Exception:
        return
