"""
Base agent — all specialist agents inherit from this.
Each agent gets: business context, benchmark profile, domain data,
shared memory from prior agents, and returns structured findings.
"""
import anthropic
import httpx
import json
import os
from memory.shared_memory import SharedMemory, AgentFinding
from config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS, MOCK_MODE, PARSE_MODEL, MODEL_FALLBACKS
from services.benchmark_service import format_benchmark_context

# Build an httpx client that works in any environment:
# - On developer machines: no proxy needed, standard SSL
# - In sandboxes/CI that use an HTTP CONNECT proxy: use HTTPS_PROXY env var
# - Sandboxes that set ALL_PROXY=socks5h://... (unsupported by httpx): filter it out
_raw_proxy = (
    os.environ.get("HTTPS_PROXY")
    or os.environ.get("https_proxy")
    or os.environ.get("HTTP_PROXY")
    or os.environ.get("http_proxy")
    or None
)
# Only use HTTP(S) proxies — socks5h is unsupported by httpx 0.27
_proxy_url = None if (_raw_proxy and _raw_proxy.startswith("socks")) else _raw_proxy
# Disable SSL verification only when a proxy that intercepts TLS is detected
# (sandboxes using mitmproxy / squid with self-signed certs)
_verify_ssl = not bool(_proxy_url and os.environ.get("PROXY_SSL_VERIFY", "1") == "0")
_http_client = httpx.Client(
    proxy=_proxy_url,
    timeout=httpx.Timeout(120.0),
    verify=_verify_ssl,
    trust_env=False,
)
# In MOCK_MODE the client is never called — skip creation so the server
# starts without a valid API key (useful for UI demos and testing).
client = None if MOCK_MODE else anthropic.Anthropic(
    api_key=ANTHROPIC_API_KEY, http_client=_http_client
)



_TRANSIENT_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}


def _is_transient(exc) -> bool:
    """Classify an exception as a transient (retryable) LLM/API error."""
    name = type(exc).__name__.lower()
    if any(k in name for k in ("ratelimit", "timeout", "connection", "overloaded", "internalserver", "apistatus", "serviceunavailable")):
        return True
    code = getattr(exc, "status_code", None)
    return code in _TRANSIENT_STATUS


def _is_model_unavailable(exc) -> bool:
    """Classify an error as 'this model can't be used' (deprecated/retired/unknown)
    so we fall back to the next model in the chain rather than failing the run."""
    if exc is None:
        return False
    if getattr(exc, "status_code", None) == 404:
        return True
    s = str(exc).lower()
    if "model" in s and any(k in s for k in ("not found", "does not exist", "deprecat",
                                             "not_found", "unknown model", "no longer available", "invalid model")):
        return True
    return "notfound" in type(exc).__name__.lower()


