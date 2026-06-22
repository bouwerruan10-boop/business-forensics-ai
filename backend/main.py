"""
Imara -- FastAPI backend
Endpoints:
  POST /api/analyze         -- upload files + business profile, trigger full analysis
  GET  /api/status/{id}     -- poll analysis progress
  GET  /api/report/{id}     -- get full JSON report
  GET  /api/report/{id}/pdf -- download premium PDF report
  GET  /api/admin/analyses  -- admin: list all analyses
  GET  /api/health          -- health check

Rate limiting: 3 analyses per hour per IP (configurable via RATE_LIMIT env var).
API key gate: set API_SECRET_KEY in .env to require X-API-Key header on /api/analyze.
"""
import os
import uuid
import asyncio
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from services.file_parser import parse_file, merge_parsed_data
from services.report_generator import generate_pdf_report
from services.html_report import generate_html_report
from services.database import (
    init_db, create_analysis, save_report, save_error,
    get_report, list_analyses, count_analyses, delete_analysis,
    get_analysis as db_get_analysis, mark_interrupted_analyses,
    create_share, resolve_share, revoke_share,
)
from agents.ceo_agent import CEOAgent
from memory.shared_memory import SharedMemory
from auth import get_principal, Principal
from config import PUBLIC_API, API_VERSION, EXPOSE_DOCS
from services.score_contract import score_contract, usage_summary
from services.jsonsafe import finite_safe

# -- Rate limiter setup -------------------------------------------
# Configurable via RATE_LIMIT env var, default: 3 per hour
RATE_LIMIT = os.getenv("RATE_LIMIT", "3/hour")
# Ask Imara is an open LLM endpoint (cost/abuse vector) -> its own per-IP limit.
ASK_RATE_LIMIT = os.getenv("ASK_RATE_LIMIT", "20/hour")


