"""
Bright Data live-fallback for supplier benchmarking — the "live" half of the hybrid.

OFF by default and OFF the hot analysis path. When enabled (SUPPLIER_LIVE_ENABLED=true
+ BRIGHTDATA_API_KEY), it augments a curated opportunity with CITED current pricing
pulled via the Bright Data SERP API, so a switch suggestion can show a live, dated,
sourced reference instead of only the curated band. Fails closed: any error returns
gracefully and the curated result stands. Never invents a price — every live figure
carries its source URL + retrieval date.

Activation (production): set SUPPLIER_LIVE_ENABLED=true, BRIGHTDATA_API_KEY=<key>,
optionally BRIGHTDATA_SERP_ZONE (default "serp"). Then call /supplier-savings?live=true.
"""
import os
from datetime import date


def live_enabled() -> bool:
    return (os.getenv("SUPPLIER_LIVE_ENABLED", "").lower() in ("1", "true", "yes")
            and bool(os.getenv("BRIGHTDATA_API_KEY")))


def _today() -> str:
    return date.today().isoformat()


def fetch_live_pricing(category: str, providers: list, region: str = "South Africa", limit: int = 3) -> dict:
    """Return live, cited pricing references for the named providers in a category.

    {enabled: False, reason} when off; {enabled: True, results:[{provider,title,url,snippet,as_of}]}
    when on. Designed to never raise into the caller.
    """
    if not live_enabled():
        return {"enabled": False,
                "reason": "Live supplier pricing is off (set SUPPLIER_LIVE_ENABLED=true + BRIGHTDATA_API_KEY)."}
    try:
        import requests
        key = os.getenv("BRIGHTDATA_API_KEY")
        zone = os.getenv("BRIGHTDATA_SERP_ZONE", "serp")
        cat = category.replace("_", " ")
        results = []
        for prov in (providers or [])[:limit]:
            q = "{} {} pricing {}".format(prov, cat, region)
            url = "https://www.google.com/search?q=" + requests.utils.quote(q) + "&brd_json=1"
            r = requests.post(
                "https://api.brightdata.com/request",
                json={"zone": zone, "url": url, "format": "json"},
                headers={"Authorization": "Bearer " + key},
                timeout=20,
            )
            if not r.ok:
                continue
            data = r.json()
            top = (data.get("organic") or [])[:1]
            for o in top:
                results.append({
                    "provider": prov,
                    "title": o.get("title"),
                    "url": o.get("link"),
                    "snippet": (o.get("description") or "")[:200],
                    "as_of": _today(),
                })
        return {"enabled": True, "results": results,
                "source": "Bright Data SERP API (live, cited)", "as_of": _today()}
    except Exception as e:  # fail closed — curated result stands
        return {"enabled": True, "error": str(e)[:160], "results": []}


def augment(benchmark: dict, max_categories: int = 6) -> dict:
    """Enrich a curated supplier_benchmark result in place with live cited pricing for
    the top substitutable opportunities. No-op when live is disabled."""
    if not benchmark or not benchmark.get("available") or not live_enabled():
        if benchmark is not None:
            benchmark["live"] = {"enabled": False}
        return benchmark
    enriched = 0
    for opp in benchmark.get("opportunities", []):
        if enriched >= max_categories:
            break
        if opp.get("alternatives"):
            live = fetch_live_pricing(opp["category"], opp["alternatives"])
            if live.get("results"):
                opp["live_pricing"] = live["results"]
                enriched += 1
    benchmark["live"] = {"enabled": True, "categories_enriched": enriched, "as_of": _today()}
    return benchmark
