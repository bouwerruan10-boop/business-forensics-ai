"""
Imara -- FastAPI backend
Endpoints:
  POST /api/analyze         -- upload files + business profile, trigger full analysis
  GET  /api/status/{id}     -- poll analysis progress
  GET  /api/report/{id}     -- get full JSON report
  GET  /api/report/{id}/pdf -- download premium PDF report
  POST /api/simulate        -- what-if digital twin simulation
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
from fastapi.responses import Response
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from services.file_parser import parse_file, merge_parsed_data
from services.report_generator import generate_pdf_report
from services.html_report import generate_html_report
from services.benchmark_service import get_benchmarks, detect_industry
from services.database import (
    init_db, create_analysis, save_report, save_error,
    get_report, list_analyses, count_analyses, delete_analysis,
    get_analysis as db_get_analysis, mark_interrupted_analyses,
    create_share, resolve_share, revoke_share,
)
from agents.ceo_agent import CEOAgent
from memory.shared_memory import SharedMemory
from auth import get_principal, Principal
from config import PUBLIC_API, API_VERSION
from services.score_contract import score_contract, usage_summary

# -- Rate limiter setup -------------------------------------------
# Configurable via RATE_LIMIT env var, default: 3 per hour
RATE_LIMIT = os.getenv("RATE_LIMIT", "3/hour")
limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])

# -- Optional API key gate ----------------------------------------
# Set API_SECRET_KEY in your .env to enable. Leave blank to disable.
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")


def verify_api_key(request: Request):
    """Dependency: enforce API key if API_SECRET_KEY is configured."""
    if not API_SECRET_KEY:
        return  # gate disabled
    provided = request.headers.get("X-API-Key", "")
    if provided != API_SECRET_KEY:
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
    if provided != ADMIN_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing admin key. Provide it in the X-Admin-Key header.",
        )


app = FastAPI(
    title="Imara",
    description="AI-powered multi-agent business consulting platform",
    version="2.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.on_event("startup")
def on_startup():
    init_db()
    _interrupted = mark_interrupted_analyses()
    if _interrupted:
        print("[startup] flagged {} interrupted analysis(es) from a previous run".format(_interrupted))


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
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for active sessions -- SQLite is the durable store
analyses: dict = {}
analysis_status: dict = {}


# -- Pydantic models -----------------------------------------------

class SimulateRequest(BaseModel):
    analysis_id: str
    scenario: str
    change_percent: float

class ActionSimRequest(BaseModel):
    analysis_id: str
    actions: list = []
    scenario: str = "expected"
    variable: str


# -- Routes --------------------------------------------------------

@app.get("/api/health")
def health():
    # RAILWAY_GIT_COMMIT_SHA is injected by Railway at build time; "dev" locally.
    return {
        "status": "ok",
        "service": "Imara v2.0",
        "commit": os.getenv("RAILWAY_GIT_COMMIT_SHA", "dev")[:8],
    }


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
    # File category labels — JSON array matching files[] order
    # e.g. '["financial","bank","tax"]'
    file_categories: Optional[str] = Form("[]"),
    _api_key: None = Depends(verify_api_key),
    principal: Principal = Depends(get_principal),
):
    """Accept files + business profile. Returns analysis_id to poll."""
    import json as _json
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    # Parse file category labels
    try:
        categories = _json.loads(file_categories or "[]")
    except Exception:
        categories = []

    analysis_id = str(uuid.uuid4())
    analysis_status[analysis_id] = {
        "status": "processing",
        "progress": [],
        "current_agent": "Parsing uploaded files...",
        "message": "Reading and classifying your business data...",
    }

    # Read file bytes immediately -- can't read in background task
    file_data = []
    for i, f in enumerate(files):
        content = await f.read()
        file_data.append({
            "filename": f.filename,
            "content": content,
            "category": categories[i] if i < len(categories) else "general",
        })

    profile = {
        "company_name": company_name or "Unknown Business",
        "industry_key": industry_key or "general",
        "annual_revenue": annual_revenue or 0.0,
        "headcount": headcount or 0,
        "currency": currency or "ZAR",
        "country": country or "",
        "primary_concern": primary_concern or "",
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


@app.post("/api/simulate/montecarlo")
def simulate_montecarlo(req: ActionSimRequest):
    """Probabilistic outcome distribution + probability of reaching the next band."""
    result = analyses.get(req.analysis_id) or get_report(req.analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    from services.simulation import monte_carlo
    return monte_carlo(result, req.actions)


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


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    """
    Run a what-if scenario using the digital twin parameters from an analysis.
    Uses the business actual revenue and benchmark cost ratios for the industry.
    """
    result = analyses.get(req.analysis_id) or get_report(req.analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")

    twin = result.get("digital_twin_parameters", {})
    base_revenue = twin.get("base_revenue", 0) or result.get("annual_revenue", 0)
    currency = result.get("currency", "ZAR")
    industry_key = result.get("industry_key", "general")
    bm = get_benchmarks(industry_key)
    labour_ratio = bm.get("cost_ratios", {}).get("labour_pct_revenue", 0.30)
    fuel_ratio = bm.get("cost_ratios", {}).get("fuel_pct_revenue", 0.08)
    op_margin = bm.get("margins", {}).get("operating_margin", 0.12)

    change = req.change_percent / 100
    c = currency

    if req.variable == "revenue":
        new_rev = base_revenue * (1 + change)
        profit_impact = (new_rev - base_revenue) * op_margin
        return {
            "scenario": "Revenue {:+.1f}%".format(req.change_percent),
            "change": "{:+.1f}%".format(req.change_percent),
            "projected_revenue": new_rev,
            "revenue_delta": new_rev - base_revenue,
            "estimated_profit_impact": profit_impact,
            "currency": c,
            "note": "Profit impact estimated at {:.1f}% operating margin (industry benchmark)".format(op_margin * 100),
        }
    elif req.variable == "labor_cost":
        labour_base = base_revenue * labour_ratio
        saving = labour_base * abs(change)
        key = "annual_saving" if change < 0 else "annual_cost"
        return {
            "scenario": "Labour cost {:+.1f}%".format(req.change_percent),
            "change": "{:+.1f}%".format(req.change_percent),
            "estimated_labour_base": labour_base,
            key: saving,
            "profit_impact": saving if change < 0 else -saving,
            "currency": c,
            "note": "Labour estimated at {:.0f}% of revenue (industry benchmark)".format(labour_ratio * 100),
        }
    elif req.variable == "fuel_cost":
        fuel_base = base_revenue * fuel_ratio
        fuel_impact = fuel_base * change
        return {
            "scenario": "Fuel cost {:+.1f}%".format(req.change_percent),
            "change": "{:+.1f}%".format(req.change_percent),
            "estimated_fuel_base": fuel_base,
            "fuel_cost_change": fuel_impact,
            "profit_impact": -fuel_impact,
            "currency": c,
            "note": "Fuel estimated at {:.0f}% of revenue (industry benchmark)".format(fuel_ratio * 100),
        }
    else:
        return {
            "scenario": req.scenario,
            "variable": req.variable,
            "change": "{:+.1f}%".format(req.change_percent),
            "note": "Custom scenario -- provide more specific financial data for detailed modelling",
        }


# -- Admin endpoints -----------------------------------------------

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

            # 3. Progress callback for frontend polling
            def on_progress(agent, message):
                analysis_status[analysis_id]["current_agent"] = agent
                analysis_status[analysis_id]["message"] = message
                analysis_status[analysis_id]["progress"].append(
                    {"agent": agent, "message": message}
                )

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

            analyses[analysis_id] = report
            save_report(analysis_id, report)
            analysis_status[analysis_id]["status"] = "complete"
            analysis_status[analysis_id]["current_agent"] = "Analysis complete"
            analysis_status[analysis_id]["message"] = "All agents have completed their analysis."

        except Exception as e:
            save_error(analysis_id, str(e))
            analysis_status[analysis_id]["status"] = "error"
            analysis_status[analysis_id]["error"] = str(e)
            analysis_status[analysis_id]["current_agent"] = "Error: {}".format(e)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _sync_run)


# -- Demo endpoint (no API key required) --------------------------

DEMO_REPORT = {
    "analysis_id": "demo-001",
    "business_name": "Mzansi Retail Group",
    "industry": "Retail",
    "industry_key": "retail",
    "currency": "ZAR",
    "annual_revenue": 24500000,
    "headcount": 47,
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
    "credit_products":   ["ABSA Business Term Loan", "Nedbank Trade Finance Facility", "IDC SME Growth Fund", "SEFA Bridging Finance"],
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
                "Apply for ABSA Business Term Loan (credit score now C+)",
                "Engage SEFA SME Growth Fund for Sandton capex",
            ],
            "expected_impact": "ZAR 1.2M revenue uplift from new location + reduced COGS 4%",
        },
    ],
}


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
        raise HTTPException(status_code=500, detail="PDF generation error: {}".format(str(e)))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
