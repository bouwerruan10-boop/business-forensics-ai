"""
obs.py - structured logging + error tracking (Tier 1.4).

Replaces ad-hoc print() with structured logging (structlog routed THROUGH stdlib,
so uvicorn's own logs share the format) and wires optional Sentry error tracking.
Every log line emitted inside an analysis or request context carries the
correlation id (analysis_id / request_id) via structlog.contextvars, so one
analysis can be traced end-to-end. "You can't fix what you can't see."

Scope (honest): structured logs to stdout (Railway already centralises stdout) +
Sentry's free tier. Heavy log aggregation (ELK / Loki / Datadog) is deferred to
Tier 2. Both halves are opt-in / no-op-safe: logging always works; Sentry
activates only when SENTRY_DSN is set, and is a no-op if the SDK is absent.
"""
import logging
import os
import sys

import structlog

_CONFIGURED = False


def configure_logging():
    """Idempotent. JSON in prod (or LOG_FORMAT=json); human console on a TTY."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    as_json = os.getenv("LOG_FORMAT", "").lower() == "json" or not sys.stderr.isatty()

    pre_chain = [
        structlog.contextvars.merge_contextvars,     # inject bound analysis_id / request_id
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    renderer = (structlog.processors.JSONRenderer() if as_json
                else structlog.dev.ConsoleRenderer(colors=False))

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=pre_chain,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            renderer,
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)

    structlog.configure(
        processors=pre_chain + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True


def get_logger(name=None):
    if not _CONFIGURED:
        configure_logging()
    return structlog.get_logger(name)


def bind_context(**kwargs):
    """Bind correlation keys (analysis_id, request_id, ...) onto every subsequent
    log line in this execution context."""
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context():
    structlog.contextvars.clear_contextvars()


def init_sentry():
    """Activate Sentry IF SENTRY_DSN is set. No-op otherwise / if SDK missing.
    Returns True when activated."""
    dsn = os.getenv("SENTRY_DSN", "")
    if not dsn:
        return False
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("SENTRY_ENV", os.getenv("RAILWAY_ENVIRONMENT", "production")),
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
            send_default_pii=False,
            # Imara processes confidential SME financial documents (POPIA). Never let
            # Sentry capture request/response bodies — only the exception + stack.
            max_request_body_size="never",
        )
        return True
    except Exception:
        return False
