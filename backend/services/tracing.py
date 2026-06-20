"""
Observability seam — per-analysis LLM usage ledger + Langfuse-ready export.

Real token/cost capture for every Claude call, attributed to the analysis that
made it (correct even when several analyses run concurrently), plus a no-op-by-
default hook to export spans to Langfuse when configured. Nothing here changes
behaviour unless an analysis opens a ledger; export stays dormant until
LANGFUSE_* / TRACING_ENABLED is set.

Design: the ledger lives in a contextvars.ContextVar so it is per-analysis. The
parallel pipeline propagates it into worker threads with contextvars.copy_context
(see agents/parallel.py), so every wave/agent records into the right ledger.
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

    def __init__(self):
        self._lock = threading.Lock()
        self.calls = []

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


def new_ledger() -> UsageLedger:
    """Open a fresh ledger for the current analysis context."""
    ledger = UsageLedger()
    _LEDGER.set(ledger)
    return ledger


def current_ledger():
    return _LEDGER.get()


def tracing_enabled() -> bool:
    return bool(os.environ.get("LANGFUSE_PUBLIC_KEY") or os.environ.get("TRACING_ENABLED"))


def record_call(span: str, model: str, in_tok: int, out_tok: int, ms: int):
    """Record one LLM call into the active analysis ledger (if any) and, when
    tracing is enabled, best-effort export to Langfuse. Never raises."""
    ledger = _LEDGER.get()
    if ledger is not None:
        ledger.record(span, model, in_tok, out_tok, ms)
    if tracing_enabled():
        _maybe_export(span, model, in_tok, out_tok, ms)


def _maybe_export(span, model, in_tok, out_tok, ms):
    """Dormant Langfuse export hook. Lazy-imports the SDK so the package is an
    optional dependency; any failure is swallowed so observability never breaks
    an analysis. Full span-tree wiring is the activation step once a Langfuse
    project + keys exist."""
    try:
        from langfuse import Langfuse  # type: ignore
        Langfuse().generation(
            name=span, model=model,
            usage={"input": in_tok, "output": out_tok},
        )
    except Exception:
        return
