"""
Authentication / principal abstraction — the seam for future multi-tenancy.

Operator-run today: there is a single principal ("operator"). Endpoints depend on
get_principal() and tag data with principal.id. On the pivot to mass distribution,
get_principal() resolves an API key / JWT to a tenant here — and NO endpoint changes.
"""
from dataclasses import dataclass
from fastapi import Request
from config import DEFAULT_OWNER, MULTI_TENANT


@dataclass
class Principal:
    id: str = DEFAULT_OWNER
    kind: str = "operator"   # operator | tenant | user (future)
    tenant: str = DEFAULT_OWNER


def get_principal(request: Request) -> Principal:
    """Resolve the caller. Today: always the operator. Future (MULTI_TENANT=true):
    resolve request headers (X-API-Key / Authorization) to a tenant Principal."""
    if not MULTI_TENANT:
        return Principal()
    # Future pivot: look up an API key / JWT -> tenant. For now, still operator.
    return Principal()