class BaseAgent:
    name: str = "Base Agent"
    role: str = ""
    system_prompt: str = ""

    def _call_claude(self, user_message: str, system_override: str = "", model_override: str = "") -> str:
        system = system_override or self.system_prompt
        primary = model_override or MODEL
        # Provider-resilience: try the chosen model, then ordered fallbacks if it is
        # unavailable/deprecated (or transient-exhausted), so a model retirement degrades
        # gracefully instead of taking the whole pipeline down.
        candidates = [primary] + [m for m in MODEL_FALLBACKS if m and m != primary]
        import time as _time
        _t0 = _time.perf_counter()
        response = None
        used_model = primary
        last_exc = None
        for model in candidates:
            _attempts = 3
            for _attempt in range(_attempts):
                try:
                    response = client.messages.create(
                        model=model,
                        max_tokens=MAX_TOKENS,
                        system=system,
                        messages=[{"role": "user", "content": user_message}]
                    )
                    used_model = model
                    break
                except Exception as _exc:
                    last_exc = _exc
                    if _is_transient(_exc) and _attempt < _attempts - 1:
                        import random as _r
                        _time.sleep((2 ** _attempt) + _r.random())
                        continue
                    break
            if response is not None:
                break
            # This model failed: fall back to the next only if it is unavailable/deprecated
            # or a transient that exhausted retries; raise auth/400-type errors immediately.
            if not (_is_model_unavailable(last_exc) or _is_transient(last_exc)):
                raise last_exc
            if model != candidates[-1]:
                print("[model] '{}' unavailable ({}); falling back to next model".format(model, last_exc))
        if response is None:
            raise last_exc
        try:  # observability: attribute token usage + cost to this analysis (never fatal)
            from services.tracing import record_call
            _u = getattr(response, "usage", None)
            record_call(self.name, used_model,
                        getattr(_u, "input_tokens", 0) or 0,
                        getattr(_u, "output_tokens", 0) or 0,
                        int((_time.perf_counter() - _t0) * 1000))
        except Exception:
            pass
        return response.content[0].text

    def _build_benchmark_block(self, memory: SharedMemory) -> str:
        return format_benchmark_context(
            industry_key=memory.industry_key or 'general',
            annual_revenue=memory.annual_revenue,
            currency=memory.currency
        )

    def _parse_findings(self, raw_text: str, memory: SharedMemory) -> list[AgentFinding]:
        """
        Convert free-form analysis text into structured AgentFinding objects.
        Uses a second Claude call for reliable JSON extraction.
        """
        parse_prompt = f"""You are a precision data extractor for a consulting firm.
Convert the following analysis into a JSON array of findings.

Each finding object MUST have ALL of these exact keys:
- "category": string (e.g. "Revenue", "Cost Control", "Operations", "Risk", "HR")
- "severity": one of exactly: "critical", "high", "medium", "low"
- "title": max 10 words, must be specific (include numbers where possible)
- "detail": 2-4 sentences. MUST cite specific numbers from the analysis. No generic language.
- "financial_impact": specific currency amount or range (e.g. "R 1.2M annual profit erosion"). Use "Unquantified" only if truly no data.
- "recommendation": one clear, actionable sentence starting with a verb.
- "roi_estimate": estimated return and timeframe (e.g. "R 800K saving within 9 months"). Use "TBD with client" if unknown.
- "cost_of_inaction": what happens if this is NOT fixed (e.g. "Compounding losses of ~R 3.6M over 3 years if unaddressed")
- "benchmark_reference": the specific benchmark comparison made (e.g. "Gross margin 21.3% vs industry median 33.2%")
- "data_source": which file/sheet/section this finding came from
- "quick_win": true if this can be actioned in under 30 days, false otherwise

ANALYSIS TO EXTRACT FROM:
{raw_text}

Return ONLY a valid JSON array. No explanation text. No markdown fences.
"""
        _parse_system = "You are a precise JSON data-extraction engine. Output only valid JSON — no prose, no markdown fences."
        try:
            raw = self._call_claude(parse_prompt, system_override=_parse_system, model_override=PARSE_MODEL)
        except Exception as _exc:
            print("[parse] {} model failed ({}); retrying on default model".format(PARSE_MODEL, _exc))
            raw = self._call_claude(parse_prompt, system_override=_parse_system)
        raw = raw.strip()

        # Strip markdown code fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip().rstrip("`").strip()

        try:
            items = json.loads(raw)
            if not isinstance(items, list):
                items = [items]
        except Exception:
            # Fallback: single finding preserving the analysis text
            items = [{
                "category": "General",
                "severity": "medium",
                "title": "Analysis finding — review required",
                "detail": raw_text[:400],
                "financial_impact": "Unquantified — requires client data",
                "recommendation": "Review this area with management team",
                "roi_estimate": "TBD with client",
                "cost_of_inaction": "Risk of continued underperformance if unaddressed",
                "benchmark_reference": "See analysis above",
                "data_source": "Uploaded data",
                "quick_win": False
            }]

        findings = []
        for item in items:
            findings.append(AgentFinding(
                agent=self.name,
                category=item.get("category", "General"),
                severity=item.get("severity", "medium"),
                title=item.get("title", "Finding"),
                detail=item.get("detail", ""),
                financial_impact=item.get("financial_impact", "Unquantified"),
                recommendation=item.get("recommendation", ""),
                roi_estimate=item.get("roi_estimate", "TBD with client"),
                cost_of_inaction=item.get("cost_of_inaction", ""),
                benchmark_reference=item.get("benchmark_reference", ""),
                data_source=item.get("data_source", ""),
                quick_win=bool(item.get("quick_win", False))
            ))
        return findings

    def analyze(self, business_data: dict, memory: SharedMemory) -> list[AgentFinding]:
        """Override in each specialist agent."""
        raise NotImplementedError
