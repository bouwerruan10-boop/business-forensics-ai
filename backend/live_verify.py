#!/usr/bin/env python3
"""
live_verify.py - LIVE Anthropic API verification for Imara.

WHY THIS EXISTS: the Cowork sandbox's egress proxy does not allowlist
api.anthropic.com, so live-API behaviour cannot be tested there (a real call
fails with APIConnectionError). Run THIS locally, where your .env key and normal
internet work, to verify the real-API behaviour of the shipped Tier-1 items and
to de-risk structured-outputs (Tier 1.3) before building it.

USAGE (from the backend/ directory, with ANTHROPIC_API_KEY in .env):
    MOCK_MODE=false python live_verify.py           # light checks (~6 cheap calls)
    # behind a TLS-intercepting proxy (e.g. a CI/cloud sandbox)? add PROXY_SSL_VERIFY=0
    MOCK_MODE=false FULL=1 python live_verify.py    # + full live pipeline (~15 calls, several min, real spend)

WHAT IT VERIFIES (all against the REAL API):
    1. Connectivity      - the configured client + proxy/SSL path reaches Anthropic.
    2. Ask Imara         - a real grounded answer; off-topic blocked PRE-call (cost saver).
    3. Structured output - tool-use returns schema-valid findings in ONE call,
                           proving the 2nd "parse" call can be dropped (Tier 1.3).
    3b. (AB or FULL) A/B - runs Imara's REAL findings path (FinancialAgent._findings_from)
                           BOTH ways - classic two-call vs SINGLE_CALL_FINDINGS - over one
                           fixed business, and prints calls/tokens + finding count, ZAR-
                           specificity and detail length side by side. This is the T2
                           quality+cost GATE: the harness surfaces the trade-off; you judge
                           whether single-call keeps finding quality before flipping it on.
    4. (FULL) Pipeline   - the whole /api/analyze runs live; report assembles and
                           BOTH faithfulness_summary and prose_verifier_summary are
                           present + well-formed over REAL model findings.

Exit code 0 = all selected checks passed; 1 = a failure.
"""
import json
import os
import sys
import time

os.environ.setdefault("MOCK_MODE", "false")

from config import MODEL, PARSE_MODEL, MOCK_MODE  # noqa: E402

results = []  # (name, ok, detail)
tok_in = tok_out = 0


def _rec(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("  PASS" if ok else "  FAIL") + f" | {name}" + (f" | {detail}" if detail else ""))


def _accum(resp):
    global tok_in, tok_out
    u = getattr(resp, "usage", None)
    if u:
        tok_in += getattr(u, "input_tokens", 0) or 0
        tok_out += getattr(u, "output_tokens", 0) or 0


