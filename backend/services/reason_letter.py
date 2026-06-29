"""
Adverse-action / reason letter — a portable artifact the SME receives.

Dossier H3/D2: the "why this score" reason codes + POPIA s71(3) disclosure existed only as an
in-dashboard panel / report section. This packages them into a standalone letter (HTML + PDF) the
SME can be given — the principal factors holding the score back (ordered by impact), the supporting
strengths, and the right to contest.

FRAMING (load-bearing): the Imara Score is decision-support — Imara does NOT make the credit
decision. So this is an *explanation of the Score's principal factors* that a credit provider can
use to SUPPORT its own adverse-action / reason-for-decision notice (NCA s62 / ECOA); it is not
itself an adverse-action notice issued by Imara. Deterministic — reuses reason_codes via
build_disclosure; no LLM, no new numbers.
"""
import html as _html
from datetime import date

from services.score_disclosure import build_disclosure

__all__ = ["build_reason_letter", "render_reason_letter_html"]


def build_reason_letter(report) -> dict:
    """Assemble the reason-letter content from the POPIA s71(3) disclosure. Pure; never raises."""
    try:
        d = build_disclosure(report)
    except Exception:
        d = {"available": False}
    if not isinstance(d, dict) or not d.get("available"):
        return {"available": False, "reason": "No Imara Score components to explain."}
    biz = (report or {}).get("business_name") or "the business"
    reasons = [r for r in (d.get("principal_reasons") or []) if isinstance(r, dict)]
    strengths = [s for s in (d.get("strengths") or []) if isinstance(s, dict)]
    rights = d.get("your_rights") or {}
    return {
        "available": True,
        "title": "Imara Score — Explanation of Principal Factors",
        "business_name": biz,
        "generated_on": date.today().strftime("%d %B %Y"),
        "score": d.get("score"),
        "band": d.get("band"),
        "label": d.get("label"),
        "intro": ("This letter explains the principal factors affecting the Imara Score for %s. The "
                  "Imara Score is a 0-100 decision-support rating that a lender considers alongside its "
                  "own assessment. The factors below are the main reasons the score was not higher, in "
                  "order of impact, each tied to the underlying figure." % biz),
        "principal_reasons": reasons,
        "strengths": strengths,
        "rights": rights,
        "how_to_contest": rights.get("make_representations"),
        "basis": ("Provided to support a credit provider's own adverse-action / reason-for-decision "
                  "notice (e.g. NCA s62 / ECOA). The Imara Score is decision-support; Imara does not "
                  "make the credit decision — a human credit provider does."),
        "disclaimer": d.get("disclaimer"),
    }


def _e(t):
    return _html.escape(str(t if t is not None else ""), quote=True)


def render_reason_letter_html(report) -> str:
    """Self-contained, emailable HTML reason letter (inline styles, all values escaped)."""
    L = build_reason_letter(report)
    if not L.get("available"):
        return ("<!doctype html><meta charset='utf-8'><div style='font-family:Arial;padding:24px;color:#555'>"
                "No Imara Score factors are available to explain for this analysis.</div>")
    navy, gold, gray, green = "#0D1B2A", "#C9A84C", "#888888", "#1A7A40"
    reasons = "".join(
        "<li style='margin-bottom:8px;color:%s'><b>%s</b> <span style='color:%s'>(%s/100)</span><br>"
        "<span style='font-size:13px;color:%s'>%s</span></li>" % (
            navy, _e(r.get("factor")), gray, _e(r.get("score")), gray, _e(r.get("detail")))
        for r in L["principal_reasons"][:6]) or \
        "<li style='color:%s'>No single factor is materially holding the score back.</li>" % green
    strengths = ""
    if L["strengths"]:
        strengths = ("<p style='font-weight:700;color:%s;margin-top:18px'>What is supporting the score</p>"
                     "<p style='color:%s'>%s</p>" % (
                         navy, gray, _e(", ".join("%s (%s/100)" % (s.get("factor"), s.get("score"))
                                                  for s in L["strengths"][:4]))))
    contest = ""
    if L.get("how_to_contest"):
        contest = ("<div style='background:%s11;border:1px solid %s55;border-radius:8px;padding:12px 14px;"
                   "margin-top:18px;font-size:13px;color:#333'><b style='color:%s'>Your right to contest.</b> %s</div>"
                   % (green, green, navy, _e(L["how_to_contest"])))
    band = (" &middot; band %s" % _e(L["band"])) if L.get("band") else ""
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>%s</title></head>"
        "<body style='font-family:Arial,Helvetica,sans-serif;max-width:720px;margin:0 auto;padding:32px;color:%s'>"
        "<div style='border-bottom:3px solid %s;padding-bottom:10px;margin-bottom:18px'>"
        "<div style='font-size:11px;letter-spacing:2px;color:%s'>IMARA</div>"
        "<h1 style='font-size:20px;margin:6px 0 2px'>%s</h1>"
        "<div style='font-size:13px;color:%s'>%s &middot; %s</div></div>"
        "<p style='color:#333'>%s</p>"
        "<p style='font-weight:700;color:%s;margin:18px 0 6px'>Imara Score: %s%s</p>"
        "<p style='font-weight:700;color:%s;margin:12px 0 6px'>Principal factors (in order of impact)</p>"
        "<ul style='padding-left:18px;line-height:1.5'>%s</ul>"
        "%s%s"
        "<p style='font-size:12px;color:%s;margin-top:22px;border-top:1px solid #eee;padding-top:12px'>%s</p>"
        "<p style='font-size:11px;color:%s;font-style:italic'>%s</p>"
        "</body></html>" % (
            _e(L["title"]), navy, gold, gold,
            _e(L["title"]), gray, _e(L["business_name"]), _e(L["generated_on"]),
            _e(L["intro"]),
            navy, _e(L["score"]), band,
            navy, reasons, strengths, contest,
            gray, _e(L["basis"]), gray, _e(L["disclaimer"])))
