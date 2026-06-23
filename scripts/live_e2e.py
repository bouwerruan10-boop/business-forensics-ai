#!/usr/bin/env python3
"""Imara live end-to-end test against the DEPLOYED instance (stdlib only; no pip install).

Modes:
  smoke (default, FREE - no Anthropic spend, no secret needed): /api/health +
        /api/demo with every report section asserted present/available.
  full  (PAID ~ $0.29, needs OPERATOR_PASSWORD): smoke + login -> analyze a sample
        financials file -> poll status to 'complete' -> fetch report + the
        assurance / credit-memo / working-capital / compliance-calendar endpoints.

Env: IMARA_API (default = Railway prod URL), OPERATOR_PASSWORD, E2E_ANALYZE_TIMEOUT.
Exit 0 = all checks passed, 1 = a check failed.
"""
import os, sys, json, time, uuid, urllib.request, urllib.error

API = os.environ.get("IMARA_API", "https://web-production-87ff5c.up.railway.app").rstrip("/")
PW = os.environ.get("OPERATOR_PASSWORD", "")
TIMEOUT = int(os.environ.get("E2E_ANALYZE_TIMEOUT", "1500"))

_fails = []
def check(name, ok, detail=""):
    print("  [{}] {}{}".format("PASS" if ok else "FAIL", name, ("  -- " + detail) if detail else ""))
    if not ok:
        _fails.append(name)
    return ok

def _req(method, path, headers=None, body=None):
    req = urllib.request.Request(API + path, data=body, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()

def get_json(path, headers=None):
    st, raw = _req("GET", path, headers)
    try:
        return st, json.loads(raw.decode("utf-8"))
    except Exception:
        return st, None

def multipart(fields, files):
    boundary = "----imara" + uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append("--" + boundary)
        parts.append('Content-Disposition: form-data; name="{}"'.format(k))
        parts.append("")
        parts.append(str(v))
    body = ("\r\n".join(parts) + "\r\n").encode("utf-8")
    for name, filename, content, ctype in files:
        body += ("--" + boundary + "\r\n"
                 'Content-Disposition: form-data; name="{}"; filename="{}"\r\n'.format(name, filename)
                 + "Content-Type: {}\r\n\r\n".format(ctype)).encode("utf-8") + content + b"\r\n"
    body += ("--" + boundary + "--\r\n").encode("utf-8")
    return body, "multipart/form-data; boundary=" + boundary

SAMPLE_CSV = (
    b"Line Item,Amount (ZAR)\r\nRevenue,8450000\r\nCost of Sales,5915000\r\n"
    b"Gross Profit,2535000\r\nOperating Profit,230000\r\nInterest Expense,198000\r\n"
    b"Net Profit Before Tax,32000\r\nCash and Equivalents,142000\r\nAccounts Receivable,1620000\r\n"
    b"Inventory,1340000\r\nTotal Assets,4952000\r\nAccounts Payable,1180000\r\n"
    b"Total Liabilities,3380000\r\nShareholders Equity,1572000\r\n"
)

def smoke():
    print("== SMOKE (free) ==")
    st, h = get_json("/api/health?cb=" + str(int(time.time())))
    check("health 200", st == 200, "status {}".format(st))
    check("health has auth_required", isinstance(h, dict) and "auth_required" in (h or {}), str(h)[:70])
    st, d = get_json("/api/demo?cb=" + str(int(time.time())))
    check("demo 200", st == 200, "status {}".format(st))
    d = d or {}
    for key in ("imara_score", "financial_ratios", "all_findings_ranked", "executive_summary"):
        check("demo has " + key, key in d)
    for sect in ("assurance", "credit_memo", "working_capital", "compliance_calendar",
                 "lender_view", "funding_fit", "normalization", "bank_signals", "distress_score"):
        check("demo " + sect + ".available", bool((d.get(sect) or {}).get("available")))
    check("demo SA panel flagged (renders all cards)", bool(d.get("sa_tax_performed") or d.get("sa_legal_performed")))

def login():
    st, raw = _req("POST", "/api/login", {"Content-Type": "application/json"},
                   json.dumps({"password": PW}).encode("utf-8"))
    try:
        tok = json.loads(raw.decode()).get("token")
    except Exception:
        tok = None
    check("login 200 + token", st == 200 and bool(tok), "status {}".format(st))
    return tok

def full():
    smoke()
    print("== FULL (paid ~ $0.29) ==")
    if not PW:
        check("OPERATOR_PASSWORD set", False, "env missing - cannot run full")
        return
    tok = login()
    if not tok:
        return
    auth = {"Authorization": "Bearer " + tok}
    fields = {
        "company_name": "E2E Test Co (Pty) Ltd", "industry_key": "construction",
        "annual_revenue": "8450000", "headcount": "31", "currency": "ZAR",
        "country": "South Africa", "entity_type": "Private Company (Pty) Ltd",
        "cipc_number": "2014/118267/07", "vat_registered": "yes", "tax_year_end": "February",
        "years_in_business": "7-15 years", "bbbee_level": "EME", "report_audience": "bank",
        "primary_concern": "Automated end-to-end test run.",
        "file_categories": json.dumps(["financial"]), "consent": "true",
    }
    body, ctype = multipart(fields, [("files", "e2e_financials.csv", SAMPLE_CSV, "text/csv")])
    hdr = dict(auth); hdr["Content-Type"] = ctype
    st, raw = _req("POST", "/api/analyze", hdr, body)
    try:
        aid = json.loads(raw.decode()).get("analysis_id")
    except Exception:
        aid = None
    if not check("analyze accepted", st in (200, 202) and bool(aid), "status {} body {}".format(st, raw[:80])):
        return
    print("  analysis_id {} - polling up to {}s".format(aid, TIMEOUT))
    t0, status = time.time(), None
    while time.time() - t0 < TIMEOUT:
        time.sleep(10)
        _, sj = get_json("/api/status/" + aid, auth)
        status = (sj or {}).get("status")
        if status in ("complete", "error", "failed"):
            break
    check("pipeline completed", status == "complete", "final status {}".format(status))
    if status != "complete":
        return
    st, rep = get_json("/api/report/" + aid, auth)
    rep = rep or {}
    check("report 200", st == 200)
    for key in ("imara_score", "financial_ratios", "all_findings_ranked"):
        check("report has " + key, key in rep)
    for sect, ep in (("assurance", "assurance"), ("credit_memo", "credit-memo"),
                     ("working_capital", "working-capital"), ("compliance_calendar", "compliance-calendar")):
        sst, sj = get_json("/api/report/{}/{}".format(aid, ep), auth)
        check("section " + sect, sst == 200 and bool((sj or {}).get("available")), "status {}".format(sst))

def main():
    mode = "smoke"
    for a in sys.argv[1:]:
        if a.startswith("--mode"):
            mode = a.split("=", 1)[1] if "=" in a else "full"
        elif a in ("smoke", "full"):
            mode = a
    print("Imara live e2e -> {}  (mode={})".format(API, mode))
    (full if mode == "full" else smoke)()
    print()
    if _fails:
        print("RESULT: FAIL ({} check(s)): {}".format(len(_fails), ", ".join(_fails)))
        sys.exit(1)
    print("RESULT: PASS - all checks green")

if __name__ == "__main__":
    main()
