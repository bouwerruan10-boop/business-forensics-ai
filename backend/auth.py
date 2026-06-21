"""
Authentication / principal abstraction — the seam for multi-tenancy.

Operator-run today: when OPERATOR_PASSWORD is set, the operator logs in and gets a
short-lived signed bearer token; endpoints depend on get_principal() and tag data
with principal.id. When OPERATOR_PASSWORD is unset, the gate is open (operator) for
backward-compatibility. On the pivot to mass distribution, get_principal() resolves
the token's `sub` to a tenant Principal — and NO endpoint changes.

Token format: a dependency-free JWS-lite — urlsafe-b64(json payload).HMAC-SHA256(payload),
payload = {"sub", "kind", "exp"}. Multi-user later = issue tokens with a tenant `sub`.
"""
import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request

from config import AUTH_ENABLED, AUTH_SECRET, AUTH_TTL_HOURS, DEFAULT_OWNER


@dataclass
class Principal:
    id: str = DEFAULT_OWNER
    kind: str = "operator"   # operator | tenant | user (future)
    tenant: str = DEFAULT_OWNER


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign(body: str) -> str:
    return _b64e(hmac.new(AUTH_SECRET.encode(), body.encode(), hashlib.sha256).digest())


def issue_token(sub: str = DEFAULT_OWNER, kind: str = "operator", ttl_hours: int | None = None) -> str:
    ttl = (ttl_hours or AUTH_TTL_HOURS) * 3600
    payload = {"sub": sub, "kind": kind, "exp": int(time.time()) + ttl}
    body = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    return body + "." + _sign(body)


def verify_token(token: str):
    """Return the payload dict if the token is valid + unexpired, else None."""
    if not token or "." not in token or not AUTH_SECRET:
        return None
    body, _, sig = token.partition(".")
    if not hmac.compare_digest(sig, _sign(body)):
        return None
    try:
        payload = json.loads(_b64d(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def _bearer(request: Request) -> str:
    h = request.headers.get("Authorization", "")
    return h[7:] if h.lower().startswith("bearer ") else ""


def get_principal(request: Request) -> Principal:
    """Resolve the caller. When AUTH_ENABLED, require a valid operator bearer token;
    otherwise open (operator), backward-compatible. The pivot resolves `sub` to a tenant."""
    if not AUTH_ENABLED:
        return Principal()
    payload = verify_token(_bearer(request))
    if not payload:
        raise HTTPException(status_code=401, detail="Authentication required")
    sub = payload.get("sub", DEFAULT_OWNER)
    return Principal(id=sub, kind=payload.get("kind", "operator"), tenant=sub)
