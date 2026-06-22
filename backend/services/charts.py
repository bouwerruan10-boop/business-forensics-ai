"""
Chart generation for Business Forensics AI PDF reports.
All charts return PNG bytes — ready to embed into ReportLab via io.BytesIO.
Uses a dark navy/gold palette that matches the premium PDF theme.
"""
import io
import math
import matplotlib
matplotlib.use("Agg")   # non-interactive backend — must be set before pyplot import
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Brand colours (matching report_generator.py) ─────────────────
NAVY       = "#0D1B2A"
DARK_CARD  = "#1A2B3C"
GOLD       = "#C9A84C"
GOLD_LIGHT = "#E8C96A"
RED        = "#C0392B"
ORANGE     = "#E67E22"
GREEN      = "#27AE60"
BLUE       = "#2980B9"
GREY       = "#64748B"
TEXT_LIGHT = "#CBD5E1"
WHITE      = "#FFFFFF"

# Severity palette
SEVERITY_COLORS = {
    "critical": RED,
    "high":     ORANGE,
    "medium":   "#F39C12",
    "low":      GREEN,
}

DPI = 150   # resolution for embedded PNGs


def _fig_to_bytes(fig) -> bytes:
    """Serialise a matplotlib figure to PNG bytes and close it."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ── 1. Business Health Score Gauge ────────────────────────────────

def score_gauge(score: int, label: str = "Business Health", width: float = 3.5) -> bytes:
    """
    Semi-circle gauge showing a 0-100 score with colour-coded arc.
    """
    fig, ax = plt.subplots(figsize=(width, width * 0.6),
                           facecolor=DARK_CARD, subplot_kw=dict(polar=False))
    ax.set_facecolor(DARK_CARD)
    ax.set_aspect("equal")
    ax.axis("off")

    score = max(0, min(100, int(score)))
    # Colour based on score range
    if score >= 70:
        arc_color = GREEN
    elif score >= 45:
        arc_color = ORANGE
    else:
        arc_color = RED

    # Background arc
    theta_bg = np.linspace(math.pi, 0, 200)
    ax.plot(np.cos(theta_bg) * 0.85, np.sin(theta_bg) * 0.85,
            color=GREY, linewidth=12, solid_capstyle="round")

    # Score arc
    frac = score / 100
    theta_sc = np.linspace(math.pi, math.pi - frac * math.pi, 200)
    ax.plot(np.cos(theta_sc) * 0.85, np.sin(theta_sc) * 0.85,
            color=arc_color, linewidth=12, solid_capstyle="round")

    # Score text
    ax.text(0, -0.05, str(score), ha="center", va="center",
            fontsize=28, fontweight="bold", color=WHITE)
    ax.text(0, -0.35, label, ha="center", va="center",
            fontsize=9, color=TEXT_LIGHT)

    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-0.55, 1.1)
    return _fig_to_bytes(fig)


# ── 2. Multi-Score Bar Chart ─────────────────────────────────────

def score_bar_chart(scores: dict, width: float = 6.0, height: float = 2.8) -> bytes:
    """
    Horizontal bar chart for 4 business dimension scores.
    Expected keys: business_health, profitability, efficiency, risk.
    """
    labels = []
    values = []
    colors = []
    for key, label in [
        ("business_health_score", "Business Health"),
        ("profitability_score",   "Profitability"),
        ("efficiency_score",      "Efficiency"),
        ("risk_score",            "Risk Management"),
    ]:
        val = scores.get(key, scores.get(key.replace("_score", ""), 0))
        try:
            val = int(val)
        except Exception:
            val = 0
        labels.append(label)
        values.append(val)
        if val >= 70:
            colors.append(GREEN)
        elif val >= 45:
            colors.append(ORANGE)
        else:
            colors.append(RED)

    fig, ax = plt.subplots(figsize=(width, height), facecolor=DARK_CARD)
    ax.set_facecolor(DARK_CARD)

    y_pos = range(len(labels))
    ax.barh(list(y_pos), values, color=colors, height=0.55,
                   zorder=3, linewidth=0)

    # Background bars (full width)
    ax.barh(list(y_pos), [100] * len(labels), color=NAVY,
            height=0.55, zorder=2, linewidth=0)
    # Re-draw coloured bars on top
    ax.barh(list(y_pos), values, color=colors, height=0.55,
            zorder=3, linewidth=0)

    # Value labels
    for i, v in enumerate(values):
        ax.text(v + 1.5, i, str(v), va="center", ha="left",
                color=WHITE, fontsize=10, fontweight="bold")

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(labels, color=TEXT_LIGHT, fontsize=10)
    ax.set_xlim(0, 115)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.tick_params(axis="x", colors=GREY, labelsize=8)
    ax.spines[:].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Score / 100", color=GREY, fontsize=8)
    ax.grid(axis="x", color=GREY, alpha=0.2, zorder=1)

    fig.tight_layout(pad=0.5)
    return _fig_to_bytes(fig)


# ── 3. Findings Severity Breakdown (Donut) ───────────────────────

def severity_donut(findings: list, width: float = 4.0) -> bytes:
    """Donut chart showing breakdown of finding severities."""
    findings = findings or []          # tolerate None / missing (caller is wrapped in try/except)
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev = (f.get("severity") or "medium").lower()
        if sev in counts:
            counts[sev] += 1
        else:
            counts["medium"] += 1

    # Only include non-zero slices
    labels = [k.capitalize() for k, v in counts.items() if v > 0]
    values = [v for v in counts.values() if v > 0]
    colors = [SEVERITY_COLORS[k] for k, v in counts.items() if v > 0]

    if not values:
        values = [1]
        labels = ["No Findings"]
        colors = [GREY]

    fig, ax = plt.subplots(figsize=(width, width * 0.85), facecolor=DARK_CARD)
    ax.set_facecolor(DARK_CARD)

    wedges, texts, autotexts = ax.pie(
        values, labels=None, colors=colors,
        autopct="%1.0f%%", startangle=90,
        wedgeprops=dict(width=0.45, edgecolor=DARK_CARD, linewidth=2),
        pctdistance=0.75,
    )
    for at in autotexts:
        at.set_color(WHITE)
        at.set_fontsize(9)
        at.set_fontweight("bold")

    ax.legend(
        wedges, [f"{l} ({v})" for l, v in zip(labels, values)],
        loc="lower center", bbox_to_anchor=(0.5, -0.12),
        ncol=2, fontsize=8, frameon=False,
        labelcolor=TEXT_LIGHT,
    )
    ax.set_title("Finding Severity", color=GOLD, fontsize=10, pad=8)
    return _fig_to_bytes(fig)


# ── 4. Benchmark Comparison Bar Chart ────────────────────────────

def benchmark_bar(client_metrics: dict, benchmarks: dict,
                  width: float = 6.5, height: float = 3.5) -> bytes:
    """
    Side-by-side bars comparing client metrics vs industry benchmarks.
    client_metrics and benchmarks are dicts of {label: float_value}.
    """
    labels = list(client_metrics.keys())
    client_vals = [float(client_metrics.get(k, 0)) for k in labels]
    bench_vals  = [float(benchmarks.get(k, 0))      for k in labels]

    if not labels:
        return _empty_chart("No benchmark data available", width, height)

    x = np.arange(len(labels))
    bar_w = 0.35

    fig, ax = plt.subplots(figsize=(width, height), facecolor=DARK_CARD)
    ax.set_facecolor(DARK_CARD)

    ax.bar(x - bar_w / 2, client_vals, bar_w, label="This business",
           color=GOLD, zorder=3)
    ax.bar(x + bar_w / 2, bench_vals,  bar_w, label="Industry benchmark",
           color=BLUE, zorder=3, alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, color=TEXT_LIGHT, fontsize=9, rotation=15, ha="right")
    ax.tick_params(axis="y", colors=GREY, labelsize=8)
    ax.spines[:].set_visible(False)
    ax.grid(axis="y", color=GREY, alpha=0.2, zorder=1)
    ax.legend(fontsize=8, frameon=False, labelcolor=TEXT_LIGHT)
    ax.set_title("Client vs Industry Benchmark", color=GOLD, fontsize=10, pad=8)

    fig.tight_layout(pad=0.5)
    return _fig_to_bytes(fig)


# ── 5. 90-Day Roadmap Timeline ────────────────────────────────────

def roadmap_timeline(phases: list, width: float = 7.0, height: float = 2.5) -> bytes:
    """
    Horizontal Gantt-style timeline for the 3 implementation phases.
    phases: list of {phase, focus, timeframe} dicts from the report.
    """
    if not phases:
        return _empty_chart("No roadmap data", width, height)

    fig, ax = plt.subplots(figsize=(width, height), facecolor=DARK_CARD)
    ax.set_facecolor(DARK_CARD)
    ax.axis("off")

    colours = [GOLD, ORANGE, BLUE]
    n = len(phases)
    bar_h = 0.4
    seg_w = 1.0 / max(n, 1)

    for i, phase in enumerate(phases):
        x_start = i * seg_w
        color = colours[i % len(colours)]
        rect = mpatches.FancyBboxPatch(
            (x_start + 0.01, 0.35), seg_w - 0.02, bar_h,
            boxstyle="round,pad=0.01",
            facecolor=color, edgecolor=DARK_CARD, linewidth=1,
            transform=ax.transAxes, clip_on=False,
        )
        ax.add_patch(rect)

        label = phase.get("phase", f"Phase {i+1}")
        focus = phase.get("focus", "")
        ax.text(x_start + seg_w / 2, 0.83, label,
                ha="center", va="center", transform=ax.transAxes,
                color=WHITE, fontsize=9, fontweight="bold")
        ax.text(x_start + seg_w / 2, 0.18, focus,
                ha="center", va="center", transform=ax.transAxes,
                color=TEXT_LIGHT, fontsize=7.5, wrap=True)

    ax.set_title("90-Day Implementation Roadmap", color=GOLD,
                 fontsize=10, pad=4, loc="left")
    return _fig_to_bytes(fig)


# ── Helpers ───────────────────────────────────────────────────────

def _empty_chart(message: str, width: float, height: float) -> bytes:
    fig, ax = plt.subplots(figsize=(width, height), facecolor=DARK_CARD)
    ax.set_facecolor(DARK_CARD)
    ax.axis("off")
    ax.text(0.5, 0.5, message, ha="center", va="center",
            transform=ax.transAxes, color=GREY, fontsize=10)
    return _fig_to_bytes(fig)


# ── Convenience: generate all charts for a report ────────────────

def generate_report_charts(report: dict) -> dict:
    """
    Given a complete analysis report dict, generate all chart PNGs.
    Returns {chart_name: png_bytes}.
    """
    scores = report.get("scores", {})
    # Also check top-level score fields
    for key in ("business_health_score", "profitability_score",
                "efficiency_score", "risk_score"):
        if key not in scores and key in report:
            scores[key] = report[key]

    charts = {}

    # 1. Score gauges (4 individual)
    for key, label in [
        ("business_health_score", "Business Health"),
        ("profitability_score",   "Profitability"),
        ("efficiency_score",      "Efficiency"),
        ("risk_score",            "Risk Mgmt"),
    ]:
        val = scores.get(key, 0)
        charts[f"gauge_{key}"] = score_gauge(val, label, width=2.8)

    # 2. Combined score bar
    charts["score_bars"] = score_bar_chart(scores)

    # 3. Severity donut
    all_findings = []
    for dept_findings in report.get("department_findings", {}).values():
        if isinstance(dept_findings, list):
            all_findings.extend(dept_findings)
    charts["severity_donut"] = severity_donut(all_findings)

    # 4. Roadmap timeline
    roadmap = report.get("implementation_roadmap", [])
    if roadmap:
        charts["roadmap_timeline"] = roadmap_timeline(roadmap)

    return charts