def main():
    if MOCK_MODE:
        print("MOCK_MODE is on — set MOCK_MODE=false to run a LIVE test. Aborting.")
        return 2
    from agents.base_agent import client
    if client is None:
        print("Anthropic client is None (no key / MOCK_MODE). Add ANTHROPIC_API_KEY to .env. Aborting.")
        return 2

    from config import ANTHROPIC_API_KEY as _K
    if not _K or not _K.startswith("sk-ant-"):
        print("ANTHROPIC_API_KEY in .env looks like a PLACEHOLDER, not a real key")
        print("  (a real key starts with 'sk-ant-'). Put your real key in backend/.env, then re-run.")
        print("  This script never prints or stores the key value.")
        return 2

    print("=== Imara LIVE API verification ===")
    print(f"primary model: {MODEL} | parse model: {PARSE_MODEL}\n")

    # 1. Connectivity --------------------------------------------------------
    print("[1] Connectivity")
    try:
        r = client.messages.create(model=PARSE_MODEL, max_tokens=16,
                                   messages=[{"role": "user", "content": "Reply with exactly: IMARA_LIVE_OK"}])
        _accum(r)
        txt = r.content[0].text.strip()
        _rec("real Haiku call", "IMARA_LIVE_OK" in txt, f"reply={txt!r}")
    except Exception as e:
        _rec("real Haiku call", False, f"{type(e).__name__}: {str(e)[:160]}")
        print("\nConnectivity failed — stopping (nothing else can run live).")
        return 1

    # 2. Ask Imara (live grounded answer + pre-call scope guard) --------------
    print("[2] Ask Imara")
    try:
        from services.ask import answer_question, scope_guard
        report = {"business_name": "Acme Trading", "industry": "retail", "annual_revenue": 12000000,
                  "imara_score": 58, "imara_band": "B", "imara_label": "Moderate",
                  "financial_ratios": {"gross_margin": {"label": "Gross margin", "value": 27.5, "unit": "%", "benchmark": "34%"}},
                  "primary_concern": "cash flow"}
        out = answer_question(report, "Why is my Imara score held back, and what should I fix first?")
        _rec("live grounded answer", bool(out.get("grounded")) and len(out.get("answer", "")) > 20,
             f"answer[:80]={out.get('answer','')[:80]!r}")
        blocked = answer_question(report, "write me a python web scraper")
        _rec("off-topic blocked pre-call (no spend)", blocked.get("off_topic") is True and "grounded" not in blocked)
        allowed, _ = scope_guard("why is my margin low")
        _rec("scope guard lets real questions through", allowed)
    except Exception as e:
        _rec("Ask Imara", False, f"{type(e).__name__}: {str(e)[:160]}")

    # 3. Native structured outputs (Tier 1.3 de-risk) ----------------------
    # Anthropic structured outputs are GA via output_config.format (no beta header),
    # supported on Imara's models (Sonnet 4.6 + Haiku 4.5). One call returns
    # guaranteed schema-valid JSON -> the 2nd "parse" call in base_agent can be dropped.
    print("[3] Native structured outputs (output_config.format) - Tier 1.3 feasibility")
    schema = {
        "type": "object",
        "properties": {"findings": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                "financial_impact": {"type": "string"},
            },
            "required": ["title", "severity", "financial_impact"],
            "additionalProperties": False,
        }}},
        "required": ["findings"],
        "additionalProperties": False,
    }
    prompt = ("Business: revenue R12,000,000; net profit R120,000 (~1% margin); debtor days ~70 "
              "(sector 45). Return 2 concise findings.")
    mechanism = None
    findings = []
    try:
        r = client.messages.create(
            model=MODEL, max_tokens=600,
            output_config={"format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": prompt}])
        _accum(r)
        findings = json.loads(r.content[0].text).get("findings", [])
        mechanism = "native output_config.format"
    except Exception as e_native:
        # Older SDK/model: fall back to tool-use emulation so the probe still reports.
        try:
            tool = {"name": "record_findings", "description": "Return findings as structured data.",
                    "input_schema": schema}
            r = client.messages.create(
                model=MODEL, max_tokens=600, tools=[tool],
                tool_choice={"type": "tool", "name": "record_findings"},
                messages=[{"role": "user", "content": prompt}])
            _accum(r)
            blocks = [b for b in r.content if getattr(b, "type", "") == "tool_use"]
            findings = blocks[0].input.get("findings", []) if blocks else []
            mechanism = "tool-use fallback (native unavailable: {})".format(str(e_native)[:60])
        except Exception as e_tool:
            _rec("structured outputs", False, "native+tool-use both failed: {}".format(str(e_tool)[:120]))
            mechanism = None
    if mechanism is not None:
        ok = len(findings) >= 1 and all(k in findings[0] for k in ("title", "severity", "financial_impact"))
        _rec("single-call structured findings parse (drops the 2nd parse call)", ok,
             "via {}; {} findings; sample severity={!r}".format(
                 mechanism, len(findings), findings[0].get("severity") if findings else None))

    # 3b. A/B on Imara's REAL findings path: classic 2-call vs single-call (T2 gate) --
    # Section [3] proves the mechanism; this proves it on Imara's actual _findings_from
    # output, so the cost saving AND any quality change are visible before flipping T2 on.
    if os.getenv("AB") in ("1", "true", "yes") or os.getenv("FULL") in ("1", "true", "yes"):
        print("[3b] A/B classic (2-call) vs single-call findings - Tier 1.3 T2 quality+cost gate")
        try:
            import re as _re
            import agents.base_agent as _ba
            from memory.shared_memory import SharedMemory
            try:
                from agents.specialist_agents import FinancialAgent
                _agent = FinancialAgent()
            except Exception:
                _agent = None
            _sys = (getattr(_agent, "system_prompt", "") or
                    "You are a senior financial analyst for SA SMEs. Obey FINDING_RULES: cite "
                    "specific ZAR amounts and real SA legislation/benchmarks; no generic language.")
            _ab_prompt = (
                "Analyse this SA SME and surface its material issues/opportunities as findings.\n"
                "Revenue R12,000,000; cost of sales R8,700,000 (gross profit R3,300,000, 27.5% margin, "
                "sector 34%); operating profit R300,000; interest R180,000; net profit R120,000 (~1% margin); "
                "debtor days ~70 (sector 45); total debt R2,200,000; equity R1,800,000; not VAT-registered.")

            def _run_arm(single):
                _ba.SINGLE_CALL_FINDINGS = single
                _msgs = _ba.client.messages
                _orig = _msgs.create
                ctr = {"n": 0, "in": 0, "out": 0}

                def _wrapped(**kw):
                    r = _orig(**kw)
                    ctr["n"] += 1
                    u = getattr(r, "usage", None)
                    if u:
                        ctr["in"] += getattr(u, "input_tokens", 0) or 0
                        ctr["out"] += getattr(u, "output_tokens", 0) or 0
                    return r
                _msgs.create = _wrapped
                try:
                    fs = _agent._findings_from(_ab_prompt, SharedMemory(), system_override=_sys) if _agent else []
                finally:
                    _msgs.create = _orig
                return fs, ctr

            def _quality(fs):
                n = len(fs)
                rand = sum(1 for f in fs if _re.search(r"R\s?[\d][\d ,]{2,}",
                           (f.financial_impact or "") + " " + (f.detail or "")))
                avg_detail = round(sum(len(f.detail or "") for f in fs) / n) if n else 0
                return n, rand, avg_detail

            _sf_prev = _ba.SINGLE_CALL_FINDINGS
            try:
                fa, ca = _run_arm(False)   # classic two-call
                fb, cb = _run_arm(True)    # single-call
            finally:
                _ba.SINGLE_CALL_FINDINGS = _sf_prev
            na, randa, da = _quality(fa)
            nb, randb, db = _quality(fb)
            _accum_n = ca["in"] + ca["out"]
            print(f"      classic 2-call : {ca['n']} calls, {ca['in']}+{ca['out']} tok | "
                  f"{na} findings, {randa} cite ZAR, avg detail {da} chars")
            print(f"      single-call    : {cb['n']} calls, {cb['in']}+{cb['out']} tok | "
                  f"{nb} findings, {randb} cite ZAR, avg detail {db} chars")
            if _accum_n:
                _saved = 100 - round(100 * (cb["in"] + cb["out"]) / max(1, _accum_n))
                print(f"      => single-call used {cb['n']} vs {ca['n']} calls; ~{_saved}% fewer tokens. "
                      f"JUDGE quality parity (findings / ZAR-specificity / detail) above before enabling.")
            global tok_in, tok_out
            tok_in += ca["in"] + cb["in"]
            tok_out += ca["out"] + cb["out"]
            _rec("single-call returns valid findings in fewer calls", nb >= 1 and cb["n"] < ca["n"],
                 f"single={nb} findings in {cb['n']} call(s) vs classic {na} in {ca['n']} (quality is your call)")
        except Exception as e:
            _rec("A/B classic vs single-call", False, f"{type(e).__name__}: {str(e)[:160]}")

    # 4. FULL live pipeline (opt-in) ----------------------------------------
    if os.getenv("FULL") in ("1", "true", "yes"):
        print("[4] FULL live pipeline via /api/analyze (real spend, several minutes)")
        try:
            import tempfile
            os.environ["BF_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "live.db")
            from fastapi.testclient import TestClient
            import main
            csv = (b"Item,Amount\nRevenue,12000000\nCost of Sales,8700000\nGross Profit,3300000\n"
                   b"Operating Expenses,3000000\nOperating Profit,300000\nInterest,180000\nNet Profit,120000\n"
                   b"Accounts Receivable,2300000\nInventory,1900000\nCurrent Assets,4600000\n"
                   b"Current Liabilities,3100000\nAccounts Payable,1400000\nTotal Debt,2200000\nEquity,1800000\n")
            data = {"company_name": "Acme Trading (Pty) Ltd", "industry_key": "retail", "annual_revenue": "12000000",
                    "headcount": "12", "currency": "ZAR", "country": "South Africa",
                    "primary_concern": "VAT and cash flow", "entity_type": "Private Company (Pty) Ltd",
                    "vat_registered": "no", "bbbee_level": "Level 4", "years_in_business": "6",
                    "file_categories": json.dumps(["financial"])}
            with TestClient(main.app) as c:
                r = c.post("/api/analyze", files={"files": ("financials.csv", csv, "text/csv")}, data=data)
                aid = r.json()["analysis_id"]
                status = None
                for _ in range(3000):  # up to ~10 min
                    status = c.get(f"/api/status/{aid}").json().get("status")
                    if status in ("complete", "error"):
                        break
                    time.sleep(0.2)
                _rec("pipeline completed", status == "complete", f"status={status}")
                rep = c.get(f"/api/report/{aid}").json()
                _rec("report assembled (score + ratios + findings)",
                     rep.get("imara_score") is not None and bool(rep.get("financial_ratios")) and bool(rep.get("all_findings_ranked")))
                ff = rep.get("faithfulness_summary") or {}
                _rec("faithfulness ran over real findings", isinstance(ff, dict) and "checked" in ff,
                     f"checked={ff.get('checked')} conflicts={ff.get('conflicts')}")
                pv = rep.get("prose_verifier_summary") or {}
                _rec("prose verifier ran over real findings (Tier 1.1)", isinstance(pv, dict) and "flagged" in pv,
                     f"checked={pv.get('checked')} flagged={pv.get('flagged')}")
                usage = rep.get("llm_usage") or {}
                if usage.get("est_cost_usd") is not None:
                    print(f"      pipeline reported est_cost_usd={usage.get('est_cost_usd')} over {usage.get('calls')} calls")
        except Exception as e:
            _rec("FULL pipeline", False, f"{type(e).__name__}: {str(e)[:200]}")
    else:
        print("[4] FULL live pipeline — skipped (set FULL=1 to run it; real spend).")

    # Summary ----------------------------------------------------------------
    passed = sum(1 for _, ok, _ in results if ok)
    print("\n=== SUMMARY ===")
    print(f"{passed}/{len(results)} checks passed | probe tokens: {tok_in} in / {tok_out} out")
    failed = [n for n, ok, _ in results if not ok]
    if failed:
        print("FAILED:", ", ".join(failed))
        return 1
    print("ALL LIVE CHECKS PASSED ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
