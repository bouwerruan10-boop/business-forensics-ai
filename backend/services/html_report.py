"""
Interactive HTML Report Generator — Imara
Self-contained: all CSS, JS, and SVG charts are inlined.
No external dependencies — works offline, can be emailed.
"""
from datetime import date
import html as _html_mod


# ── Colour constants (JS hex strings) ────────────────────────────
NAVY   = "#0D1B2A"
GOLD   = "#C9A84C"
GREEN  = "#1A7A40"
AMBER  = "#C9820A"
ORANGE = "#D35400"
RED    = "#C0392B"
GRAY   = "#888888"
LIGHT  = "#EBEBEB"
OFF_W  = "#F8F7F4"
DARK   = "#555555"


def _e(text) -> str:
    """HTML-escape a value."""
    return _html_mod.escape(str(text or ""), quote=True)


def _rag_color(val: float, lo: float, hi: float, invert: bool = False) -> str:
    """Return hex colour for a value given lo/hi thresholds."""
    if invert:
        if val <= lo:
            return GREEN
        elif val <= hi:
            return AMBER
        else:
            return RED
    else:
        if val >= hi:
            return GREEN
        elif val >= lo:
            return AMBER
        else:
            return RED


# ── Main entry point ──────────────────────────────────────────────

def generate_html_report(report: dict) -> str:
    """Return a fully self-contained HTML string for the report."""
    biz      = _e(report.get("business_name", "Business"))
    industry = _e(report.get("industry", "General"))
    cur      = _e(report.get("currency", "ZAR"))
    rev      = report.get("annual_revenue", 0)
    country  = _e(report.get("country", ""))
    today    = date.today().strftime("%d %B %Y")
    scores   = report.get("scores", {})
    health   = scores.get("business_health", 0)
    profit   = scores.get("profitability", 0)
    eff      = scores.get("efficiency", 0)
    risk     = scores.get("risk", 0)
    credit_score = report.get("credit_score", 0)
    credit_grade = _e(report.get("credit_grade", "—"))
    fraud_level  = _e(report.get("fraud_risk_level", "unknown"))
    fraud_score  = report.get("fraud_risk_score", 0)
    val_low  = report.get("valuation_low",  0)
    val_mid  = report.get("valuation_mid",  0)
    val_high = report.get("valuation_high", 0)
    val_meth = _e(report.get("valuation_method", ""))
    fcast_base = report.get("forecast_base_12m", 0)
    fcast_bull = report.get("forecast_bull_12m", 0)
    fcast_bear = report.get("forecast_bear_12m", 0)
    total_f  = report.get("total_findings", 0)
    critical = report.get("critical_findings", 0)
    high_f   = report.get("high_findings",  0)
    quick_w  = len(report.get("quick_wins", []))
    exec_sum = _e(report.get("executive_summary") or report.get("summary", ""))
    situation    = _e(report.get("situation", ""))
    complication = _e(report.get("complication", ""))
    resolution   = _e(report.get("resolution", ""))
    biz_summary  = _e(report.get("business_model_summary", ""))
    strategic    = _e(report.get("strategic_plays_narrative", ""))

    rev_str = f"{cur} {rev:,.0f}" if rev else "—"

    # ── SVG score bars ────────────────────────────────────────────
    def _score_bar(label: str, val: int, lo: int = 50, hi: int = 70,
                   invert: bool = False) -> str:
        col = _rag_color(val, lo, hi, invert)
        w = max(2, int(val * 2.4))   # 0–240 px
        return f"""
        <div class="bar-row">
          <span class="bar-label">{_e(label)}</span>
          <div class="bar-track">
            <div class="bar-fill" style="width:{w}px; background:{col}"></div>
          </div>
          <span class="bar-val" style="color:{col}">{val}</span>
        </div>"""

    score_bars = (
        _score_bar("Business Health", health) +
        _score_bar("Profitability", profit) +
        _score_bar("Efficiency", eff) +
        _score_bar("Risk", risk) +
        _score_bar("Credit Readiness", credit_score, 40, 60) +
        _score_bar("Fraud Risk (lower=better)", fraud_score, 20, 50, invert=True)
    )

    # ── Financial Fundamentals (deterministic, grounded) ──────────
    _ratios = report.get("financial_ratios", {}) or {}
    ratios_html = ""
    if _ratios:
        _fund = report.get("financial_fundamentals_score")
        _statcol = {"good": GREEN, "warning": AMBER, "critical": RED}
        _rrows = ""
        for _k, _r in _ratios.items():
            _v = _r.get("value")
            _val = ("%g%s" % (_v, _r.get("unit", ""))) if _v is not None else "—"
            _col = _statcol.get(_r.get("status"), GRAY)
            _rrows += f"""
            <tr>
              <td class="fr-label">{_e(_r.get('label',''))}</td>
              <td class="fr-val" style="color:{_col}">{_e(_val)}</td>
              <td class="fr-bench">{_e(_r.get('benchmark'))}</td>
              <td class="fr-status"><span style="color:{_col}">&#9679;</span> {_e(str(_r.get('status','')).title())}</td>
              <td class="fr-src">{_e(_r.get('source',''))}</td>
            </tr>"""
        _fund_html = (f'<span class="fr-score">Fundamentals score: <b>{_fund}/100</b></span>'
                      if _fund else '')
        ratios_html = f"""
  <style>
    .fr-wrap{{background:#fff;border:1px solid {LIGHT};border-radius:14px;padding:18px 20px;margin-bottom:22px}}
    .fr-head{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px}}
    .fr-title{{font-size:15px;font-weight:700;color:{NAVY}}}
    .fr-score{{font-size:12px;color:{DARK}}}
    .fr-note{{font-size:11px;color:{GRAY};margin-bottom:12px}}
    table.fr{{width:100%;border-collapse:collapse;font-size:12px}}
    table.fr th{{text-align:left;color:{GRAY};font-size:10px;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid {LIGHT};padding:4px 8px}}
    table.fr td{{padding:6px 8px;border-bottom:1px solid #F3F3F3;vertical-align:top}}
    .fr-label{{font-weight:600;color:{NAVY};white-space:nowrap}}
    .fr-val{{font-weight:700;white-space:nowrap}}
    .fr-bench{{color:{DARK}}}
    .fr-status{{white-space:nowrap}}
    .fr-src{{color:{GRAY};font-size:11px}}
  </style>
  <div class="fr-wrap">
    <div class="fr-head">
      <span class="fr-title">Financial Fundamentals</span>
      {_fund_html}
    </div>
    <div class="fr-note">Computed directly from your financial statements (arithmetic, not AI-generated). Each figure is traceable to its source line items.</div>
    <table class="fr">
      <thead><tr><th>Metric</th><th>Value</th><th>Benchmark</th><th>Status</th><th>Source figures</th></tr></thead>
      <tbody>{_rrows}</tbody>
    </table>
  </div>"""

    # ── Imara Score hero ──────────────────────────────────────────
    imara_score = report.get("imara_score")
    imara_html = ""
    if imara_score is not None:
        imara_band  = _e(report.get("imara_band", ""))
        imara_label = _e(report.get("imara_label", ""))
        _imc = report.get("imara_components", []) or []

        def _imara_col(s):
            if s >= 80: return GOLD
            if s >= 65: return GREEN
            if s >= 50: return AMBER
            if s >= 35: return ORANGE
            return RED

        icol = report.get("imara_color") or _imara_col(imara_score)
        imara_conf = (report.get("imara_confidence") or "").capitalize()
        imara_compl = report.get("imara_completeness")
        comp_rows = ""
        for c in _imc:
            v = int(round(c.get("value", 0)))
            wpct = int(round(c.get("weight", 0) * 100))
            vcol = GREEN if v >= 70 else AMBER if v >= 40 else RED
            bw = max(2, int(v * 1.6))
            comp_rows += f"""
            <div class="imara-comp">
              <span class="imara-comp-label">{_e(c.get('label',''))}</span>
              <div class="imara-comp-track"><div class="imara-comp-fill" style="width:{bw}px;background:{vcol}"></div></div>
              <span class="imara-comp-val" style="color:{vcol}">{v}</span>
              <span class="imara-comp-wt">{wpct}%</span>
            </div>"""

        imara_html = f"""
  <style>
    .imara-hero{{display:flex;gap:20px;flex-wrap:wrap;background:#fff;border:1px solid {GOLD}33;border-radius:14px;padding:20px;margin-bottom:22px}}
    .imara-score-panel{{flex:0 0 200px;border:1.5px solid;border-radius:12px;padding:16px;text-align:center;background:{OFF_W}}}
    .imara-kicker{{font-size:10px;letter-spacing:2px;color:{GOLD};font-weight:700;margin-bottom:6px}}
    .imara-score-num{{font-size:52px;font-weight:800;line-height:1}}
    .imara-score-sub{{font-size:11px;color:{GRAY};margin-bottom:10px}}
    .imara-band{{display:inline-block;color:#fff;font-size:12px;font-weight:700;border-radius:20px;padding:4px 12px}}
    .imara-breakdown{{flex:1;min-width:260px}}
    .imara-bd-title{{font-size:15px;font-weight:700;color:{NAVY};margin-bottom:4px}}
    .imara-bd-desc{{font-size:12px;color:{DARK};line-height:1.5;margin-bottom:12px}}
    .imara-comp{{display:flex;align-items:center;gap:10px;margin-bottom:7px}}
    .imara-comp-label{{flex:0 0 145px;font-size:12px;color:{DARK}}}
    .imara-comp-track{{flex:1;height:7px;background:{LIGHT};border-radius:4px;overflow:hidden}}
    .imara-comp-fill{{height:100%;border-radius:4px}}
    .imara-comp-val{{flex:0 0 26px;text-align:right;font-size:12px;font-weight:700}}
    .imara-comp-wt{{flex:0 0 38px;text-align:right;font-size:11px;color:{GRAY}}}
  </style>
  <div class="imara-hero">
    <div class="imara-score-panel" style="border-color:{icol}">
      <div class="imara-kicker">IMARA SCORE&trade;</div>
      <div class="imara-score-num" style="color:{icol}">{imara_score}</div>
      <div class="imara-score-sub">out of 100</div>
      <div class="imara-band" style="background:{icol}">Band {imara_band} &middot; {imara_label}</div>
    </div>
    <div class="imara-breakdown">
      <div class="imara-bd-title">Bankability &amp; Investability</div>
      <div class="imara-bd-desc">A single composite rating across every specialist analysis, weighted toward what a lender or investor assesses. Weights are re-normalised over the components scored in this analysis.{(" &middot; <b>Confidence: " + imara_conf + "</b> (" + str(imara_compl) + "% of signals)") if imara_conf else ""}</div>
      {comp_rows}
    </div>
  </div>"""

    # ── Valuation bar SVG ─────────────────────────────────────────
    def _val_bar_svg() -> str:
        if not val_mid:
            return "<p style='color:#888;font-size:13px'>No valuation data available.</p>"
        total = val_high or (val_mid * 1.5)
        if total == 0:
            return ""
        lo_pct  = int(val_low  / total * 300)
        mid_pct = int(val_mid  / total * 300)
        hi_pct  = int(val_high / total * 300)
        return f"""
        <svg width="320" height="70" viewBox="0 0 320 70" xmlns="http://www.w3.org/2000/svg">
          <rect x="0"        y="20" width="{lo_pct}"  height="30" rx="4" fill="{RED}"  opacity="0.85"/>
          <rect x="0"        y="20" width="{mid_pct}" height="30" rx="4" fill="{AMBER}" opacity="0.85"/>
          <rect x="0"        y="20" width="{hi_pct}"  height="30" rx="4" fill="{GREEN}" opacity="0.85"/>
          <text x="{lo_pct  - 4}" y="16" font-size="9" fill="{RED}"   text-anchor="end">Bear {cur} {val_low:,.0f}</text>
          <text x="{mid_pct - 4}" y="60" font-size="9" fill="{AMBER}" text-anchor="end">Base {cur} {val_mid:,.0f}</text>
          <text x="{hi_pct  - 4}" y="16" font-size="9" fill="{GREEN}" text-anchor="end">Bull {cur} {val_high:,.0f}</text>
        </svg>"""

    # ── Department findings HTML ──────────────────────────────────
    sev_color = {"critical": RED, "high": ORANGE, "medium": AMBER, "low": GREEN}
    sev_bg    = {"critical": "#FDECEA", "high": "#FEF0E6", "medium": "#FEF8E6", "low": "#E8F5EE"}

    dept_html = ""
    dept = report.get("department_findings", {})
    for agent_name, findings in dept.items():
        if not findings:
            continue
        cards = ""
        for f in sorted(findings, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x.get("severity", "medium"), 9)):
            sev   = f.get("severity", "medium")
            col   = sev_color.get(sev, GRAY)
            bg    = sev_bg.get(sev, OFF_W)
            qw    = "⚡ " if f.get("quick_win") else ""
            title = _e(f.get("title", ""))
            det   = _e(f.get("detail", ""))
            imp   = _e(f.get("financial_impact", ""))
            rec   = _e(f.get("recommendation", ""))
            bench = _e(f.get("benchmark_reference", ""))
            coi   = _e(f.get("cost_of_inaction", ""))
            roi   = _e(f.get("roi_estimate", ""))
            cards += f"""
            <div class="finding-card" style="border-left:4px solid {col}; background:{bg}">
              <div class="finding-header" style="background:{col}">
                <span class="sev-badge">{sev.upper()}</span>
                <span class="finding-title">{qw}{title}</span>
              </div>
              <div class="finding-body">
                {f'<p>{det}</p>' if det else ""}
                {f'<p class="bench">📊 {bench}</p>' if bench else ""}
                {f'<p class="impact">💰 Financial impact: <strong>{imp}</strong></p>' if imp else ""}
                {f'<p class="coi">⚠️ Cost of inaction: {coi}</p>' if coi else ""}
                {f'<p class="roi">📈 ROI: {roi}</p>' if roi else ""}
                {f'<p class="rec">→ {rec}</p>' if rec else ""}
              </div>
            </div>"""
        dept_html += f"""
        <div class="agent-section">
          <h3 class="agent-name">{_e(agent_name)}</h3>
          {cards}
        </div>"""

    # ── Quick wins checklist ──────────────────────────────────────
    quick_wins_html = ""
    for qw_f in report.get("quick_wins", [])[:8]:
        title = _e(qw_f.get("title", ""))
        rec   = _e(qw_f.get("recommendation", ""))
        imp   = _e(qw_f.get("financial_impact", ""))
        quick_wins_html += f"""
        <div class="qw-item">
          <label>
            <input type="checkbox" class="qw-check">
            <span class="qw-title">{title}</span>
          </label>
          {f'<p class="qw-rec">→ {rec}</p>' if rec else ""}
          {f'<span class="qw-impact">💰 {imp}</span>' if imp else ""}
        </div>"""

    # ── Roadmap items ─────────────────────────────────────────────
    phase_cols = [RED, ORANGE, GREEN]
    roadmap_html = ""
    for i, phase in enumerate(report.get("implementation_roadmap", [])):
        pc    = phase_cols[i] if i < len(phase_cols) else NAVY
        ptitle = _e(phase.get("phase", f"Phase {i + 1}"))
        focus  = _e(phase.get("focus", ""))
        exp    = _e(phase.get("expected_impact", ""))
        actions_html = ""
        for j, act in enumerate(phase.get("actions", [])[:5], 1):
            if isinstance(act, dict):
                at = _e(act.get("action", ""))
                ao = _e(act.get("owner", ""))
                ai = _e(act.get("impact", ""))
            else:
                at = _e(str(act))
                ao = ai = ""
            actions_html += f"""
            <div class="road-action">
              <span class="road-num" style="color:{pc}">{j}</span>
              <span>{at}</span>
              {f'<small style="color:#888"> · {ao}</small>' if ao else ""}
              {f'<small style="color:#888"> · {ai}</small>' if ai else ""}
            </div>"""
        roadmap_html += f"""
        <div class="phase-card" style="border-top:3px solid {pc}">
          <div class="phase-header" style="background:{pc}">
            <span class="phase-num">{i + 1}</span>
            <span class="phase-title">{ptitle}</span>
            <span class="phase-focus">{focus}</span>
          </div>
          <div class="phase-body">
            {f'<p class="exp-impact">Expected: {exp}</p>' if exp else ""}
            {actions_html}
          </div>
        </div>"""

    # ── Forecast monthly chart (simple SVG) ───────────────────────
    forecast_html = ""
    monthly = report.get("forecast_monthly", [])
    if monthly and fcast_base:
        max_val = max((m.get("bull", 0) for m in monthly), default=1) or 1
        bar_w = 14
        gap   = 4
        svg_w = (bar_w * 3 + gap * 2 + 6) * 12 + 20
        svg_h = 120
        bars_svg = ""
        for i, m in enumerate(monthly[:12]):
            x0   = 10 + i * (bar_w * 3 + gap * 2 + 6)
            base = int(m.get("base", 0) / max_val * 90)
            bull = int(m.get("bull", 0) / max_val * 90)
            bear = int(m.get("bear", 0) / max_val * 90)
            mon  = _e(m.get("month", str(i + 1)))
            bars_svg += f"""
            <rect x="{x0}"              y="{100 - bear}" width="{bar_w}" height="{bear}" fill="{RED}" opacity="0.7"/>
            <rect x="{x0 + bar_w + 2}"  y="{100 - base}" width="{bar_w}" height="{base}" fill="{AMBER}" opacity="0.8"/>
            <rect x="{x0 + bar_w * 2 + 4}" y="{100 - bull}" width="{bar_w}" height="{bull}" fill="{GREEN}" opacity="0.7"/>
            <text x="{x0 + bar_w + 1}" y="115" font-size="7" text-anchor="middle" fill="{GRAY}">{mon[:3]}</text>"""
        forecast_html = f"""
        <div class="section-block">
          <h2 class="section-title">12-MONTH REVENUE FORECAST</h2>
          <div class="forecast-summary">
            <div class="fcast-box" style="color:{RED}">
              <span class="fcast-label">BEAR</span>
              <span class="fcast-val">{cur} {fcast_bear:,.0f}</span>
            </div>
            <div class="fcast-box" style="color:{AMBER}">
              <span class="fcast-label">BASE</span>
              <span class="fcast-val">{cur} {fcast_base:,.0f}</span>
            </div>
            <div class="fcast-box" style="color:{GREEN}">
              <span class="fcast-label">BULL</span>
              <span class="fcast-val">{cur} {fcast_bull:,.0f}</span>
            </div>
          </div>
          <svg width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}"
               style="max-width:100%;overflow:visible" xmlns="http://www.w3.org/2000/svg">
            {bars_svg}
          </svg>
          <div class="legend">
            <span style="color:{RED}">■ Bear</span>&nbsp;&nbsp;
            <span style="color:{AMBER}">■ Base</span>&nbsp;&nbsp;
            <span style="color:{GREEN}">■ Bull</span>
          </div>
        </div>"""

    # ── Credit barriers + strengths ───────────────────────────────
    credit_html = ""
    barriers  = report.get("credit_barriers", [])
    strengths = report.get("credit_strengths", [])
    products  = report.get("credit_products", [])
    if credit_score or barriers or strengths:
        grade_col = {"A": GREEN, "B": GREEN, "C": AMBER, "D": ORANGE, "F": RED}.get(
            report.get("credit_grade", ""), GRAY)
        grade_str = report.get("credit_grade", "—")
        bar_html = (
            "".join(f'<div class="cr-barrier">✗ {_e(b)}</div>' for b in barriers[:5]) or "<em>None</em>"
        )
        str_html = (
            "".join(f'<div class="cr-strength">✓ {_e(s)}</div>' for s in strengths[:5]) or "<em>None</em>"
        )
        prod_html = "  ·  ".join(_e(p) for p in products[:8]) or "—"
        credit_html = f"""
        <div class="section-block">
          <h2 class="section-title">CREDIT READINESS</h2>
          <div class="credit-summary">
            <div class="credit-score-box">
              <span class="big-num" style="color:{_rag_color(credit_score,40,60)}">{credit_score}</span>
              <span class="score-label">/ 100</span>
            </div>
            <div class="credit-grade-box">
              <span class="big-grade" style="color:{grade_col}">{_e(grade_str)}</span>
              <span class="grade-label">Credit Grade</span>
            </div>
          </div>
          <div class="sb-grid">
            <div class="sb-col green-bg">
              <h4>STRENGTHS</h4>{str_html}
            </div>
            <div class="sb-col red-bg">
              <h4>BARRIERS</h4>{bar_html}
            </div>
          </div>
          <div class="products-row">
            <strong>Available Funding Products:</strong> {prod_html}
          </div>
        </div>"""

    # ── Fraud risk block ──────────────────────────────────────────
    flags   = report.get("fraud_indicators", [])
    fr_col  = {"low": GREEN, "medium": AMBER, "high": ORANGE, "critical": RED}.get(
        fraud_level.lower(), GRAY)
    fr_bg   = {"low": "#E8F5EE", "medium": "#FEF8E6",
               "high": "#FEF0E6", "critical": "#FDECEA"}.get(fraud_level.lower(), OFF_W)
    flags_html = "".join(
        f'<div class="flag-item" style="border-left:3px solid {fr_col}"><b>{i}.</b> {_e(f)}</div>'
        for i, f in enumerate(flags[:5], 1)
    )
    fraud_html = f"""
    <div class="section-block" style="border:2px solid {fr_col}; background:{fr_bg}">
      <h2 class="section-title">FRAUD &amp; ANOMALY RISK</h2>
      <div class="fraud-summary">
        <span class="fraud-level" style="color:{fr_col}">{_e(fraud_level).upper()}</span>
        <span class="fraud-score" style="color:{fr_col}">Score: {fraud_score}/100</span>
      </div>
      {f'<div class="flags-list">{flags_html}</div>' if flags_html else ""}
      <p class="disclaimer">Statistical analysis only — engage a CFE for a formal forensic audit.</p>
    </div>"""

    # ── Top priority issues ───────────────────────────────────────
    top_issues_html = ""
    for issue in report.get("top_priority_issues", [])[:5]:
        rank   = _e(issue.get("rank", ""))
        title  = _e(issue.get("title", ""))
        impact = _e(issue.get("estimated_total_impact", ""))
        why    = _e(issue.get("why_critical", ""))
        is_qw  = issue.get("quick_win", False)
        top_issues_html += f"""
        <div class="issue-row">
          <span class="issue-rank" style="color:{GOLD}">#{rank}</span>
          <div class="issue-body">
            <strong>{title}</strong>
            {' <span class="qw-tag">⚡ QUICK WIN</span>' if is_qw else ""}
            {f'<p class="issue-why">{why}</p>' if why else ""}
            {f'<p class="issue-impact"><strong>{impact}</strong></p>' if impact else ""}
          </div>
        </div>"""

    # ── Key risks + opportunities ─────────────────────────────────
    risks = report.get("key_risks", [])
    opps  = report.get("key_opportunities", [])
    risk_html = "".join(f'<li>{_e(r)}</li>' for r in risks[:5])
    opp_html  = "".join(f'<li>{_e(o)}</li>' for o in opps[:5])

    # ── Valuation block HTML ──────────────────────────────────────
    val_html = ""
    if val_mid:
        val_html = f"""
        <div class="section-block">
          <h2 class="section-title">BUSINESS VALUATION</h2>
          <div class="val-grid">
            <div class="val-box" style="color:{RED}">
              <span class="val-label">BEAR</span>
              <span class="val-num">{cur} {val_low:,.0f}</span>
            </div>
            <div class="val-box" style="color:{NAVY}; font-size:1.3em">
              <span class="val-label">BASE (MID)</span>
              <span class="val-num">{cur} {val_mid:,.0f}</span>
            </div>
            <div class="val-box" style="color:{GREEN}">
              <span class="val-label">BULL</span>
              <span class="val-num">{cur} {val_high:,.0f}</span>
            </div>
          </div>
          {_val_bar_svg()}
          {f'<p class="val-method"><strong>Method:</strong> {val_meth}</p>' if val_meth else ""}
          <p class="disclaimer">Indicative estimates. Engage a registered valuator before transacting.</p>
        </div>"""

    # ── Tax Me If You Can — legal tax savings ──────────────────────
    tax_html = ""
    _tx = report.get("tax_optimization") or {}
    if _tx.get("available"):
        _tcur = _tx.get("currency", "ZAR")
        _ttotal = _tx.get("total_saving_high", 0) or 0

        def _tesc(t):
            return str(t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        _trows = ""
        for _o in (_tx.get("opportunities") or []):
            _osav = _o.get("est_saving_high") or 0
            if _o.get("quantified"):
                _amt = f'<span style="color:{GREEN};font-weight:700">save {_tcur} {_osav:,.0f}</span>'
            elif _osav:
                _amt = f'<span style="color:{AMBER}">up to {_tcur} {_osav:,.0f} (unconfirmed)</span>'
            else:
                _amt = f'<span style="color:{GRAY}">potential</span>'
            _trows += (f'<div style="padding:8px 0;border-bottom:1px solid #eee">'
                       f'<strong>{_tesc(_o.get("name"))}</strong> '
                       f'<em style="color:{GRAY}">[{_tesc(_o.get("eligible"))}]</em> &nbsp; {_amt}<br>'
                       f'<span style="font-size:12px;color:{DARK}">{_tesc(_o.get("basis"))}</span><br>'
                       f'<span style="font-size:12px;color:{GRAY}">Action: {_tesc(_o.get("action"))}</span></div>')
        tax_html = f"""
        <div class="section-block">
          <h2 class="section-title">TAX ME IF YOU CAN \u2014 LEGAL TAX SAVINGS</h2>
          <p style="font-size:20px;font-weight:800;color:{GREEN};margin:4px 0">Estimated quantifiable annual saving: {_tcur} {_ttotal:,.0f}</p>
          <p style="font-size:13px;color:{NAVY}">{_tesc(_tx.get("summary", ""))}</p>
          {_trows}
          <p style="font-size:11px;color:{GRAY};font-style:italic;margin-top:8px">{_tesc(_tx.get("disclaimer", ""))}</p>
        </div>"""

    # ── CSS ────────────────────────────────────────────────────────
    css = f"""
    :root {{
      --navy:{NAVY}; --gold:{GOLD}; --green:{GREEN}; --amber:{AMBER};
      --orange:{ORANGE}; --red:{RED}; --gray:{GRAY}; --light:{LIGHT};
      --off:{OFF_W}; --dark:{DARK};
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background: #f3f4f6;
            color: var(--dark); font-size: 14px; }}
    a {{ color: var(--navy); }}

    /* Header */
    .report-header {{ background: var(--navy); color: white; padding: 28px 40px 20px; }}
    .report-header h1 {{ font-size: 28px; font-weight: 700; color: var(--gold); }}
    .report-header .sub {{ font-size: 13px; opacity: 0.7; margin-top: 4px; }}
    .report-date {{ font-size: 12px; opacity: 0.5; float: right; margin-top: -24px; }}

    /* Nav */
    .report-nav {{ background: var(--navy); border-top: 1px solid rgba(255,255,255,0.1);
                   padding: 0 40px; display:flex; gap:0; overflow-x:auto; }}
    .nav-tab {{ color: rgba(255,255,255,0.6); padding: 10px 18px; cursor:pointer;
                font-size:12px; font-weight:600; letter-spacing:0.5px;
                border-bottom: 3px solid transparent; white-space:nowrap; }}
    .nav-tab:hover, .nav-tab.active {{ color: var(--gold); border-bottom-color: var(--gold); }}

    /* Content */
    .content {{ padding: 28px 40px; max-width: 1100px; margin: 0 auto; }}
    .page {{ display:none; }}
    .page.active {{ display:block; }}

    /* Score metrics */
    .metrics-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:20px; }}
    .metric-card {{ background:white; border-radius:8px; padding:16px;
                    box-shadow:0 1px 4px rgba(0,0,0,.08); text-align:center; }}
    .metric-label {{ font-size:10px; font-weight:700; letter-spacing:1px;
                     color:var(--gray); text-transform:uppercase; }}
    .metric-val {{ font-size:32px; font-weight:700; margin:6px 0 2px; }}
    .metric-sub {{ font-size:11px; color:var(--gray); }}

    /* Score bars */
    .bars-section {{ background:white; border-radius:8px; padding:20px;
                     box-shadow:0 1px 4px rgba(0,0,0,.08); margin-bottom:20px; }}
    .bars-title {{ font-size:11px; font-weight:700; letter-spacing:1px;
                   color:var(--navy); text-transform:uppercase; margin-bottom:14px; }}
    .bar-row {{ display:flex; align-items:center; gap:10px; margin-bottom:10px; }}
    .bar-label {{ width:200px; font-size:12px; color:var(--dark); flex-shrink:0; }}
    .bar-track {{ width:240px; height:12px; background:var(--light); border-radius:6px;
                  overflow:hidden; flex-shrink:0; }}
    .bar-fill {{ height:100%; border-radius:6px; transition:width 0.6s ease; }}
    .bar-val {{ font-size:13px; font-weight:700; width:36px; }}

    /* Section blocks */
    .section-block {{ background:white; border-radius:8px; padding:22px;
                      box-shadow:0 1px 4px rgba(0,0,0,.08); margin-bottom:20px; }}
    .section-title {{ font-size:11px; font-weight:700; letter-spacing:1.5px;
                      color:var(--navy); text-transform:uppercase;
                      border-bottom:2px solid var(--gold); padding-bottom:8px;
                      margin-bottom:14px; }}

    /* SCR */
    .scr-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:1px;
                 background:var(--light); border:1px solid var(--light);
                 border-radius:6px; overflow:hidden; margin-bottom:16px; }}
    .scr-col {{ background:white; padding:14px; }}
    .scr-col h4 {{ font-size:10px; font-weight:700; letter-spacing:1px;
                   color:var(--navy); text-transform:uppercase;
                   background:var(--navy); color:white;
                   margin:-14px -14px 10px; padding:6px 14px; }}
    .scr-col p {{ font-size:13px; line-height:1.6; color:var(--dark); }}

    /* Risks/opportunities */
    .ro-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
    .ro-col {{ background:white; border-radius:8px; padding:14px;
               box-shadow:0 1px 4px rgba(0,0,0,.08); }}
    .ro-col h4 {{ font-size:10px; font-weight:700; letter-spacing:1px;
                  text-transform:uppercase; margin-bottom:8px; }}
    .ro-col ul {{ padding-left:16px; }}
    .ro-col li {{ font-size:13px; margin-bottom:4px; color:var(--dark); }}

    /* Top issues */
    .issue-row {{ display:flex; gap:14px; padding:10px 0;
                  border-bottom:1px solid var(--light); align-items:flex-start; }}
    .issue-rank {{ font-size:20px; font-weight:700; flex-shrink:0; }}
    .issue-body strong {{ font-size:13px; color:var(--navy); }}
    .issue-why {{ font-size:12px; color:var(--gray); margin:2px 0; }}
    .issue-impact {{ font-size:13px; color:var(--red); margin-top:2px; }}
    .qw-tag {{ background:#E8F5EE; color:var(--green); font-size:10px;
               font-weight:700; padding:2px 6px; border-radius:4px; margin-left:6px; }}

    /* Agent findings */
    .agent-section {{ margin-bottom:28px; }}
    .agent-name {{ font-size:13px; font-weight:700; color:var(--gold);
                   text-transform:uppercase; letter-spacing:0.5px;
                   border-bottom:2px solid var(--gold); padding-bottom:4px;
                   margin-bottom:12px; }}
    .finding-card {{ border-radius:6px; margin-bottom:10px; overflow:hidden; }}
    .finding-header {{ display:flex; align-items:center; gap:10px;
                       padding:6px 12px; }}
    .sev-badge {{ font-size:9px; font-weight:700; color:white; letter-spacing:0.5px; }}
    .finding-title {{ font-size:13px; font-weight:700; color:white; }}
    .finding-body {{ padding:10px 14px; }}
    .finding-body p {{ font-size:12px; line-height:1.6; margin-bottom:4px; }}
    .impact {{ color:var(--red); font-weight:600; }}
    .rec {{ color:var(--green); font-weight:600; }}
    .bench, .coi, .roi {{ color:var(--gray); }}

    /* Quick wins checklist */
    .qw-item {{ background:white; border-left:4px solid var(--green); padding:10px 14px;
                border-radius:0 6px 6px 0; margin-bottom:10px;
                box-shadow:0 1px 3px rgba(0,0,0,.06); }}
    .qw-item label {{ display:flex; align-items:flex-start; gap:8px; cursor:pointer; }}
    .qw-check {{ margin-top:3px; accent-color:var(--green); width:16px; height:16px;
                 flex-shrink:0; }}
    .qw-check:checked ~ .qw-title {{ text-decoration:line-through; opacity:0.5; }}
    .qw-title {{ font-size:13px; font-weight:600; color:var(--navy); }}
    .qw-rec {{ font-size:12px; color:var(--green); margin:4px 0 0 24px; }}
    .qw-impact {{ font-size:11px; color:var(--red); display:block; margin-left:24px; }}

    /* Roadmap */
    .phase-card {{ border-radius:8px; overflow:hidden; margin-bottom:14px;
                   box-shadow:0 1px 4px rgba(0,0,0,.08); }}
    .phase-header {{ display:flex; align-items:center; gap:12px; padding:10px 14px; }}
    .phase-num {{ font-size:20px; font-weight:700; color:white; }}
    .phase-title {{ font-size:13px; font-weight:700; color:white; flex:1; }}
    .phase-focus {{ font-size:11px; color:rgba(255,255,255,0.75); }}
    .phase-body {{ background:white; padding:12px 14px; }}
    .exp-impact {{ font-size:12px; color:var(--green); font-weight:600; margin-bottom:8px; }}
    .road-action {{ display:flex; align-items:baseline; gap:8px;
                    padding:5px 0; border-bottom:1px solid var(--light);
                    font-size:12px; color:var(--dark); }}
    .road-num {{ font-size:14px; font-weight:700; flex-shrink:0; width:20px; }}

    /* Credit */
    .credit-summary {{ display:flex; gap:20px; margin-bottom:14px; }}
    .credit-score-box, .credit-grade-box {{ text-align:center; padding:14px 24px;
                                            background:var(--off); border-radius:8px; }}
    .big-num {{ font-size:52px; font-weight:700; display:block; line-height:1; }}
    .score-label, .grade-label {{ font-size:11px; color:var(--gray); }}
    .big-grade {{ font-size:64px; font-weight:700; display:block; line-height:1; }}
    .sb-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:1px;
                background:var(--light); border:1px solid var(--light);
                border-radius:6px; overflow:hidden; margin-bottom:10px; }}
    .sb-col {{ padding:12px 14px; }}
    .sb-col h4 {{ font-size:10px; font-weight:700; letter-spacing:1px;
                  text-transform:uppercase; margin-bottom:8px; }}
    .green-bg {{ background:#E8F5EE; }}
    .red-bg {{ background:#FDECEA; }}
    .cr-strength {{ font-size:13px; color:var(--green); margin-bottom:4px; }}
    .cr-barrier  {{ font-size:13px; color:var(--red);   margin-bottom:4px; }}
    .products-row {{ font-size:12px; color:var(--dark); padding:8px 0;
                     border-top:1px solid var(--light); }}

    /* Valuation */
    .val-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:14px; }}
    .val-box {{ text-align:center; padding:16px; background:var(--off); border-radius:8px; }}
    .val-label {{ font-size:10px; font-weight:700; letter-spacing:1px;
                  text-transform:uppercase; display:block; opacity:0.7; }}
    .val-num {{ font-size:20px; font-weight:700; display:block; margin-top:4px; }}
    .val-method {{ font-size:12px; color:var(--gray); margin-top:10px; }}

    /* Forecast */
    .forecast-summary {{ display:grid; grid-template-columns:repeat(3,1fr);
                          gap:12px; margin-bottom:14px; }}
    .fcast-box {{ text-align:center; padding:12px; background:var(--off); border-radius:8px; }}
    .fcast-label {{ font-size:10px; font-weight:700; letter-spacing:1px;
                    text-transform:uppercase; display:block; opacity:0.7; }}
    .fcast-val {{ font-size:18px; font-weight:700; display:block; margin-top:4px; }}
    .legend {{ font-size:11px; color:var(--gray); margin-top:8px; text-align:center; }}

    /* Fraud */
    .fraud-summary {{ display:flex; align-items:center; gap:20px; margin-bottom:14px; }}
    .fraud-level {{ font-size:36px; font-weight:700; }}
    .fraud-score {{ font-size:18px; font-weight:600; }}
    .flags-list {{ margin-bottom:10px; }}
    .flag-item {{ padding:6px 10px; font-size:12px; color:var(--dark);
                  margin-bottom:4px; padding-left:14px; }}

    /* Disclaimer */
    .disclaimer {{ font-size:11px; color:var(--gray); margin-top:10px; font-style:italic; }}

    /* Print */
    @media print {{
      body {{ background: white; font-size: 12px; }}
      .report-nav {{ display:none; }}
      .page {{ display:block !important; }}
      .content {{ padding: 10px; }}
    }}
    """

    # ── JavaScript ────────────────────────────────────────────────
    js = """
    function showTab(id) {
      document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
      document.getElementById(id).classList.add('active');
      event.target.classList.add('active');
    }
    document.addEventListener('DOMContentLoaded', function() {
      document.querySelectorAll('.qw-check').forEach(function(cb) {
        cb.addEventListener('change', function() {
          var title = this.nextElementSibling;
          if (this.checked) {
            title.style.textDecoration = 'line-through';
            title.style.opacity = '0.5';
          } else {
            title.style.textDecoration = '';
            title.style.opacity = '';
          }
        });
      });
    });
    """

    # ── Assemble HTML ─────────────────────────────────────────────
    h_score_col = _rag_color(health, 50, 70)
    c_score_col = _rag_color(credit_score, 40, 60)
    f_score_col = _rag_color(fraud_score, 20, 50, invert=True)
    v_score_col = GREEN if val_mid else GRAY
    val_mid_display = (f"{cur} {val_mid:,.0f}") if val_mid else "—"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{biz} — Business Forensics Report</title>
<style>{css}</style>
</head>
<body>

<div class="report-header">
  <span class="report-date">{today}</span>
  <h1>{biz}</h1>
  <div class="sub">{industry}{" · " + country if country else ""} · Imara</div>
</div>

<nav class="report-nav">
  <div class="nav-tab active" onclick="showTab('page-overview')">Overview</div>
  <div class="nav-tab" onclick="showTab('page-situation')">Situation</div>
  <div class="nav-tab" onclick="showTab('page-findings')">Findings</div>
  <div class="nav-tab" onclick="showTab('page-quickwins')">Quick Wins</div>
  <div class="nav-tab" onclick="showTab('page-credit')">Credit</div>
  <div class="nav-tab" onclick="showTab('page-valuation')">Valuation</div>
  <div class="nav-tab" onclick="showTab('page-forecast')">Forecast</div>
  <div class="nav-tab" onclick="showTab('page-fraud')">Fraud Risk</div>
  <div class="nav-tab" onclick="showTab('page-roadmap')">Roadmap</div>
</nav>

<div class="content">

<!-- ── OVERVIEW ───────────────────────────────────────────── -->
<div id="page-overview" class="page active">
  {imara_html}
  {ratios_html}
  <div class="metrics-grid">
    <div class="metric-card">
      <div class="metric-label">Business Health</div>
      <div class="metric-val" style="color:{h_score_col}">{health}</div>
      <div class="metric-sub">Overall score /100</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Credit Grade</div>
      <div class="metric-val" style="color:{c_score_col}">{credit_grade}</div>
      <div class="metric-sub">Score: {credit_score}/100</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Fraud Risk</div>
      <div class="metric-val" style="color:{f_score_col}">{_e(fraud_level).upper()}</div>
      <div class="metric-sub">Score: {fraud_score}/100</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Valuation (mid)</div>
      <div class="metric-val" style="color:{v_score_col};font-size:22px">{val_mid_display}</div>
      <div class="metric-sub">Annual Revenue: {rev_str}</div>
    </div>
  </div>

  <div class="metrics-grid">
    <div class="metric-card">
      <div class="metric-label">Total Findings</div>
      <div class="metric-val" style="color:{NAVY}">{total_f}</div>
      <div class="metric-sub">Across all agents</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Critical</div>
      <div class="metric-val" style="color:{RED}">{critical}</div>
      <div class="metric-sub">Immediate action</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">High Priority</div>
      <div class="metric-val" style="color:{ORANGE}">{high_f}</div>
      <div class="metric-sub">Address this week</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Quick Wins</div>
      <div class="metric-val" style="color:{GREEN}">{quick_w}</div>
      <div class="metric-sub">Under 30 days</div>
    </div>
  </div>

  <div class="bars-section">
    <div class="bars-title">Performance Scorecard</div>
    {score_bars}
  </div>

  {f'<div class="section-block"><h2 class="section-title">EXECUTIVE SUMMARY</h2><p style="font-size:13px;line-height:1.7">{exec_sum}</p></div>' if exec_sum else ""}

  {f'''<div class="section-block">
    <h2 class="section-title">TOP PRIORITY ISSUES</h2>
    {top_issues_html}
  </div>''' if top_issues_html else ""}
</div>

<!-- ── SITUATION ──────────────────────────────────────────── -->
<div id="page-situation" class="page">
  {f'<div class="section-block"><h2 class="section-title">BUSINESS MODEL</h2><p style="font-size:13px;line-height:1.7;color:{DARK}">{biz_summary}</p></div>' if biz_summary else ""}
  <div class="section-block">
    <h2 class="section-title">SITUATION · COMPLICATION · RESOLUTION</h2>
    <div class="scr-grid">
      <div class="scr-col"><h4>Situation</h4><p>{situation or "—"}</p></div>
      <div class="scr-col"><h4>Complication</h4><p>{complication or "—"}</p></div>
      <div class="scr-col"><h4>Resolution</h4><p>{resolution or "—"}</p></div>
    </div>
    <div class="ro-grid">
      <div class="ro-col"><h4 style="color:{RED}">Key Risks</h4><ul>{risk_html}</ul></div>
      <div class="ro-col"><h4 style="color:{GREEN}">Key Opportunities</h4><ul>{opp_html}</ul></div>
    </div>
  </div>
</div>

<!-- ── FINDINGS ───────────────────────────────────────────── -->
<div id="page-findings" class="page">
  <div class="section-block">
    <h2 class="section-title">DEPARTMENT FINDINGS</h2>
    {dept_html or "<p>No findings recorded.</p>"}
  </div>
</div>

<!-- ── QUICK WINS ─────────────────────────────────────────── -->
<div id="page-quickwins" class="page">
  <div class="section-block">
    <h2 class="section-title">QUICK WINS  (Under 30 Days)</h2>
    {quick_wins_html or "<p>No quick wins identified.</p>"}
  </div>
</div>

<!-- ── CREDIT ─────────────────────────────────────────────── -->
<div id="page-credit" class="page">
  {credit_html or '<div class="section-block"><p>Credit readiness data not available.</p></div>'}
</div>

<!-- ── VALUATION ──────────────────────────────────────────── -->
<div id="page-valuation" class="page">
  {val_html or '<div class="section-block"><p>Valuation data not available. Provide audited financials.</p></div>'}
  {tax_html}
</div>

<!-- ── FORECAST ───────────────────────────────────────────── -->
<div id="page-forecast" class="page">
  {forecast_html or '<div class="section-block"><p>Forecast data not available.</p></div>'}
</div>

<!-- ── FRAUD RISK ─────────────────────────────────────────── -->
<div id="page-fraud" class="page">
  {fraud_html}
</div>

<!-- ── ROADMAP ────────────────────────────────────────────── -->
<div id="page-roadmap" class="page">
  {f'<div class="section-block"><h2 class="section-title">STRATEGIC PROGRAMME</h2><p style="font-size:13px;line-height:1.7">{strategic}</p></div>' if strategic else ""}
  <div class="section-block">
    <h2 class="section-title">90-DAY IMPLEMENTATION ROADMAP</h2>
    {roadmap_html or "<p>No roadmap data available.</p>"}
  </div>
</div>

</div><!-- /.content -->

<script>{js}</script>
</body>
</html>"""

    return html
