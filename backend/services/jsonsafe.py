"""
JSON-safety: strip non-finite floats (NaN / +-inf) from data before it is stored
or serialized.

Root cause of a recurring bug class: any consumer that copies a computed number
(a ratio, a score, a derived figure) into an output could carry a NaN/inf, which
makes json.dumps(allow_nan=False) raise — i.e. the API endpoint 500s or emits
invalid JSON. Rather than finite-guarding every new surface one at a time, we
sanitize once at report assembly AND at the serialization boundary.
"""
import math

__all__ = ["finite_safe"]


def finite_safe(obj):
    """Recursively replace NaN/inf floats with None. Dicts/lists are rebuilt;
    everything else passes through unchanged. Deterministic, no side effects."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: finite_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [finite_safe(v) for v in obj]
    return obj
