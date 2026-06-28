"""
sars_fetch.py - polite, single-URL, on-demand fetch of one SARS rate page.

NOT a crawler/spider. It fetches ONE allowlisted SARS rate URL per explicit call, with a
transparent User-Agent + contact, a timeout, conditional GET (ETag / If-Modified-Since)
against a small in-process cache, and a single light retry. PDFs (the interest tables)
are extracted to text with pdfplumber (already a dependency).

Compliance note: SARS's Terms & Conditions (s4.8.2) prohibit web crawlers/spiders and
license content for non-commercial use. This helper is therefore deliberately minimal -
operator-initiated, one page at a time, cached to avoid re-fetching - and the product's
real logic is the offline diff engine (sars_rate_check.py), which also accepts content
the operator supplies manually. Use respectfully and review SARS's terms before relying
on automated fetching.
"""

import io
import os

from services.sars_rate_manifest import PAGES

# Only these (the manifest's pages) may be fetched - never an arbitrary URL.
_ALLOWLIST = set(PAGES.values())

_UA = os.environ.get(
    "SARS_FETCH_USER_AGENT",
    "ImaraRateCurrencyChecker/1.0 (internal compliance verification; contact: ops@imara.local)")

# in-process conditional-GET cache: url -> {"etag", "last_modified", "text"}
_CACHE = {}


def _pdf_to_text(content_bytes):
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages[:20])
    except Exception:
        return ""


def fetch_page(url, timeout=15.0) -> dict:
    """Fetch ONE allowlisted SARS page politely. Returns {url, ok, text, from_cache,
    status_code, error}. Honours ETag/If-Modified-Since; never raises."""
    if url not in _ALLOWLIST:
        return {"url": url, "ok": False, "error": "URL not in the SARS rate-page allowlist.",
                "text": "", "from_cache": False}
    try:
        import httpx
    except Exception as exc:
        return {"url": url, "ok": False, "error": "httpx unavailable: {}".format(exc),
                "text": "", "from_cache": False}

    cached = _CACHE.get(url) or {}
    headers = {"User-Agent": _UA, "Accept": "text/html,application/pdf,*/*"}
    if cached.get("etag"):
        headers["If-None-Match"] = cached["etag"]
    if cached.get("last_modified"):
        headers["If-Modified-Since"] = cached["last_modified"]

    last_err = None
    for attempt in range(2):                       # one light retry, no aggressive looping
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
            if resp.status_code == 304 and cached.get("text") is not None:
                return {"url": url, "ok": True, "text": cached["text"], "from_cache": True,
                        "status_code": 304, "error": None}
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "").lower()
            text = _pdf_to_text(resp.content) if "pdf" in ctype or url.lower().endswith(".pdf") else resp.text
            _CACHE[url] = {"etag": resp.headers.get("etag"),
                           "last_modified": resp.headers.get("last-modified"), "text": text}
            return {"url": url, "ok": True, "text": text, "from_cache": False,
                    "status_code": resp.status_code, "error": None}
        except Exception as exc:
            last_err = str(exc)
    return {"url": url, "ok": False, "text": "", "from_cache": False, "error": last_err}


def fetch_pages(page_ids=None) -> dict:
    """Fetch the requested manifest pages (default: all) and return {page_id: text} for
    pages that fetched OK, plus an `_errors` map. Polite single-URL calls in sequence."""
    ids = page_ids if isinstance(page_ids, (list, tuple)) else list(PAGES.keys())
    out, errors = {}, {}
    for pid in ids:
        url = PAGES.get(pid)
        if not url:
            errors[pid] = "unknown page id"
            continue
        res = fetch_page(url)
        if res["ok"]:
            out[pid] = res["text"]
        else:
            errors[pid] = res["error"]
    if errors:
        out["_errors"] = errors
    return out
