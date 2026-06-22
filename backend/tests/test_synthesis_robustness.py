"""Hardening: a non-dict LLM synthesis response must never crash report assembly.
Pressure-test (2026-06-22) found that a model returning a JSON array/string made
synthesis.get(...) raise AttributeError in _generate_executive_summary."""
from agents.ceo_agent import CEOAgent
from memory.shared_memory import SharedMemory


def _synthesise(canned):
    ceo = CEOAgent()
    ceo._call_claude = lambda *a, **k: canned   # stub the LLM call
    return ceo._cross_agent_synthesis(SharedMemory())


def test_non_object_synthesis_is_coerced_to_dict():
    for canned in ("[1,2,3]", '"just a string"', "42", "true", "null", "not json at all"):
        r = _synthesise(canned)
        assert isinstance(r, dict), f"{canned!r} -> {type(r).__name__}"
        r.get("situation", "")   # the consumer call that used to crash must be safe


def test_valid_object_synthesis_is_preserved():
    r = _synthesise('{"situation": "S", "top_priority_issues": [{"x": 1}]}')
    assert isinstance(r, dict) and r.get("situation") == "S" and r.get("top_priority_issues") == [{"x": 1}]