def client_ip(request: Request) -> str:
    """Real client IP for rate limiting.

    Behind Railway's edge proxy the raw socket address (what
    get_remote_address sees) is the proxy connection, not the caller -- so
    per-IP limits never key on the actual user and silently never trip. The
    true client IP is the first hop in X-Forwarded-For. Fall back to the
    socket address for local/dev where no proxy header is present.
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip, default_limits=[RATE_LIMIT])

# -- Optional API key gate ----------------------------------------
# Set API_SECRET_KEY in your .env to enable. Leave blank to disable.
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")


def verify_api_key(request: Request):
    """Dependency: enforce API key if API_SECRET_KEY is configured."""
    if not API_SECRET_KEY:
        return  # gate disabled
    provided = request.headers.get("X-API-Key", "")
    import hmac as _hmac
    if not _hmac.compare_digest(provided, API_SECRET_KEY):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Provide it in the X-API-Key header.",
        )

# -- Optional admin gate (separate key for /api/admin/*) -----------
# Set ADMIN_API_KEY in the backend env to lock the admin endpoints. Opt-in:
# if unset, the gate stays open (no behaviour change until you set the key).
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")


def verify_admin_key(request: Request):
    """Dependency: protect /api/admin/* when ADMIN_API_KEY is configured."""
    if not ADMIN_API_KEY:
        return  # gate disabled
    provided = request.headers.get("X-Admin-Key", "")
    import hmac as _hmac
    if not _hmac.compare_digest(provided, ADMIN_API_KEY):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing admin key. Provide it in the X-Admin-Key header.",
        )


class SafeJSONResponse(JSONResponse):
    """Default JSON response: strips NaN/inf so no endpoint can ever emit invalid
    JSON or 500 on a non-finite number — the root-cause guard for that bug class."""
    def render(self, content) -> bytes:
        import json as _json
        return _json.dumps(finite_safe(content), ensure_ascii=False, allow_nan=False,
                           separators=(",", ":")).encode("utf-8")


app = FastAPI(
    title="Imara",
    description="AI-powered multi-agent business consulting platform",
    version="2.1.0",
    default_response_class=SafeJSONResponse,
    # Hide the OpenAPI schema + Swagger/ReDoc in production (enumeration surface);
    # EXPOSE_DOCS=true re-enables them in dev.
    docs_url="/docs" if EXPOSE_DOCS else None,
    redoc_url="/redoc" if EXPOSE_DOCS else None,
    openapi_url="/openapi.json" if EXPOSE_DOCS else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Observability (Tier 1.4): structured logging + optional Sentry ──
from services.obs import configure_logging, get_logger, init_sentry, bind_context, clear_context
configure_logging()
log = get_logger("imara.api")


@app.middleware("http")
async def _request_logging(request: Request, call_next):
    import uuid as _uuid, time as _t
    rid = request.headers.get("X-Request-ID") or _uuid.uuid4().hex[:12]
    bind_context(request_id=rid)
    started = _t.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("request_error", method=request.method, path=request.url.path)
        clear_context()
        raise
    response.headers["X-Request-ID"] = rid
    log.info("request", method=request.method, path=request.url.path,
             status=response.status_code, ms=round((_t.perf_counter() - started) * 1000))
    clear_context()
    return response



@app.on_event("startup")
def on_startup():
    init_db()
    if init_sentry():
        log.info("sentry_enabled")
    _interrupted = mark_interrupted_analyses()
    if _interrupted:
        log.info("interrupted_analyses_flagged", count=_interrupted)
    _start_backup_scheduler()
    _start_retention_scheduler()


def _start_backup_scheduler():
    """Daemon thread: periodic consistent DB snapshots + rotation. Opt-in via
    BACKUP_ENABLED (default off, backward-compatible). Runs one snapshot at
    startup, then every BACKUP_INTERVAL_HOURS."""
    import config as _cfg
    if not _cfg.BACKUP_ENABLED:
        return
    import threading, time
    from services.backup import create_backup, prune_backups

    def _loop():
        while True:
            try:
                snap = create_backup()
                prune_backups(_cfg.BACKUP_KEEP)
                log.info("backup_snapshot", file=snap.name)
            except Exception as exc:
                log.error("backup_failed", error=str(exc))
            time.sleep(max(1, _cfg.BACKUP_INTERVAL_HOURS) * 3600)

    threading.Thread(target=_loop, daemon=True, name="backup-scheduler").start()
    log.info("backup_scheduler_started", interval_hours=_cfg.BACKUP_INTERVAL_HOURS, keep=_cfg.BACKUP_KEEP)


def _start_retention_scheduler():
    """Daemon: POPIA s14 retention. Opt-in via RETENTION_ENABLED (default off).
    Deletes analyses older than RETENTION_DAYS - one pass at startup, then daily."""
    import config as _cfg
    if not _cfg.RETENTION_ENABLED:
        return
    import threading, time
    from services.database import purge_old_analyses

    def _loop():
        while True:
            try:
                res = purge_old_analyses(_cfg.RETENTION_DAYS)
                if res["deleted"]:
                    log.info("retention_purge", deleted=res["deleted"], cutoff=res["cutoff"])
            except Exception as exc:
                log.error("retention_purge_failed", error=str(exc))
            time.sleep(24 * 3600)

    threading.Thread(target=_loop, daemon=True, name="retention-scheduler").start()
    log.info("retention_scheduler_started", retention_days=_cfg.RETENTION_DAYS)


# CORS — restrict to the Vercel frontend (+ preview deploys) and local dev,
# instead of a wildcard. Override with CORS_ORIGINS (comma-separated) for custom domains.
# Note: "*" with allow_credentials=True is rejected by browsers anyway.
_default_origins = (
    "https://business-forensics-ai.vercel.app,"
    "http://localhost:3000,http://localhost:5173"
)
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", _default_origins).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # Only THIS project's Vercel preview deploys, not any *.vercel.app site.
    allow_origin_regex=r"https://business-forensics-ai-[a-z0-9-]+\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _security_headers(request, call_next):
    """Baseline OWASP secure-headers on every response. CSP is intentionally left to the
    frontend/Vercel: the self-contained HTML report uses inline styles, so a strict backend
    CSP would break it."""
    response = await call_next(request)
    h = response.headers
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("X-Frame-Options", "DENY")
    h.setdefault("Referrer-Policy", "no-referrer")
    h.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
    h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    # no-store: this API serves live + sensitive (client financial) data. Stops intermediaries/
    # CDNs caching responses — fixes the stale /api/health + /openapi.json seen behind the edge,
    # and prevents client reports being cached downstream.
    h.setdefault("Cache-Control", "no-store")
    return response

# In-memory store for active sessions -- SQLite is the durable store
analyses: dict = {}
analysis_status: dict = {}


# -- Pydantic models -----------------------------------------------

class ActionSimRequest(BaseModel):
    analysis_id: str
    actions: list = []
    scenario: str = "expected"
    variable: str | None = None   # vestigial — unused by /simulate/actions & /montecarlo; optional so the frontend (which omits it) doesn't 422

class AskRequest(BaseModel):
    analysis_id: str
    question: str = ""


class OutcomeIn(BaseModel):
    analysis_id: str
    outcome_type: str          # default|repaid|funded|declined|external_score
    label: int | None = None   # 1=bad/default, 0=good (when applicable)
    value: float | None = None # numeric (e.g. external bureau score)
    note: str = ""
    source: str = ""


# -- Routes --------------------------------------------------------

class LoginRequest(BaseModel):
    password: str = ""


@app.post("/api/login")
def login(req: LoginRequest):
    """Operator login. With OPERATOR_PASSWORD set, exchange it for a bearer token;
    unset = open (dev/operator), reports auth is not required."""
    from config import AUTH_ENABLED, OPERATOR_PASSWORD
    if not AUTH_ENABLED:
        return {"auth_required": False}
    import hmac as _hmac
    # strip both sides (a trailing newline/space in the host env var or the typed value is the
    # usual cause of a false "Invalid password"); compare as bytes so non-ASCII passwords work.
    submitted = (req.password or "").strip()
    if not OPERATOR_PASSWORD or not _hmac.compare_digest(submitted.encode("utf-8"), OPERATOR_PASSWORD.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid password")
    from auth import issue_token
    return {"token": issue_token(), "token_type": "bearer", "auth_required": True}


_AUTH_GATED_PREFIXES = ("/api/report/", "/api/analyze", "/api/status/", "/api/simulate")


def _auth_path_public(path: str) -> bool:
    if path in ("/api/login", "/api/health", "/openapi.json", "/docs", "/redoc"):
        return True
    if path.startswith(("/api/shared/", "/api/admin/", "/api/v1/")):
        return True
    parts = path.split("/")   # /api/report/demo-001[/...] -> the public demo only
    if len(parts) >= 4 and parts[1] == "api" and parts[2] == "report" and parts[3] == "demo-001":
        return True
    return False


@app.middleware("http")
async def _operator_gate(request: Request, call_next):
    """Gate the report/analyze/status surface behind the operator token when
    OPERATOR_PASSWORD is set. Public share links, the demo, admin (own key), /v1 and
    health stay open. No-op when auth is disabled (dev/test)."""
    # CORS preflight (OPTIONS) carries no Authorization header by design. Never gate it,
    # or the browser preflight 401s and the real (token-bearing) request never fires.
    if request.method == "OPTIONS":
        return await call_next(request)
    from config import AUTH_ENABLED
    if AUTH_ENABLED:
        path = request.url.path
        if any(path.startswith(p) for p in _AUTH_GATED_PREFIXES) and not _auth_path_public(path):
            from auth import verify_token
            h = request.headers.get("Authorization", "")
            tok = h[7:] if h.lower().startswith("bearer ") else ""
            if not verify_token(tok):
                return SafeJSONResponse({"detail": "Authentication required"}, status_code=401)
    return await call_next(request)


@app.get("/api/health")
def health():
    # RAILWAY_GIT_COMMIT_SHA is injected by Railway at build time; "dev" locally.
    from config import AUTH_ENABLED
    return {
        "status": "ok",
        "service": "Imara v2.0",
        "commit": os.getenv("RAILWAY_GIT_COMMIT_SHA", "dev")[:8],
        "auth_required": AUTH_ENABLED,
    }


MAX_UPLOAD_FILES = 40   # generous for the 6 upload zones; bounds memory/time on abusive requests
MAX_UPLOAD_FILE_BYTES = 25 * 1024 * 1024     # per-file cap (aligns with the parser's content cap)
MAX_UPLOAD_TOTAL_BYTES = 150 * 1024 * 1024   # aggregate cap across all files in one request
ANALYSIS_TIMEOUT_SECONDS = int(os.getenv("ANALYSIS_TIMEOUT_SECONDS", "1800"))  # wall-clock cap on a single run


def _coerce_categories(raw_json, n):
    """Turn the file_categories form field into EXACTLY n category strings.
    Tolerates malformed JSON, non-list values, wrong lengths, and non-string elements
    (anything unexpected -> 'general'), so a bad client payload can never crash the upload
    or the routing membership test."""
    import json as _json
    try:
        cats = _json.loads(raw_json or "[]")
    except Exception:
        cats = []
    if not isinstance(cats, list):
        cats = []
    out = []
    for i in range(n):
        c = cats[i] if i < len(cats) else "general"
        out.append(c if isinstance(c, str) else "general")
    return out


@app.post("/api/analyze")
@limiter.limit(RATE_LIMIT)
async def analyze(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    company_name: Optional[str] = Form(None),
    industry_key: Optional[str] = Form(None),
    annual_revenue: Optional[float] = Form(None),
    headcount: Optional[int] = Form(None),
    currency: Optional[str] = Form("ZAR"),
    country: Optional[str] = Form(""),
    primary_concern: Optional[str] = Form(None),
    # SA-specific intake fields
    entity_type: Optional[str] = Form(""),
    cipc_number: Optional[str] = Form(""),
    vat_registered: Optional[str] = Form("unknown"),
    vat_number: Optional[str] = Form(""),
    tax_year_end: Optional[str] = Form(""),
    years_in_business: Optional[str] = Form(""),
    bbbee_level: Optional[str] = Form(""),
    banking_partner: Optional[str] = Form(""),
    report_audience: Optional[str] = Form("owner"),
    # POPIA consent capture (intake gate)
    consent: Optional[str] = Form(None),
    consent_at: Optional[str] = Form(None),
    # File category labels — JSON array matching files[] order
    # e.g. '["financial","bank","tax"]'
    file_categories: Optional[str] = Form("[]"),
    _api_key: None = Depends(verify_api_key),
    principal: Principal = Depends(get_principal),
):
    """Accept files + business profile. Returns analysis_id to poll."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    if len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(status_code=400,
                            detail="Too many files ({}); max {} per analysis.".format(len(files), MAX_UPLOAD_FILES))

    # Parse file category labels (robust to malformed / non-list / wrong-length / non-string payloads)
    categories = _coerce_categories(file_categories, len(files))

    analysis_id = str(uuid.uuid4())
    # Bound the in-memory status dict so a long-running server can't leak memory
    # (entries persist after completion); evict the oldest once it grows large.
    if len(analysis_status) > 1000:
        for _old in list(analysis_status)[:200]:
            analysis_status.pop(_old, None)
    analysis_status[analysis_id] = {
        "status": "processing",
        "progress": [],
        "current_agent": "Parsing uploaded files...",
        "message": "Reading and classifying your business data...",
    }

    # POPIA: record that the user affirmed they have the right to upload this data
    # and consented to processing (auditable in the structured logs).
    _consented = str(consent).lower() in ("true", "1", "yes", "on")
    log.info("consent_recorded", analysis_id=analysis_id,
             consented=_consented, consent_at=consent_at or "")
    import config as _cfg
    if getattr(_cfg, "REQUIRE_CONSENT", False) and not _consented:
        analysis_status.pop(analysis_id, None)
        raise HTTPException(status_code=400,
                            detail="Consent is required: confirm you have the right to upload this data and consent to processing.")

    # Read file bytes immediately -- can't read in background task.
    # Validate per-file (empty / oversize) and aggregate size at the door so a
    # pathological upload can't exhaust memory or hang the parser.
    file_data = []
    _total = 0
    for i, f in enumerate(files):
        content = await f.read()
        if not content:
            analysis_status.pop(analysis_id, None)
            raise HTTPException(status_code=400, detail="File '{}' is empty.".format(f.filename or "?"))
        if len(content) > MAX_UPLOAD_FILE_BYTES:
            analysis_status.pop(analysis_id, None)
            raise HTTPException(status_code=413, detail="File '{}' exceeds the {}MB per-file limit.".format(
                f.filename or "?", MAX_UPLOAD_FILE_BYTES // (1024 * 1024)))
        _total += len(content)
        if _total > MAX_UPLOAD_TOTAL_BYTES:
            analysis_status.pop(analysis_id, None)
            raise HTTPException(status_code=413, detail="Total upload exceeds the {}MB limit.".format(
                MAX_UPLOAD_TOTAL_BYTES // (1024 * 1024)))
        file_data.append({
            "filename": f.filename,
            "content": content,
            "category": categories[i],
        })

    profile = {
        "company_name": company_name or "Unknown Business",
        "industry_key": industry_key or "general",
        "annual_revenue": annual_revenue or 0.0,
        "headcount": headcount or 0,
        "currency": currency or "ZAR",
        "country": country or "",
        "primary_concern": primary_concern or "",
        "consent_at": consent_at or "",
        # SA-specific
        "entity_type": entity_type or "",
        "cipc_number": cipc_number or "",
        "vat_registered": vat_registered or "unknown",
        "vat_number": vat_number or "",
        "tax_year_end": tax_year_end or "",
        "years_in_business": years_in_business or "",
        "bbbee_level": bbbee_level or "",
        "banking_partner": banking_partner or "",
        "report_audience": report_audience or "owner",
    }

    # Persist the new analysis record immediately
    create_analysis(analysis_id, profile, file_count=len(file_data), owner=principal.id)

    background_tasks.add_task(_run_analysis, analysis_id, file_data, profile)
    return {"analysis_id": analysis_id, "message": "Analysis started"}


@app.get("/api/status/{analysis_id}")
def get_status(analysis_id: str):
    status = analysis_status.get(analysis_id)
    if status:
        return status
    # Fall back to SQLite so status survives a server restart (in-memory dict is volatile).
    row = db_get_analysis(analysis_id)
    if row:
        st = row.get("status", "unknown")
        return {
            "analysis_id": analysis_id,
            "status": st,
            "current_agent": "Analysis complete" if st == "complete" else ("Error" if st == "error" else "Processing"),
            "message": row.get("error") or "",
            "error": row.get("error"),
            "progress": [],
        }
    raise HTTPException(status_code=404, detail="Analysis not found")


@app.get("/api/report/{analysis_id}")
def get_report_endpoint(analysis_id: str):
    # Check in-memory first (fastest for recent analyses)
    result = analyses.get(analysis_id)
    if result:
        return result
    # Fall back to SQLite (survives server restart)
    result = get_report(analysis_id)
    if result:
        analyses[analysis_id] = result  # warm the cache
        return result
    status = analysis_status.get(analysis_id, {})
    if status.get("status") == "processing":
        raise HTTPException(status_code=202, detail="Analysis still in progress")
    raise HTTPException(status_code=404, detail="Analysis not found")


@app.post("/api/report/{analysis_id}/share")
def create_report_share(analysis_id: str, expires_in_days: int = 0, principal: Principal = Depends(get_principal)):
    """Create a public, optionally-expiring share link for a report."""
    if not db_get_analysis(analysis_id):
        raise HTTPException(status_code=404, detail="Analysis not found")
    expires_at = None
    if expires_in_days and expires_in_days > 0:
        from datetime import datetime, timezone, timedelta
        expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_in_days)).isoformat()
    token = create_share(analysis_id, expires_at, owner=principal.id)
    return {"token": token, "expires_at": expires_at}


@app.get("/api/shared/{token}")
def get_shared_report(token: str):
    """Public report fetch via a share token — 410 if expired or revoked."""
    analysis_id = resolve_share(token)
    if not analysis_id:
        raise HTTPException(status_code=410, detail="This shared link has expired or been revoked.")
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Report not available")
    return result


@app.post("/api/admin/shares/{token}/revoke")
def admin_revoke_share(token: str, _admin: None = Depends(verify_admin_key)):
    """Revoke a share token so its public link stops working."""
    if not revoke_share(token):
        raise HTTPException(status_code=404, detail="Share not found")
    return {"revoked": True}


@app.get("/api/report/{analysis_id}/pdf")
def get_pdf(analysis_id: str, audience: str = "owner"):
    """
    Download premium PDF report.
    ?audience=owner   — plain-language, action-focused (default)
    ?audience=banker  — credit/risk focus for lenders
    ?audience=investor — valuation and growth story
    """
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found or still processing")
    audience = audience.lower() if audience in ("owner", "banker", "investor") else "owner"
    pdf_bytes = generate_pdf_report(result, audience=audience)
    biz_name = result.get("business_name", "report").replace(" ", "_")
    suffix = f"_{audience}" if audience != "owner" else ""
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{biz_name}_forensics{suffix}.pdf"'
        },
    )


@app.get("/api/report/{analysis_id}/html")
def get_html_report(analysis_id: str):
    """Download self-contained interactive HTML report."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found or still processing")
    html_str = generate_html_report(result)
    biz_name = result.get("business_name", "report").replace(" ", "_")
    return Response(
        content=html_str.encode("utf-8"),
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="{biz_name}_interactive_report.html"'
        },
    )


@app.get("/api/report/{analysis_id}/credit")
def get_credit_summary(analysis_id: str):
    """Return structured credit readiness data for the frontend credit panel."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found or still processing")
    return {
        "credit_score":     result.get("credit_score", 0),
        "credit_grade":     result.get("credit_grade", ""),
        "credit_barriers":  result.get("credit_barriers", []),
        "credit_strengths": result.get("credit_strengths", []),
        "credit_products":  result.get("credit_products", []),
        "fraud_risk_level": result.get("fraud_risk_level", "unknown"),
        "fraud_risk_score": result.get("fraud_risk_score", 0),
        "fraud_indicators": result.get("fraud_indicators", []),
        "valuation_low":    result.get("valuation_low", 0),
        "valuation_mid":    result.get("valuation_mid", 0),
        "valuation_high":   result.get("valuation_high", 0),
        "valuation_method": result.get("valuation_method", ""),
        "forecast_base_12m": result.get("forecast_base_12m", 0),
        "forecast_bull_12m": result.get("forecast_bull_12m", 0),
        "forecast_bear_12m": result.get("forecast_bear_12m", 0),
        "forecast_assumptions": result.get("forecast_assumptions", []),
        "currency": result.get("currency", "ZAR"),
    }


@app.get("/api/report/{analysis_id}/actions")
def list_simulation_actions(analysis_id: str):
    """Candidate improvement actions derived from this report's ratios vs sector."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    from services.simulation import derive_actions
    return {"actions": derive_actions(result)}


@app.post("/api/simulate/actions")
def simulate_actions(req: ActionSimRequest):
    """Project the outcome of taking the selected actions (deterministic model)."""
    result = analyses.get(req.analysis_id) or get_report(req.analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    from services.simulation import apply_actions
    return apply_actions(result, req.actions, req.scenario)


@app.get("/api/report/{analysis_id}/levers")
def report_levers(analysis_id: str, scenario: str = "expected"):
    """Sensitivity ranking — each action's standalone impact (the biggest levers)."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    from services.simulation import rank_levers
    return {"levers": rank_levers(result, scenario)}


@app.get("/api/report/{analysis_id}/optimize")
def report_optimize(analysis_id: str, scenario: str = "expected",
                    max_actions: int = 3, objective: str = "imara"):
    """Best BUNDLE of actions under an action-count budget (exhaustive, deterministic).
    objective: imara | profit | cash."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    from services.simulation import optimize_actions
    return optimize_actions(result, scenario=scenario, max_actions=max_actions, objective=objective)


@app.get("/api/report/{analysis_id}/macro")
def report_macro(analysis_id: str):
    """Macro-economic overlay: the firm's bottom-up macro sensitivity + a
    probability-weighted macro stress test (economics agent x simulator)."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    from services.macro_data import firm_macro_sensitivity, SA_MACRO
    from services.simulation import macro_stress_test
    return {
        "snapshot": SA_MACRO,
        "sensitivity": firm_macro_sensitivity(result),
        "stress_test": macro_stress_test(result),
    }


@app.get("/api/report/{analysis_id}/reasons")
def report_reasons(analysis_id: str):
    """Imara Score reason codes: the principal factors affecting the score,
    ordered by impact, derived deterministically from the score components."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    from services.reason_codes import reason_codes
    return reason_codes(result)


@app.post("/api/report/{analysis_id}/ask")
@limiter.limit(ASK_RATE_LIMIT)
def report_ask(request: Request, analysis_id: str, body: AskRequest,
               _api_key: None = Depends(verify_api_key)):
    """Ask Imara: a grounded Q&A over an already-produced analysis. Explains the
    deterministic facts in the report; never invents numbers; defers what-ifs to
    the Action Simulator. Cheap (Haiku) and decision-support only.
    Per-IP rate-limited (ASK_RATE_LIMIT, default 20/hour) and behind the optional
    API-key gate (active only when API_SECRET_KEY is set) - it is an open LLM endpoint."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    from services.ask import answer_question
    return answer_question(result, body.question)


@app.get("/api/report/{analysis_id}/distress")
def report_distress(analysis_id: str):
    """Altman Z''-score (emerging markets) — an independent, published distress
    model used as an external convergent-validity cross-check on the Imara Score."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    from services.distress_score import altman_z_em
    return result.get("distress_score") or altman_z_em(result.get("financial_figures") or {}, result.get("imara_band", ""))


@app.get("/api/report/{analysis_id}/cashflow")
def report_cashflow(analysis_id: str):
    """Deterministic 13-week direct-method cash-flow projection - the short-term
    liquidity horizon that complements the 12-month strategic scenarios."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    from services.cashflow_13week import from_report as cashflow_from_report
    return result.get("cashflow_13week") or cashflow_from_report(result, None)


@app.get("/api/report/{analysis_id}/consistency")
def report_consistency(analysis_id: str):
    """Deterministic cross-agent corroboration - which issues multiple independent
    specialist agents flagged (a confidence signal), and where they diverge."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    from services.agent_consistency import analyze_consistency
    return result.get("cross_agent_consistency") or analyze_consistency(result.get("all_findings_ranked") or [])


@app.get("/api/report/{analysis_id}/bank-signals")
def report_bank_signals(analysis_id: str):
    """Deterministic bank-statement cash-flow signals (bounced debit orders, overdraft,
    cash-flow direction, cadence) — decision-support evidence, not an Imara Score input."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return result.get("bank_signals") or {"available": False, "reason": "Not computed for this analysis."}


@app.get("/api/report/{analysis_id}/normalization")
def report_normalization(analysis_id: str):
    """Indicative Adjusted EBITDA / owner add-backs + SA loan-account flag — the
    tax-books vs deal/loan-books view. Decision-support, not an Imara Score input."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return result.get("normalization") or {"available": False, "reason": "Not computed for this analysis."}


@app.get("/api/report/{analysis_id}/lender-view")
def report_lender_view(analysis_id: str):
    """The lender's-eye view: bank-vs-financials reconciliation, cash-flow conduct,
    indicative borrowing capacity and a decline-risk readout with fixes. Deterministic
    decision-support — NOT a credit decision and NOT an Imara Score input."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return result.get("lender_view") or {"available": False, "reason": "Not computed for this analysis."}


@app.get("/api/report/{analysis_id}/funding-fit")
def report_funding_fit(analysis_id: str):
    """Funding-Fit / which-path: maps the firm to the funding ARCHETYPES that fit, with the
    reasons, what is still needed, and a strengthen-first gate. Objective info on funding TYPES
    (FAIS s1(3)(a)) — not a product recommendation, not a credit decision, not a Score input."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if result.get("funding_fit"):
        return result["funding_fit"]
    from services.funding_fit import recommend_funding
    return recommend_funding(result)


@app.get("/api/report/{analysis_id}/audit")
def report_audit(analysis_id: str):
    """The decision audit record(s) for this analysis: how the score was produced —
    input/figures hashes, model + engine versions, timestamp, tamper-evident hash.
    Governance evidence (EU AI Act / SA COFI direction); raw documents are never stored."""
    from services.database import get_audit
    try:
        rows = get_audit(analysis_id)
    except Exception:
        rows = []
    if rows:
        return {"available": True, "records": rows}
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    a = result.get("audit")
    return {"available": bool(a), "records": ([a] if a else [])}


@app.get("/api/admin/audit")
def admin_audit(limit: int = 100, _admin: None = Depends(verify_admin_key)):
    """Admin: recent decision audit records + a tamper-evidence check of the hash chain."""
    from services.database import list_audit, verify_audit_chain
    try:
        return {"chain": verify_audit_chain(), "records": list_audit(limit)}
    except Exception as _e:
        return {"chain": {"intact": None, "error": str(_e)}, "records": []}


@app.get("/api/report/{analysis_id}/bank-ready-pack")
def report_bank_ready_pack(analysis_id: str):
    """Bank-Ready Pack — a deterministic, lender-facing PDF bundling normalised earnings
    (Adjusted EBITDA + owner add-backs), bank-conduct evidence + reconciliation, indicative
    affordability and the readiness fixes — the bundle SA banks ask self-employed applicants
    for. Decision-support to get application-ready; not a credit decision."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    from services.bank_ready_pack import generate_bank_ready_pack
    pdf_bytes = generate_bank_ready_pack(result)
    biz = (result.get("business_name") or "business").replace(" ", "_")
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="%s_Bank_Ready_Pack.pdf"' % biz})


@app.get("/api/report/{analysis_id}/supplier-savings")
def report_supplier_savings(analysis_id: str, live: bool = False):
    """Supplier benchmarking — per-line-item spend-vs-benchmark + lower-cost-supplier
    opportunities with indicative savings. Decision-support, not an Imara Score input.
    ?live=true augments with Bright Data cited pricing when that seam is enabled."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    sb = result.get("supplier_benchmark") or {"available": False, "reason": "Not computed for this analysis."}
    if live and sb.get("available"):
        from services.supplier_live import augment
        sb = augment(dict(sb))
    return sb


@app.post("/api/simulate/montecarlo")
def simulate_montecarlo(req: ActionSimRequest):
    """Probabilistic outcome distribution + probability of reaching the next band."""
    result = analyses.get(req.analysis_id) or get_report(req.analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    from services.simulation import monte_carlo
    return monte_carlo(result, req.actions)


@app.get("/api/v1/model-card")
def public_model_card():
    """Imara Score model card (governance \"nutrition label\"): intended use, method,
    AHP weight derivation, eval baselines, fairness stance, limitations, NCA/POPIA framing.
    Also surfaces the live Z-double-prime proxy discrimination when enough analyses exist."""
    from services.model_card import model_card
    card = model_card()
    try:
        from services.database import recent_reports
        from services.validation import zscore_proxy_backtest
        zp = zscore_proxy_backtest(recent_reports(200))
        if zp.get("available"):
            card["evaluation"]["live_zscore_discrimination"] = {
                "auc": zp.get("auc"), "gini": zp.get("gini"), "n": zp.get("n"),
                "basis": "Altman Z-double-prime distress-zone proxy over recent analyses (not real outcomes)"}
    except Exception:
        pass
    return card


@app.get("/api/v1/score/{analysis_id}")
def public_score(analysis_id: str):
    """Stable, versioned Imara Score contract for external (B2B) consumers.
    Dormant until PUBLIC_API=true (operator-run today)."""
    if not PUBLIC_API:
        raise HTTPException(status_code=404, detail="Public API is not enabled.")
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return score_contract(result, analysis_id)


@app.get("/api/report/{analysis_id}/usage")
def report_usage(analysis_id: str):
    """Per-analysis usage summary (metering-ready)."""
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return usage_summary(result)


@app.get("/api/v1/health")
def health_v1():
    return {"status": "ok", "api_version": API_VERSION}


# -- Admin endpoints -----------------------------------------------

@app.post("/api/admin/backup")
def admin_create_backup(_admin: None = Depends(verify_admin_key)):
    """Trigger a consistent DB snapshot now + rotate. Returns the new snapshot list."""
    import config as _cfg
    from services.backup import create_backup, prune_backups, list_backups
    snap = create_backup()
    prune_backups(_cfg.BACKUP_KEEP)
    return {"ok": True, "created": snap.name, "backups": list_backups()}


@app.get("/api/admin/backups")
def admin_list_backups(_admin: None = Depends(verify_admin_key)):
    """List existing DB snapshots (newest first)."""
    from services.backup import list_backups
    return {"backups": list_backups()}


@app.get("/api/admin/retention")
def admin_retention_preview(_admin: None = Depends(verify_admin_key)):
    """Preview the POPIA-retention purge (dry run): how many analyses are past RETENTION_DAYS."""
    import config as _cfg
    from services.database import purge_old_analyses
    res = purge_old_analyses(_cfg.RETENTION_DAYS, dry_run=True)
    res["retention_days"] = _cfg.RETENTION_DAYS
    res["enabled"] = _cfg.RETENTION_ENABLED
    return res


@app.post("/api/admin/retention/purge")
def admin_retention_purge(_admin: None = Depends(verify_admin_key)):
    """Run the POPIA-retention purge now (deletes analyses older than RETENTION_DAYS)."""
    import config as _cfg
    from services.database import purge_old_analyses
    res = purge_old_analyses(_cfg.RETENTION_DAYS)
    log.info("retention_purge_manual", **res)
    return res


@app.get("/api/admin/analyses")
def admin_list_analyses(limit: int = 50, offset: int = 0, _admin: None = Depends(verify_admin_key)):
    """List all historical analyses. Returns metadata only (no report blob)."""
    rows = list_analyses(limit=limit, offset=offset)
    totals = {
        "total": count_analyses(),
        "complete": count_analyses("complete"),
        "processing": count_analyses("processing"),
        "error": count_analyses("error"),
    }
    return {"analyses": rows, "totals": totals}


@app.get("/api/admin/fleet-quality")
def admin_fleet_quality(limit: int = 50, recent_window: int = 8, _admin: None = Depends(verify_admin_key)):
    """ONLINE quality monitor: aggregate per-run quality signals across recent
    analyses + drift alerts (recent window vs baseline). Complements offline evals."""
    from services.database import recent_reports
    from services.fleet_quality import extract_metrics, aggregate
    recs = recent_reports(limit)
    records = [{"created_at": r["created_at"], "metrics": extract_metrics(r["report"])} for r in recs]
    return aggregate(records, recent_window=recent_window)


@app.post("/api/admin/outcomes")
def admin_record_outcome(body: OutcomeIn, _admin: None = Depends(verify_admin_key)):
    """Record a real-world outcome for an analysis (the raw material for calibration)."""
    from services.database import record_outcome, get_report
    if not get_report(body.analysis_id):
        raise HTTPException(status_code=404, detail="Analysis not found")
    record_outcome(body.analysis_id, body.outcome_type, body.label, body.value, body.note, body.source)
    return {"recorded": True, "analysis_id": body.analysis_id, "outcome_type": body.outcome_type}


@app.get("/api/admin/validation")
def admin_validation(limit: int = 200, _admin: None = Depends(verify_admin_key)):
    """Model validation evidence: discrimination (AUC/Gini/KS + reliability) on REAL
    recorded outcomes, plus a Z''-proxy backtest computed NOW from existing analyses."""
    from services.database import outcomes_with_scores, recent_reports
    from services.validation import validation_report
    return validation_report(outcomes_with_scores(), recent_reports(limit))


@app.get("/api/admin/calibration")
def admin_calibration(min_n: int = 50, _admin: None = Depends(verify_admin_key)):
    """Platt calibration of the Imara Score -> probability-of-distress from recorded
    outcomes. Returns {calibrated: False} until enough data (AHP prior stands)."""
    from services.database import outcomes_with_scores
    from services.score_calibration import calibrate
    return calibrate(outcomes_with_scores(), min_n=min_n)


@app.get("/api/admin/analyses/{analysis_id}")
def admin_get_analysis(analysis_id: str, _admin: None = Depends(verify_admin_key)):
    """Full detail for one analysis including report."""
    row = db_get_analysis(analysis_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return row


@app.delete("/api/admin/analyses/{analysis_id}")
def admin_delete_analysis(analysis_id: str, _admin: None = Depends(verify_admin_key)):
    """Hard-delete an analysis record."""
    deleted = delete_analysis(analysis_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Not found")
    analyses.pop(analysis_id, None)
    analysis_status.pop(analysis_id, None)
    return {"deleted": True, "id": analysis_id}


# -- Background analysis pipeline ---------------------------------

async def _run_analysis(analysis_id: str, file_data: list, profile: dict):
    """Full multi-agent analysis pipeline. Runs in a thread pool."""
    def _sync_run():
        try:
            from services.tracing import new_ledger
            _ledger = new_ledger()  # per-analysis token/cost ledger (contextvars)
            clear_context(); bind_context(analysis_id=analysis_id)  # correlate all logs for this analysis
            get_logger("imara.pipeline").info("analysis_started", files=len(file_data))
            # 1. Parse uploaded files — route by category
            analysis_status[analysis_id]["current_agent"] = "Parsing uploaded files..."
            parsed_files = []
            category_texts = {
                "financial": [], "bank": [], "tax": [],
                "legal": [], "hr": [], "business_plan": [], "general": [],
            }
            for fd in file_data:
                analysis_status[analysis_id]["message"] = "Reading {}...".format(fd["filename"])
                parsed = parse_file(fd["filename"], fd["content"])
                parsed_files.append(parsed)
                cat = fd.get("category", "general")
                if cat not in category_texts:
                    cat = "general"
                if isinstance(parsed, dict):
                    text = parsed.get("text", "") or str(parsed)
                else:
                    text = str(parsed)
                category_texts[cat].append(text)

            business_data = merge_parsed_data(parsed_files)

            # 2. Build SharedMemory with profile context + SA fields + doc buckets
            memory = SharedMemory(
                business_name=profile["company_name"],
                industry=profile.get("industry_key", "general"),
                industry_key=profile.get("industry_key", "general"),
                annual_revenue=float(profile.get("annual_revenue", 0) or 0),
                headcount=int(profile.get("headcount", 0) or 0),
                currency=profile.get("currency", "ZAR"),
                country=profile.get("country", ""),
                primary_concern=profile.get("primary_concern", ""),
                # SA intake fields
                entity_type=profile.get("entity_type", ""),
                cipc_number=profile.get("cipc_number", ""),
                vat_registered=profile.get("vat_registered", "unknown"),
                vat_number=profile.get("vat_number", ""),
                tax_year_end=profile.get("tax_year_end", ""),
                years_in_business=profile.get("years_in_business", ""),
                bbbee_level=profile.get("bbbee_level", ""),
                banking_partner=profile.get("banking_partner", ""),
                report_audience=profile.get("report_audience", "owner"),
                # Document category text buckets
                uploaded_financial_text="\n\n".join(category_texts["financial"]),
                uploaded_bank_text="\n\n".join(category_texts["bank"]),
                uploaded_tax_text="\n\n".join(category_texts["tax"]),
                uploaded_legal_text="\n\n".join(category_texts["legal"]),
                uploaded_hr_text="\n\n".join(category_texts["hr"]),
                uploaded_plan_text="\n\n".join(category_texts["business_plan"]),
            )

            # 2b. Input-security guard: defang prompt-injection + redact PII in the
            # uploaded document text BEFORE any agent reads it (deterministic; figures
            # are never altered). Closes the one injection gap the pressure test flagged.
            from services.input_guard import sanitize_inputs
            business_data, input_security = sanitize_inputs(memory, business_data)

            # 3. Progress callback for frontend polling
            def on_progress(agent, message):
                analysis_status[analysis_id]["current_agent"] = agent
                analysis_status[analysis_id]["message"] = message
                _prog = analysis_status[analysis_id]["progress"]
                _prog.append({"agent": agent, "message": message})
                if len(_prog) > 200:               # bound unbounded growth on long runs
                    del _prog[:-200]

            # 4. Run full CEO-orchestrated analysis
            ceo = CEOAgent()
            report = ceo.run_full_analysis(business_data, memory, on_progress)

            # 5. Attach metadata
            report["industry_key"] = profile.get("industry_key", "general")
            report["currency"] = profile.get("currency", "ZAR")
            report["annual_revenue"] = profile.get("annual_revenue", 0)
            report["primary_concern"] = profile.get("primary_concern", "")
            report["llm_usage"] = _ledger.summary()
            from services.finding_quality import critique_report
            report["finding_quality"] = critique_report(report)  # deterministic per-finding critique
            from services.distress_score import altman_z_em
            report["distress_score"] = altman_z_em(report.get("financial_figures") or {}, report.get("imara_band", ""))
            from services.bank_signals import analyze_bank_statement
            report["bank_signals"] = analyze_bank_statement(memory.uploaded_bank_text)
            from services.normalization import normalize_earnings
            report["normalization"] = normalize_earnings(report.get("financial_figures") or {}, memory.uploaded_financial_text, getattr(memory, "uploaded_legal_text", ""))
            from services.lender_view import run_lender_view
            report["lender_view"] = run_lender_view(report.get("financial_figures") or {}, report.get("bank_signals") or {}, report.get("normalization") or {}, report.get("annual_revenue") or 0)
            from services.funding_fit import recommend_funding
            report["funding_fit"] = recommend_funding(report)
            from services.governance import decision_support_notice
            report["decision_support"] = decision_support_notice()
            from services.supplier_benchmark import run_supplier_benchmark
            _rev = report.get("annual_revenue") or (report.get("financial_figures") or {}).get("revenue") or 0
            report["supplier_benchmark"] = run_supplier_benchmark(memory.uploaded_financial_text, _rev, profile)
            from services.cashflow_13week import from_report as cashflow_from_report
            report["cashflow_13week"] = cashflow_from_report(report, memory)
            from services.agent_consistency import analyze_consistency
            report["cross_agent_consistency"] = analyze_consistency(report.get("all_findings_ranked") or [])
            report["input_security"] = input_security

            report = finite_safe(report)  # root-cause: strip NaN/inf once -> every consumer + the stored JSON is safe
            report["analysis_id"] = analysis_id  # ensure the report (and audit record) carry their id
            from services.audit_log import record_decision
            try:
                report["audit"] = record_decision(report, memory)  # hash-chained governance record
            except Exception as _ae:
                log.warning("audit_non_fatal", error=str(_ae))
            analyses[analysis_id] = report
            save_report(analysis_id, report)
            analysis_status[analysis_id]["status"] = "complete"
            analysis_status[analysis_id]["current_agent"] = "Analysis complete"
            analysis_status[analysis_id]["message"] = "All agents have completed their analysis."

        except Exception:
            get_logger("imara.pipeline").exception("analysis_failed")
            # Flip the client-visible status to a GENERIC message FIRST so a failure in
            # save_error() can't leave the run stuck on "processing"; never echo the raw
            # exception to the client (it can leak file paths / internal detail - the full
            # trace is in the server log above).
            _generic = "Analysis failed. Please try again or contact support."
            analysis_status[analysis_id]["status"] = "error"
            analysis_status[analysis_id]["error"] = _generic
            analysis_status[analysis_id]["message"] = _generic
            analysis_status[analysis_id]["current_agent"] = "Error"
            try:
                save_error(analysis_id, _generic)
            except Exception as _se:
                get_logger("imara.pipeline").warning("save_error_failed", error=str(_se))
        finally:
            clear_context()

    loop = asyncio.get_event_loop()
    try:
        await asyncio.wait_for(loop.run_in_executor(None, _sync_run), timeout=ANALYSIS_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        get_logger("imara.pipeline").error("analysis_timeout", analysis_id=analysis_id,
                                           timeout_s=ANALYSIS_TIMEOUT_SECONDS)
        _msg = "Analysis timed out. Please try again with fewer or smaller documents."
        st = analysis_status.get(analysis_id)
        if st is not None:
            st["status"] = "error"; st["error"] = _msg; st["message"] = _msg; st["current_agent"] = "Error"
        try:
            save_error(analysis_id, _msg)
        except Exception as _se:
            get_logger("imara.pipeline").warning("save_error_failed", error=str(_se))


# -- Demo endpoint (no API key required) --------------------------

DEMO_REPORT = {
    "analysis_id": "demo-001",
    "business_name": "Mzansi Retail Group",
    "industry": "Retail",
    "industry_key": "retail",
    "currency": "ZAR",
    "annual_revenue": 24500000,
    "headcount": 47,
    # SA intake identity (so the Bank-Ready Pack snapshot is fully populated in the demo)
    "entity_type": "Private company (Pty) Ltd",
    "cipc_number": "2016/204815/07",
    "vat_registered": "yes",
    "vat_number": "4820284517",
    "banking_partner": "Standard Bank",
    "years_in_business": "9",
    "tax_year_end": "28 February",
    "primary_concern": "Cash flow is tight — we struggle to pay suppliers on time.",
    "situation": "Mzansi Retail Group is a 47-person retail operation generating ZAR 24.5M in annual revenue across three locations in Gauteng.",
    "complication": "Gross margin has compressed to 18% against a sector benchmark of 32%, driven by uncontrolled COGS and a supplier payment cycle causing late-payment penalties.",
    "resolution": "Immediate margin recovery through supplier renegotiation and stock rationalisation can unlock an estimated ZAR 1.4M within 60 days.",
    "executive_summary": "Mzansi Retail Group shows strong top-line revenue but critical margin compression and working-capital stress. Three departments — procurement, inventory, and finance — require immediate intervention. The 15-agent analysis identified 11 findings, 3 of which are critical. Implementing the 90-day roadmap could recover ZAR 2.1M in margin and reduce debtor days from 54 to 30.",
    "scores": {
        "business_health": 42,
        "profitability":   28,
        "efficiency":      55,
        "risk":            38,
    },
    "critical_findings": 3,
    "high_findings":     4,
    "total_findings":    11,
    "credit_score":      61,
    "credit_grade":      "C+",
    "credit_barriers":   ["Debtor days 54 vs 30 benchmark", "Thin equity buffer (D/E 1.8x)", "Late supplier payments on record"],
    "credit_strengths":  ["Consistent 3-year revenue growth (+12% CAGR)", "Tangible asset base (owned fixtures)", "Owner salary within market norms"],
    "credit_products":   ["Business term loan", "Trade finance facility", "Development funding (IDC / SEFA)", "Invoice discounting"],
    "fraud_risk_level":  "medium",
    "fraud_risk_score":  38,
    "fraud_indicators":  [
        "Benford's Law digit-1 deviation: 2.4 sigma in sales ledger (threshold 2.0 sigma)",
        "3 round-number transactions >R50,000 with no supporting invoices",
        "Petty cash reconciliation gap of R18,400 over 6 months",
    ],
    "valuation_low":     14700000,
    "valuation_mid":     21200000,
    "valuation_high":    29800000,
    "valuation_method":  "EBITDA multiple (3.5x-5.5x) blended with asset-based approach",
    "forecast_base_12m": 26300000,
    "forecast_bull_12m": 31100000,
    "forecast_bear_12m": 20800000,
    "forecast_assumptions": [
        "Base: margin recovery to 24% via supplier renegotiation",
        "Bull: new Sandton location opens Q3, adds R4.8M revenue",
        "Bear: load-shedding escalates, footfall drops 15%",
    ],
    "all_findings_ranked": [
        {
            "title": "Gross Margin 14pp Below Benchmark",
            "severity": "critical",
            "agent": "Finance Agent",
            "department": "Finance",
            "financial_impact": "ZAR 3.4M annual margin leakage",
            "benchmark_reference": "SA Retail benchmark: 32% gross margin",
            "recommendation": "Audit top-20 SKUs for margin dilution; renegotiate top-5 supplier contracts within 30 days.",
            "quick_win": True,
        },
        {
            "title": "Debtor Days 54 vs 30 Sector Norm",
            "severity": "critical",
            "agent": "Finance Agent",
            "department": "Finance",
            "financial_impact": "ZAR 1.1M tied up in slow receivables",
            "benchmark_reference": "SA Retail: 25-35 debtor days",
            "recommendation": "Introduce 2% early-payment discount; automate payment reminders on day 15 and 30.",
            "quick_win": True,
        },
        {
            "title": "Stock Turnover 3.1x vs 8x Benchmark",
            "severity": "critical",
            "agent": "Operations Agent",
            "department": "Operations",
            "financial_impact": "ZAR 890K excess working capital locked in slow-moving stock",
            "benchmark_reference": "SA Retail: 6-10x annual stock turns",
            "recommendation": "Mark down bottom-20% SKUs for clearance; implement weekly reorder-point review.",
            "quick_win": False,
        },
        {
            "title": "No Formal Budget or Rolling Forecast",
            "severity": "high",
            "agent": "Finance Agent",
            "department": "Finance",
            "financial_impact": "Unable to quantify — structural risk",
            "benchmark_reference": "Best practice: monthly rolling 12-month forecast",
            "recommendation": "Implement a simple monthly P&L budget in Excel with variance tracking.",
            "quick_win": False,
        },
        {
            "title": "HR: No Employment Contracts for 6 Staff",
            "severity": "high",
            "agent": "HR Agent",
            "department": "HR",
            "financial_impact": "CCMA exposure estimated ZAR 180K",
            "benchmark_reference": "BCEA Section 29: written particulars mandatory",
            "recommendation": "Issue compliant employment contracts within 14 days. Use SACCI template.",
            "quick_win": True,
        },
        {
            "title": "POPIA Compliance Gap — Customer Data",
            "severity": "high",
            "agent": "Risk & Compliance Agent",
            "department": "Risk & Compliance",
            "financial_impact": "Regulatory fine up to ZAR 10M or 10% of turnover",
            "benchmark_reference": "POPIA Act 4 of 2013",
            "recommendation": "Appoint Information Officer, publish privacy policy, audit data processing within 60 days.",
            "quick_win": False,
        },
        {
            "title": "Marketing Spend 0.8% of Revenue vs 4% Benchmark",
            "severity": "high",
            "agent": "Marketing Agent",
            "department": "Marketing",
            "financial_impact": "Estimated ZAR 740K revenue uplift from closing the gap",
            "benchmark_reference": "SA Retail: 3-5% marketing/revenue ratio",
            "recommendation": "Allocate ZAR 200K to targeted Google/Meta campaigns for Q3 Sandton opening.",
            "quick_win": False,
        },
        {
            "title": "No Documented SOPs for Core Processes",
            "severity": "medium",
            "agent": "Operations Agent",
            "department": "Operations",
            "financial_impact": "Training cost and error cost estimated ZAR 95K/year",
            "benchmark_reference": "ISO 9001 operational documentation standard",
            "recommendation": "Document top-5 operational processes using a simple one-page SOP template.",
            "quick_win": False,
        },
        {
            "title": "IT: No Offsite Data Backup",
            "severity": "medium",
            "agent": "IT Agent",
            "department": "IT",
            "financial_impact": "Potential total data loss; recovery cost ZAR 250K+",
            "benchmark_reference": "3-2-1 backup rule",
            "recommendation": "Enable Backblaze B2 or AWS S3 offsite backup — R150/month.",
            "quick_win": True,
        },
        {
            "title": "No Customer Loyalty Programme",
            "severity": "low",
            "agent": "Marketing Agent",
            "department": "Marketing",
            "financial_impact": "Estimated 8% repeat purchase uplift = ZAR 320K",
            "benchmark_reference": "SA Retail: 60%+ of revenue from repeat customers",
            "recommendation": "Implement Smile.io or a simple punch-card programme within 30 days.",
            "quick_win": True,
        },
        {
            "title": "Supplier Concentration: Top 2 Suppliers = 71% of COGS",
            "severity": "medium",
            "agent": "Operations Agent",
            "department": "Operations",
            "financial_impact": "Single-supplier failure could halt operations for 3-6 weeks",
            "benchmark_reference": "Best practice: no single supplier >30% of COGS",
            "recommendation": "Qualify 2 alternative suppliers per product category within 90 days.",
            "quick_win": False,
        },
    ],
    "department_findings": {},
    "implementation_roadmap": [
        {
            "phase": "Phase 1 — Immediate (0-30 days)",
            "actions": [
                "Renegotiate top-5 supplier contracts for 3-5% cost reduction",
                "Issue employment contracts for 6 uncontracted staff",
                "Enable offsite backup (Backblaze B2)",
                "Introduce 2% early-payment discount for debtors",
                "Mark down slow-moving SKUs for clearance (bottom-20% by turns)",
            ],
            "expected_impact": "ZAR 580K margin recovery + ZAR 180K CCMA risk eliminated",
        },
        {
            "phase": "Phase 2 — Short-term (30-60 days)",
            "actions": [
                "Appoint POPIA Information Officer and audit data processing",
                "Implement monthly rolling P&L forecast (Excel)",
                "Automate debtor payment reminders (days 15, 30)",
                "Document top-5 operational SOPs",
                "Launch customer loyalty programme",
            ],
            "expected_impact": "ZAR 320K additional margin + regulatory compliance achieved",
        },
        {
            "phase": "Phase 3 — Medium-term (60-90 days)",
            "actions": [
                "Qualify 2 alternative suppliers per product category",
                "Allocate ZAR 200K to digital marketing for Sandton opening",
                "Weekly stock reorder-point review process",
                "Approach commercial lenders for a business term loan (the profile now supports it)",
                "Explore development-funding options (e.g. SEFA / IDC) for Sandton capex",
            ],
            "expected_impact": "ZAR 1.2M revenue uplift from new location + reduced COGS 4%",
        },
    ],
}


def _enrich_demo():
    """Compute the newer panels for the demo via the REAL engines (so the showcase is
    consistent and current) and register it so fetch-based panels (reasons / macro /
    simulator) resolve for analysis_id 'demo-001'. The demo is the primary sales surface."""
    from services.financial_ratios import compute_ratios, fundamentals_score
    from services.distress_score import altman_z_em
    from services.supplier_benchmark import run_supplier_benchmark
    from services.bank_signals import analyze_bank_statement
    from services.governance import decision_support_notice
    from services.normalization import normalize_earnings
    from services.lender_view import run_lender_view

    figs = {
        "revenue": 24_500_000, "cogs": 20_090_000, "gross_profit": 4_410_000,
        "operating_profit": 735_000, "net_profit": 380_000, "opex": 3_675_000,
        "current_assets": 4_600_000, "current_liabilities": 6_700_000, "inventory": 3_900_000,
        "receivables": 3_600_000, "payables": 4_100_000, "total_debt": 4_200_000,
        "equity": 1_400_000, "interest": 520_000, "cash": 300_000,
        "total_assets": 9_800_000, "total_liabilities": 8_400_000, "retained_earnings": -700_000,
    }
    DEMO_REPORT["financial_figures"] = figs
    DEMO_REPORT["financial_ratios"] = compute_ratios(figs, "retail", 24_500_000)
    DEMO_REPORT["financial_fundamentals_score"] = fundamentals_score(DEMO_REPORT["financial_ratios"], "retail").get("score") or 0
    DEMO_REPORT["financial_extraction_source"] = "deterministic"

    DEMO_REPORT.update({
        "imara_score": 48, "imara_band": "D", "imara_label": "At Risk", "imara_color": "#fb923c",
        "imara_completeness": 100, "imara_confidence": "high",
        "imara_components": [
            {"label": "Profitability", "value": 28, "weight": 0.25},
            {"label": "Credit Readiness", "value": 61, "weight": 0.20},
            {"label": "Risk & Compliance", "value": 42, "weight": 0.15},
            {"label": "Operational Efficiency", "value": 50, "weight": 0.10},
            {"label": "Financial Integrity", "value": 62, "weight": 0.10},
            {"label": "Market Visibility", "value": 55, "weight": 0.10},
            {"label": "Tax Compliance", "value": 70, "weight": 0.05},
            {"label": "Legal Compliance", "value": 60, "weight": 0.05},
        ],
    })

    DEMO_REPORT["distress_score"] = altman_z_em(figs, "D")
    from services.cashflow_13week import project_13week as _proj13
    DEMO_REPORT["cashflow_13week"] = _proj13(figs, vat_registered=True)
    from services.agent_consistency import analyze_consistency as _consist
    DEMO_REPORT["cross_agent_consistency"] = _consist(DEMO_REPORT.get("all_findings_ranked") or [])
    DEMO_REPORT["supplier_benchmark"] = run_supplier_benchmark(
        "Bank charges 185,000\nCard machine merchant fees 430,000\nTelephone and data 96,000\n"
        "Insurance 142,000\nFuel 78,000\nAccounting software Pastel 36,000\n",
        24_500_000, {"banking_partner": "Standard Bank"})
    DEMO_REPORT["bank_signals"] = analyze_bank_statement(
        "Date Description Amount Balance\n"
        "2026-01-03 Card settlement credit received 2,050,000.00 1,410,000.00\n"
        "2026-01-08 Debit order supplier RETURNED unpaid R/D 95,000.00 1,315,000.00\n"
        "2026-01-22 Rent debit payment 180,000.00 -45,000.00\n"
        "2026-02-05 Card settlement credit received 1,980,000.00 1,690,000.00\n"
        "2026-02-19 Debit order insurance insufficient funds reversal 42,000.00 -12,000.00\n"
        "2026-03-02 Card settlement credit received 2,060,000.00 1,615,000.00\n"
        "2026-03-10 Overdraft interest charge 22,000.00 588,000.00\n")
    _demo_fin = ("Revenue 24 500 000\nOperating profit 735 000\nDepreciation 610 000\n"
                 "Directors remuneration 1 080 000\nMotor vehicle expenses 240 000\n"
                 "Entertainment 110 000\nDonations 60 000\nRestructuring costs 180 000\nDrawings 300 000\n")
    DEMO_REPORT["normalization"] = normalize_earnings(figs, _demo_fin)
    DEMO_REPORT["lender_view"] = run_lender_view(figs, DEMO_REPORT["bank_signals"], DEMO_REPORT["normalization"], 24_500_000)
    from services.funding_fit import recommend_funding
    DEMO_REPORT["funding_fit"] = recommend_funding(DEMO_REPORT)
    DEMO_REPORT["decision_support"] = decision_support_notice()
    from services.audit_log import build_audit_record
    _arec = build_audit_record(DEMO_REPORT, "demo-inputs")
    DEMO_REPORT["audit"] = {"record_hash": "demo-" + _arec["figures_hash"][:24], "prev_hash": None,
                            "generated_at": _arec["generated_at"], "engine_version": _arec["engine_version"],
                            "models": _arec["models"], "figures_hash": _arec["figures_hash"],
                            "inputs_hash": _arec["inputs_hash"]}
    DEMO_REPORT["macro_performed"] = True
    DEMO_REPORT["macro_summary"] = ("Retail margins are exposed to inflation on the cost base and "
        "rand-driven import costs; interest-rate sensitivity is moderate on the existing debt.")
    DEMO_REPORT["macro_overall_exposure"] = "medium"
    DEMO_REPORT["macro_top_driver"] = "Inflation / input costs"

    DEMO_REPORT["quick_wins"] = [f for f in DEMO_REPORT["all_findings_ranked"] if f.get("quick_win")]

    # Populate the report's Department Findings + forecast curve from data the demo already
    # holds, so any HTML/PDF EXPORT of the demo (the sales surface) is complete - the live
    # pipeline sets these per run (ceo_agent by_agent + forecast engine); the demo did not.
    _dept = {}
    for _f in (DEMO_REPORT.get("all_findings_ranked") or []):
        _dept.setdefault(_f.get("agent") or "Other", []).append(_f)
    DEMO_REPORT["department_findings"] = _dept

    _b = DEMO_REPORT.get("forecast_base_12m", 0) or 0
    _u = DEMO_REPORT.get("forecast_bull_12m", 0) or 0
    _r = DEMO_REPORT.get("forecast_bear_12m", 0) or 0
    _months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    _curve = []
    for _i in range(12):
        _ramp = 0.90 + 0.20 * (_i / 11.0)   # gentle upward ramp; averages ~1.0 across the year
        _curve.append({"month": _months[_i],
                       "base": round(_b / 12.0 * _ramp),
                       "bull": round(_u / 12.0 * _ramp),
                       "bear": round(_r / 12.0 * _ramp)})
    DEMO_REPORT["forecast_monthly"] = _curve
    DEMO_REPORT["quick_wins_narrative"] = ("Five quick wins (each under 30 days) recover an estimated "
        "R760k in margin and remove R180k of CCMA risk at minimal cost.")
    _crit = [f for f in DEMO_REPORT["all_findings_ranked"] if f.get("severity") == "critical"][:5]
    DEMO_REPORT["top_priority_issues"] = [
        {"rank": i + 1, "title": f["title"], "estimated_total_impact": f.get("financial_impact", ""),
         "why_critical": f.get("recommendation", ""), "quick_win": f.get("quick_win", False)}
        for i, f in enumerate(_crit)]

    DEMO_REPORT["document_coverage"] = {"financial": True, "bank": True, "tax": False,
                                        "legal": False, "hr": True, "business_plan": False}
    DEMO_REPORT["llm_usage"] = {"calls": 38, "tokens": 214000, "est_cost_usd": 0.29,
        "by_model": {"claude-sonnet-4-6": 0.24, "claude-haiku-4-5-20251001": 0.05}}
    DEMO_REPORT["total_runtime_seconds"] = 642
    for _k in list(DEMO_REPORT.keys()):
        DEMO_REPORT[_k] = finite_safe(DEMO_REPORT[_k])

    analyses["demo-001"] = DEMO_REPORT


_enrich_demo()


@app.get("/api/demo")
def demo_report():
    """Returns a fully-populated demo report for UI testing — no API key or file upload required."""
    return DEMO_REPORT


@app.get("/api/demo/pdf")
def demo_pdf(audience: str = "owner"):
    """Generate a PDF from the demo report."""
    valid = {"owner", "banker", "investor"}
    if audience not in valid:
        audience = "owner"
    try:
        pdf_bytes = generate_pdf_report(DEMO_REPORT, audience=audience)
        filename = "demo_{}_report.pdf".format(audience)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename={}".format(filename)},
        )
    except Exception as e:
        log.error("pdf_generation_failed", error=str(e)[:200])
        raise HTTPException(status_code=500, detail="Could not generate the PDF report.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
