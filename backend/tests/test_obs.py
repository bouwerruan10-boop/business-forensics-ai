"""Tests for the observability layer (Tier 1.4): structured logging + Sentry init."""
import structlog
from services.obs import configure_logging, get_logger, bind_context, clear_context, init_sentry


def test_configure_is_idempotent():
    configure_logging()
    configure_logging()   # second call must be a safe no-op
    assert get_logger("x") is not None


def test_logger_emits_all_levels_without_error():
    log = get_logger("test")
    log.debug("d"); log.info("i", k=1); log.warning("w"); log.error("e")
    try:
        raise ValueError("boom")
    except Exception:
        log.exception("ex")   # must not raise


def test_bind_and_clear_context():
    clear_context()
    bind_context(analysis_id="abc", request_id="r1")
    ctx = structlog.contextvars.get_contextvars()
    assert ctx.get("analysis_id") == "abc" and ctx.get("request_id") == "r1"
    clear_context()
    assert structlog.contextvars.get_contextvars() == {}


def test_init_sentry_noop_without_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert init_sentry() is False


def test_context_does_not_leak_across_reused_threads():
    """The pipeline binds analysis_id inside a thread-pool task and clears it in a
    finally. A later task on the SAME (reused) thread must NOT inherit it."""
    import asyncio, concurrent.futures, structlog as _sl

    def bound_task(aid):
        clear_context(); bind_context(analysis_id=aid)
        try:
            return dict(_sl.contextvars.get_contextvars())
        finally:
            clear_context()

    def unbound_task():
        return dict(_sl.contextvars.get_contextvars())  # must be clean

    async def run():
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)  # force reuse
        loop = asyncio.get_event_loop()
        a = await loop.run_in_executor(ex, bound_task, "A")
        leaked = await loop.run_in_executor(ex, unbound_task)
        return a, leaked

    bound, leaked = asyncio.run(run())
    assert bound == {"analysis_id": "A"}
    assert leaked == {}      # no leak from the prior bound task
