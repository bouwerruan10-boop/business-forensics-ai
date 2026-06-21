"""Tier 1.3 (T1): base_agent._parse_findings uses native structured outputs with
robust parsing of either the structured {"findings":[...]} shape or a bare array,
and degrades gracefully. No live API."""
import json
import agents.base_agent as ba
from memory.shared_memory import SharedMemory


class _Resp:
    def __init__(self, text):
        self.content = [type("C", (), {"text": text})()]
        self.usage = type("U", (), {"input_tokens": 1, "output_tokens": 1})()


class _Msgs:
    last_kwargs = None
    def __init__(self, text, raise_typeerror=False):
        self._t = text; self._raise = raise_typeerror
    def create(self, **kw):
        _Msgs.last_kwargs = kw
        if self._raise and "output_config" in kw:
            raise TypeError("messages.create() got an unexpected keyword argument 'output_config'")
        return _Resp(self._t)


class _Client:
    def __init__(self, text, raise_typeerror=False):
        self.messages = _Msgs(text, raise_typeerror)


_FINDING = {"category": "Cash", "severity": "high", "title": "X", "detail": "d",
            "financial_impact": "R1", "recommendation": "do", "roi_estimate": "r",
            "cost_of_inaction": "c", "benchmark_reference": "b", "data_source": "s", "quick_win": True}


def _agent():
    a = ba.BaseAgent(); a.name = "TestAgent"; return a


def test_structured_findings_shape_is_parsed(monkeypatch):
    monkeypatch.setattr(ba, "client", _Client(json.dumps({"findings": [_FINDING]})))
    f = _agent()._parse_findings("analysis", SharedMemory())
    assert len(f) == 1 and f[0].severity == "high" and f[0].quick_win is True
    assert "output_config" in _Msgs.last_kwargs   # structured outputs requested


def test_bare_array_shape_is_parsed(monkeypatch):
    monkeypatch.setattr(ba, "client", _Client(json.dumps([_FINDING])))
    f = _agent()._parse_findings("analysis", SharedMemory())
    assert len(f) == 1 and f[0].category == "Cash"


def test_degrades_when_sdk_rejects_output_config(monkeypatch):
    # Old SDK raises TypeError on output_config -> must degrade and still parse.
    monkeypatch.setattr(ba, "client", _Client(json.dumps([_FINDING]), raise_typeerror=True))
    f = _agent()._parse_findings("analysis", SharedMemory())
    assert len(f) == 1 and f[0].title == "X"


def test_unparseable_falls_back_to_single_finding(monkeypatch):
    monkeypatch.setattr(ba, "client", _Client("not json at all"))
    f = _agent()._parse_findings("the raw analysis text", SharedMemory())
    assert len(f) == 1 and f[0].severity == "medium"   # generic fallback preserved
