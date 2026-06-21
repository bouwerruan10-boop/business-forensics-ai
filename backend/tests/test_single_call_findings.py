"""Tier 1.3 T2 — single-call structured findings (opt-in, default off).
Verifies: ON = one structured call; OFF = classic two calls; failure degrades to classic."""
import json
import agents.base_agent as ba
from agents.base_agent import BaseAgent
from memory.shared_memory import SharedMemory

_FINDINGS = json.dumps({"findings": [{
    "category": "Tax", "severity": "high", "title": "SBC rates not claimed",
    "detail": "R12,000,000 turnover qualifies for Section 12E of the Income Tax Act 58 of 1962.",
    "financial_impact": "R 81 802 annual saving", "recommendation": "Apply Section 12E.",
    "roi_estimate": "R 81 802 in year 1", "cost_of_inaction": "Overpaying corporate tax",
    "benchmark_reference": "Section 12E", "data_source": "financials", "quick_win": True}]})


class _U:
    input_tokens = 10
    output_tokens = 10


class _C:
    def __init__(self, t):
        self.text = t


class _Msg:
    def __init__(self, t):
        self.content = [_C(t)]
        self.usage = _U()


class _Client:
    """Records calls; returns findings JSON for any structured (output_config) call, prose otherwise.
    If raise_first_structured, the first structured call raises (to exercise the degrade path)."""
    def __init__(self, raise_first_structured=False):
        self.calls = []
        self.raise_first_structured = raise_first_structured
        self._structured_seen = 0

    class _Messages:
        def __init__(self, outer):
            self.o = outer

        def create(self, **kw):
            self.o.calls.append(kw)
            if "output_config" in kw:
                self.o._structured_seen += 1
                if self.o.raise_first_structured and self.o._structured_seen == 1:
                    raise RuntimeError("structured boom")
                return _Msg(_FINDINGS)
            return _Msg("Prose analysis with R12,000,000 turnover.")

    @property
    def messages(self):
        return _Client._Messages(self)


class _Agent(BaseAgent):
    name = "TestAgent"
    system_prompt = "You are a test specialist."

    def analyze(self, business_data, memory):
        return self._findings_from("Analyze this business.", memory)


def _run(single, client):
    sc, sf = ba.client, ba.SINGLE_CALL_FINDINGS
    ba.client, ba.SINGLE_CALL_FINDINGS = client, single
    try:
        return _Agent().analyze({}, SharedMemory())
    finally:
        ba.client, ba.SINGLE_CALL_FINDINGS = sc, sf


def test_single_call_makes_one_structured_call():
    c = _Client()
    findings = _run(True, c)
    assert len(c.calls) == 1, f"expected 1 call, got {len(c.calls)}"
    assert "output_config" in c.calls[0]
    assert len(findings) == 1 and findings[0].title == "SBC rates not claimed"
    assert findings[0].agent == "TestAgent"


def test_classic_makes_two_calls():
    c = _Client()
    findings = _run(False, c)
    assert len(c.calls) == 2, f"expected 2 calls, got {len(c.calls)}"
    assert "output_config" not in c.calls[0]   # prose analysis
    assert "output_config" in c.calls[1]        # structured parse
    assert len(findings) == 1 and findings[0].title == "SBC rates not claimed"


def test_single_call_degrades_to_classic_on_failure():
    c = _Client(raise_first_structured=True)
    findings = _run(True, c)
    # structured attempt (raises) -> classic analyze (prose) -> structured parse = 3 calls
    assert len(c.calls) == 3, f"expected 3 calls, got {len(c.calls)}"
    assert len(findings) == 1 and findings[0].title == "SBC rates not claimed"


# ── Robustness of the single-call path under hostile/odd model output ──
class _FixedClient:
    """Returns a fixed structured payload for output_config calls; prose otherwise."""
    def __init__(self, structured_text):
        self.calls = []
        self.structured_text = structured_text

    class _Messages:
        def __init__(self, outer):
            self.o = outer

        def create(self, **kw):
            self.o.calls.append(kw)
            if "output_config" in kw:
                return _Msg(self.o.structured_text)
            return _Msg("Prose fallback analysis.")

    @property
    def messages(self):
        return _FixedClient._Messages(self)


def _run_client(single, client):
    sc, sf = ba.client, ba.SINGLE_CALL_FINDINGS
    ba.client, ba.SINGLE_CALL_FINDINGS = client, single
    try:
        return _Agent().analyze({}, SharedMemory())
    finally:
        ba.client, ba.SINGLE_CALL_FINDINGS = sc, sf


def test_single_call_malformed_output_does_not_crash():
    # non-JSON structured output -> generic fallback finding, no exception
    findings = _run_client(True, _FixedClient("this is not json at all <<<"))
    assert len(findings) >= 1 and findings[0].agent == "TestAgent"


def test_single_call_bare_array_shape_parsed():
    arr = json.dumps([{"category": "Ops", "severity": "low", "title": "X", "detail": "d",
                       "financial_impact": "R 1", "recommendation": "do", "roi_estimate": "r",
                       "cost_of_inaction": "c", "benchmark_reference": "b", "data_source": "s",
                       "quick_win": False}])
    findings = _run_client(True, _FixedClient(arr))
    assert len(findings) == 1 and findings[0].category == "Ops"


def test_single_call_skips_non_dict_items():
    mixed = json.dumps({"findings": ["garbage-string", {"category": "Risk", "severity": "high",
                        "title": "Real", "detail": "d", "financial_impact": "R 1",
                        "recommendation": "do", "roi_estimate": "r", "cost_of_inaction": "c",
                        "benchmark_reference": "b", "data_source": "s", "quick_win": True}]})
    findings = _run_client(True, _FixedClient(mixed))
    assert len(findings) == 1 and findings[0].title == "Real"


def test_single_call_empty_findings_falls_back_to_classic():
    # an empty structured array -> fall through to the classic two-call path (safety net)
    c = _FixedClient(json.dumps({"findings": []}))
    _run_client(True, c)
    # 1 structured (empty) + 2 classic (prose + parse) = 3 calls; no crash
    assert len(c.calls) == 3
