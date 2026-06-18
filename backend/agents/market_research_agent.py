"""
Market Research Agent — two-phase live intelligence gathering.

Phase 1 (MarketResearchAgent / quick scan):
  Runs BEFORE all specialist agents. Searches company name + industry trends,
  builds a compact market_context_summary injected into every subsequent agent's prompt.

Phase 2 (MarketDeepDiveAgent / full analysis):
  Runs AFTER all specialist agents. Comprehensive search across news, social,
  competitors, reviews, and public reputation. Produces market findings + score.

Live search: Serper.dev REST API (Google Search + News).
Graceful fallback: if SERPER_API_KEY is absent, Claude's knowledge fills the gap.
"""

import json
import httpx
import os
from agents.base_agent import BaseAgent, _http_client
from memory.shared_memory import SharedMemory, AgentFinding
from config import MOCK_MODE, SERPER_API_KEY

SERPER_SEARCH_URL = "https://google.serper.dev/search"
SERPER_NEWS_URL   = "https://google.serper.dev/news"
SERPER_TIMEOUT    = 10.0   # seconds per request


# ── Serper helpers ────────────────────────────────────────────────────────────

def _serper_search(query: str, country_code: str = "za", num: int = 10) -> dict:
    """
    Call Serper.dev /search. Returns parsed JSON or {} on any error.
    country_code: ISO-2 country code for Google localisation (za, ng, ke, zw, us …)
    """
    if not SERPER_API_KEY:
        return {}
    try:
        resp = _http_client.post(
            SERPER_SEARCH_URL,
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": num, "gl": country_code},
            timeout=SERPER_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


def _serper_news(query: str, country_code: str = "za", num: int = 10) -> dict:
    """Call Serper.dev /news. Returns parsed JSON or {} on any error."""
    if not SERPER_API_KEY:
        return {}
    try:
        resp = _http_client.post(
            SERPER_NEWS_URL,
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": num, "gl": country_code},
            timeout=SERPER_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


def _country_code(country: str) -> str:
    """Map country name to ISO-2 code for Serper localisation."""
    mapping = {
        "south africa": "za", "nigeria": "ng", "kenya": "ke",
        "zimbabwe": "zw", "ghana": "gh", "tanzania": "tz",
        "egypt": "eg", "ethiopia": "et", "rwanda": "rw",
        "uganda": "ug", "zambia": "zm", "botswana": "bw",
    }
    return mapping.get((country or "").lower().strip(), "za")


def _extract_organic(data: dict) -> list[dict]:
    """Pull organic results list from Serper response."""
    return data.get("organic", [])


def _extract_news_items(data: dict) -> list[dict]:
    """Pull news items from Serper news response."""
    return data.get("news", [])


# ── Mock data (MOCK_MODE=true) ────────────────────────────────────────────────

def _mock_market_data(memory: SharedMemory) -> dict:
    return {
        "visibility_score": 38,
        "sentiment": "neutral",
        "news": [
            {
                "title": f"{memory.business_name} expands operations in {memory.country or 'the region'}",
                "source": "Business Daily",
                "snippet": "The company recently announced new hires and a location expansion.",
                "url": "https://example.com/news/1",
                "date": "2026-06-01",
            }
        ],
        "competitors": ["Competitor A", "Competitor B", "Competitor C"],
        "opportunities": [
            "Growing e-commerce adoption in target market",
            "Underserved SME segment with limited competition",
        ],
        "risks": [
            "Low brand visibility versus established competitors",
            "Limited digital presence reduces inbound lead flow",
        ],
        "total_results": 4,
        "search_performed": True,
        "context_summary": (
            f"{memory.business_name} has limited online presence (visibility score 38/100). "
            f"The {memory.industry or memory.industry_key} sector shows moderate growth. "
            "3 named competitors identified. Sentiment: neutral."
        ),
    }


# ── Phase 1: Quick Scan ───────────────────────────────────────────────────────

class MarketResearchAgent(BaseAgent):
    """
    Quick scan — runs BEFORE specialist agents.
    Writes market_context_summary to SharedMemory so every
    subsequent agent has live market context in its prompt.
    """
    name = "Market Research Agent"
    system_prompt = """You are a senior market intelligence analyst.
Your task is to synthesise raw web search data about a business and its industry
into a concise, factual market context summary.
Focus on: online visibility, public reputation, industry trends, and named competitors.
Be precise. Do not invent information not present in the search results.
If data is sparse, say so explicitly."""

    def analyze(self, business_data: dict, memory: SharedMemory) -> list[AgentFinding]:
        """Quick scan — populates market_context_summary only. No findings produced here."""
        if MOCK_MODE:
            mock = _mock_market_data(memory)
            memory.market_context_summary = mock["context_summary"]
            memory.market_search_performed = True
            return []

        cc = _country_code(memory.country)
        name = memory.business_name
        industry = memory.industry or memory.industry_key or "business"

        # Search 1: company name presence
        company_data  = _serper_search(f'"{name}"', cc, num=5)
        # Search 2: industry trends in country
        industry_data = _serper_search(
            f"{industry} industry trends {memory.country or 'Africa'} 2025 2026", cc, num=5
        )

        organic_count = len(_extract_organic(company_data))
        industry_results = _extract_organic(industry_data)

        memory.market_total_results = organic_count
        memory.market_search_performed = True

        # Build a compact context for specialist agents
        if not SERPER_API_KEY:
            # No key — use Claude knowledge only
            context = self._claude_industry_context(memory)
        else:
            context = self._build_context_summary(
                name, industry, memory.country, organic_count, industry_results
            )

        memory.market_context_summary = context
        return []   # Quick scan produces no findings — findings come in Phase 2

    def _build_context_summary(
        self, name: str, industry: str, country: str,
        organic_count: int, industry_results: list
    ) -> str:
        presence = (
            f"Found {organic_count} search result(s) for '{name}' online."
            if organic_count > 0
            else f"No search results found for '{name}' — company has minimal online presence."
        )
        trend_snippets = "; ".join(
            r.get("snippet", "")[:120] for r in industry_results[:3] if r.get("snippet")
        )
        trend_line = f"Industry context ({industry}): {trend_snippets}" if trend_snippets else ""
        return " | ".join(filter(None, [presence, trend_line]))

    def _claude_industry_context(self, memory: SharedMemory) -> str:
        prompt = (
            f"In 2–3 sentences, summarise the current market conditions for a "
            f"{memory.industry or memory.industry_key} business operating in "
            f"{memory.country or 'Sub-Saharan Africa'}. Focus on growth trends, "
            f"key challenges, and competitive landscape. Be factual and concise."
        )
        try:
            return self._call_claude(prompt)[:400]
        except Exception:
            return f"{memory.industry or memory.industry_key} market context unavailable."


# ── Phase 2: Deep Dive ────────────────────────────────────────────────────────

class MarketDeepDiveAgent(BaseAgent):
    """
    Full market analysis — runs AFTER all specialist agents.
    Produces structured findings, visibility score, sentiment, competitors.
    """
    name = "Market Intelligence Agent"
    system_prompt = """You are a senior market intelligence and brand strategy consultant.
You analyse web search data, news coverage, social media signals, and competitor landscapes
to deliver precise, actionable market intelligence for SME business owners.

Rules:
- Only state facts supported by the search data provided.
- When data is absent, say so clearly — never invent mentions or competitors.
- Quantify where possible: number of articles, number of results, sentiment ratio.
- Frame low online presence as a business risk with commercial impact.
- Identify specific, named competitors only if found in search results.
- Strategic recommendations must be actionable within 90 days."""

    def analyze(self, business_data: dict, memory: SharedMemory) -> list[AgentFinding]:
        if MOCK_MODE:
            mock = _mock_market_data(memory)
            self._apply_mock(memory, mock)
            return self._mock_findings(memory)

        cc    = _country_code(memory.country)
        name  = memory.business_name
        ind   = memory.industry or memory.industry_key or "business"
        ctry  = memory.country or "Africa"

        search_data = self._run_searches(name, ind, ctry, cc)
        score, sentiment = self._calculate_visibility(search_data)
        news_items  = self._extract_news(search_data)
        competitors = self._extract_competitors(search_data, name)

        memory.market_visibility_score = score
        memory.market_sentiment = sentiment
        memory.market_news = news_items
        memory.market_competitors = competitors
        memory.market_total_results = search_data.get("total_results", 0)

        analysis = self._claude_analysis(name, ind, ctry, score, sentiment, search_data)
        structured = self._extract_market_intel(analysis, memory)

        memory.market_opportunities = structured.get("opportunities", [])
        memory.market_risks = structured.get("risks", [])

        findings = self._build_findings(name, score, sentiment, structured, memory, search_data)
        return findings

    # ── Search orchestration ──────────────────────────────────────

    def _run_searches(self, name: str, industry: str, country: str, cc: str) -> dict:
        """Run all 6 searches and return aggregated raw data."""
        results = {}

        if SERPER_API_KEY:
            results["company_organic"] = _serper_search(f'"{name}"', cc, num=10)
            results["company_news"]    = _serper_news(f'"{name}"', cc, num=10)
            results["company_reviews"] = _serper_search(f'"{name}" reviews OR rating OR feedback', cc, num=5)
            results["company_social"]  = _serper_search(f'"{name}" site:twitter.com OR site:linkedin.com OR site:facebook.com', cc, num=5)
            results["industry_trends"] = _serper_search(f"{industry} market trends {country} 2025 2026", cc, num=8)
            results["competitors"]     = _serper_search(f"top {industry} companies {country}", cc, num=8)

        total = sum(
            len(_extract_organic(v)) + len(_extract_news_items(v))
            for v in results.values()
        )
        results["total_results"] = total
        return results

    # ── Scoring ───────────────────────────────────────────────────

    def _calculate_visibility(self, data: dict) -> tuple[int, str]:
        """Compute market visibility score (0-100) and overall sentiment."""
        score = 0

        organic  = _extract_organic(data.get("company_organic", {}))
        news     = _extract_news_items(data.get("company_news", {}))
        reviews  = _extract_organic(data.get("company_reviews", {}))
        social   = _extract_organic(data.get("company_social", {}))

        if not SERPER_API_KEY:
            return 0, "unknown"

        # Online presence
        if len(organic) >= 5: score += 30
        elif len(organic) >= 1: score += 15

        # News coverage
        if len(news) >= 3: score += 20
        elif len(news) >= 1: score += 10

        # Reviews / reputation
        if len(reviews) >= 2: score += 15
        elif len(reviews) >= 1: score += 8

        # Social presence
        if len(social) >= 2: score += 15
        elif len(social) >= 1: score += 8

        # Website / brand indicators
        all_snippets = " ".join(
            (r.get("snippet", "") + " " + r.get("title", "")).lower()
            for r in organic + news + reviews
        )
        positive_words = ["award", "growth", "expansion", "launch", "partner", "success", "trusted", "leading"]
        negative_words = ["scam", "fraud", "complaint", "lawsuit", "scandal", "bankrupt", "closure", "fail"]

        pos_count = sum(all_snippets.count(w) for w in positive_words)
        neg_count = sum(all_snippets.count(w) for w in negative_words)

        if pos_count > neg_count and pos_count > 0:
            score += 10
            sentiment = "positive"
        elif neg_count > pos_count and neg_count > 0:
            score -= 10
            sentiment = "negative"
        elif len(organic) + len(news) > 0:
            score += 5
            sentiment = "neutral"
        else:
            sentiment = "unknown"

        return max(0, min(100, score)), sentiment

    # ── Extraction helpers ────────────────────────────────────────

    def _extract_news(self, data: dict) -> list[dict]:
        items = []
        for article in _extract_news_items(data.get("company_news", {}))[:8]:
            items.append({
                "title":   article.get("title", ""),
                "source":  article.get("source", ""),
                "snippet": article.get("snippet", ""),
                "url":     article.get("link", ""),
                "date":    article.get("date", ""),
            })
        return items

    def _extract_competitors(self, data: dict, company_name: str) -> list[str]:
        """Extract named competitors from industry search results."""
        competitors = []
        seen = set()
        comp_lower = company_name.lower()
        for r in _extract_organic(data.get("competitors", {})):
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            # Skip the company itself
            if comp_lower in title.lower() or comp_lower in snippet.lower():
                continue
            # Extract company-like names from titles (capitalised words, 2-4 words)
            words = title.split()
            if len(words) >= 2:
                candidate = " ".join(words[:3])
                if candidate not in seen and len(candidate) > 3:
                    competitors.append(candidate)
                    seen.add(candidate)
            if len(competitors) >= 6:
                break
        return competitors

    # ── Claude analysis ───────────────────────────────────────────

    def _claude_analysis(
        self, name: str, industry: str, country: str,
        score: int, sentiment: str, search_data: dict
    ) -> str:
        organic_snippets = "\n".join(
            f"- [{r.get('title','')}] {r.get('snippet','')}"
            for r in _extract_organic(search_data.get("company_organic", {}))[:6]
        ) or "(no organic results found)"

        news_snippets = "\n".join(
            f"- [{n.get('source','')}: {n.get('date','')}] {n.get('title','')} — {n.get('snippet','')}"
            for n in _extract_news_items(search_data.get("company_news", {}))[:5]
        ) or "(no news articles found)"

        review_snippets = "\n".join(
            f"- {r.get('snippet','')}"
            for r in _extract_organic(search_data.get("company_reviews", {}))[:4]
        ) or "(no reviews found)"

        social_snippets = "\n".join(
            f"- {r.get('title','')} — {r.get('snippet','')}"
            for r in _extract_organic(search_data.get("company_social", {}))[:4]
        ) or "(no social media presence found)"

        industry_snippets = "\n".join(
            f"- {r.get('snippet','')}"
            for r in _extract_organic(search_data.get("industry_trends", {}))[:4]
        ) or "(no industry trend data found)"

        competitor_snippets = "\n".join(
            f"- {r.get('title','')}: {r.get('snippet','')}"
            for r in _extract_organic(search_data.get("competitors", {}))[:5]
        ) or "(no competitor data found)"

        no_key_note = (
            "\n\nNOTE: No live search API key is configured. "
            "Use your training knowledge to provide market context for this industry and country. "
            "Be clear about what is known vs estimated.\n"
            if not SERPER_API_KEY else ""
        )

        prompt = f"""Conduct a market intelligence analysis for this business:

Business: {name}
Industry: {industry}
Country: {country}
Market Visibility Score: {score}/100
Overall Sentiment: {sentiment}
{no_key_note}
=== SEARCH DATA ===

COMPANY SEARCH RESULTS (Google organic):
{organic_snippets}

NEWS COVERAGE:
{news_snippets}

REVIEWS & PUBLIC FEEDBACK:
{review_snippets}

SOCIAL MEDIA PRESENCE:
{social_snippets}

INDUSTRY TRENDS ({industry}, {country}):
{industry_snippets}

COMPETITOR LANDSCAPE:
{competitor_snippets}

=== YOUR ANALYSIS ===

Produce a comprehensive market intelligence analysis covering:

1. BRAND VISIBILITY: How visible is this company online? Is this appropriate for their size and sector?
2. PUBLIC SENTIMENT: What does the public think? Any positive or negative signals?
3. NEWS & MEDIA: Is this company trending? What are the most recent stories?
4. COMPETITOR LANDSCAPE: Who are the key competitors? How does this company compare?
5. MARKET OPPORTUNITIES: What specific market opportunities exist for this business right now?
6. MARKET RISKS: What market-level threats could harm this business?
7. STRATEGIC RECOMMENDATIONS: 3 specific, actionable steps to improve market position within 90 days.

If there is NO online data for the company, be explicit about this and frame it as a business risk.
Cite specific evidence from the search data wherever possible. Do not invent facts."""

        try:
            return self._call_claude(prompt)
        except Exception as e:
            return f"Market analysis unavailable: {e}"

    def _extract_market_intel(self, analysis_text: str, memory: SharedMemory) -> dict:
        """Use a second Claude call to extract structured market intel from the analysis."""
        parse_prompt = f"""Extract structured market intelligence from this analysis.

ANALYSIS:
{analysis_text}

Return a JSON object with exactly these keys:
{{
  "opportunities": ["string — max 15 words each, 2-4 items"],
  "risks": ["string — max 15 words each, 2-4 items"],
  "competitor_names": ["string — company names only, 0-6 items"],
  "strategic_actions": ["string — actionable, max 20 words each, 3 items"],
  "sentiment_summary": "string — one sentence on public perception"
}}

Return ONLY valid JSON. No markdown. No explanation."""
        try:
            raw = self._call_claude(parse_prompt).strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip().rstrip("`").strip()
            return json.loads(raw)
        except Exception:
            return {
                "opportunities": [],
                "risks": ["Limited market data available — manual research recommended"],
                "competitor_names": [],
                "strategic_actions": ["Conduct manual competitor analysis", "Build Google Business Profile", "Develop content marketing strategy"],
                "sentiment_summary": "Insufficient public data to determine sentiment.",
            }

    # ── Finding builder ───────────────────────────────────────────

    def _build_findings(
        self, name: str, score: int, sentiment: str,
        structured: dict, memory: SharedMemory, search_data: dict
    ) -> list[AgentFinding]:
        findings = []

        # Finding 1: Brand Visibility
        if score == 0 and not SERPER_API_KEY:
            vis_detail = (
                f"No live market search was performed for {name} because the SERPER_API_KEY "
                f"is not configured. Market visibility is unverified. Add a Serper.dev API key "
                f"to Railway environment variables to enable live market research."
            )
            vis_severity = "medium"
            vis_impact = "Unquantified — live search not available"
            vis_rec = "Configure SERPER_API_KEY in Railway Variables to enable live market intelligence."
            vis_roi = "Full market scan available immediately once key is added"
        elif score < 20:
            vis_detail = (
                f"{name} has an extremely low online visibility score of {score}/100. "
                f"A Google search returns minimal or no results. Customers and lenders searching "
                f"for this business online will find little to nothing — a significant trust and "
                f"discoverability barrier in the current digital-first market."
            )
            vis_severity = "high"
            vis_impact = "Estimated 30-50% revenue loss from undiscoverable inbound leads"
            vis_rec = "Create a Google Business Profile, claim all review platforms, and publish at least 2 news announcements within 60 days."
            vis_roi = "Google Business Profile drives 5x more leads for equivalent businesses — free to set up"
        elif score < 50:
            vis_detail = (
                f"{name} has a below-average market visibility score of {score}/100. "
                f"The business has some online presence but is not easily discoverable by "
                f"potential customers, partners, or lenders researching the company."
            )
            vis_severity = "medium"
            vis_impact = "Estimated 15-25% potential revenue uplift from improved discoverability"
            vis_rec = "Strengthen SEO presence, increase review acquisition, and publish monthly thought leadership content."
            vis_roi = "Mid-market businesses with strong visibility score 2-3x more inbound enquiries"
        else:
            vis_detail = (
                f"{name} has a healthy market visibility score of {score}/100. "
                f"The business is findable online and has reasonable media and review presence."
            )
            vis_severity = "low"
            vis_impact = "No immediate visibility gap identified"
            vis_rec = "Maintain existing online presence and monitor sentiment monthly."
            vis_roi = "Sustaining current visibility protects existing inbound pipeline"

        findings.append(AgentFinding(
            agent=self.name,
            category="Market Intelligence",
            severity=vis_severity,
            title=f"Market Visibility Score: {score}/100",
            detail=vis_detail,
            financial_impact=vis_impact,
            recommendation=vis_rec,
            roi_estimate=vis_roi,
            cost_of_inaction="Continued low discoverability means competitors capture inbound demand by default.",
            benchmark_reference="Market visibility 50+ = industry standard for SMEs in digital markets",
            data_source="Serper.dev Google Search API" if SERPER_API_KEY else "API key not configured",
            quick_win=score < 20 and bool(SERPER_API_KEY),
        ))

        # Finding 2: Sentiment / Reputation (only if we have live data)
        if SERPER_API_KEY and sentiment in ("negative", "positive", "neutral"):
            if sentiment == "negative":
                findings.append(AgentFinding(
                    agent=self.name,
                    category="Reputation Risk",
                    severity="high",
                    title=f"Negative public sentiment detected for {name}",
                    detail=(
                        f"Online search results and news coverage show negative signals for {name}. "
                        f"{structured.get('sentiment_summary', '')} "
                        f"Negative online sentiment directly reduces customer trust, partner willingness, "
                        f"and lender confidence."
                    ),
                    financial_impact="Negative sentiment typically reduces conversion rates by 20-40%",
                    recommendation="Engage a PR professional to respond to negative coverage and implement a reputation management strategy.",
                    roi_estimate="Reputation recovery within 6-12 months with consistent positive content",
                    cost_of_inaction="Unchecked negative sentiment compounds — each unanswered review costs future customers.",
                    benchmark_reference="Businesses with >20% negative reviews lose 30% of customers (BrightLocal, 2025)",
                    data_source="Serper.dev news and review search",
                    quick_win=False,
                ))

        # Finding 3: Market opportunity (if opportunities found)
        if structured.get("opportunities"):
            opps = "; ".join(structured["opportunities"][:3])
            findings.append(AgentFinding(
                agent=self.name,
                category="Market Opportunity",
                severity="medium",
                title=f"Market opportunities identified for {memory.industry or 'this sector'}",
                detail=(
                    f"Live market research identified the following growth opportunities relevant to {name}: "
                    f"{opps}. These opportunities are based on current industry trends in {memory.country or 'the region'}."
                ),
                financial_impact="Opportunity value unquantified — strategic planning required to size each",
                recommendation=structured.get("strategic_actions", ["Develop a market opportunity assessment"])[0],
                roi_estimate="Market opportunity value depends on execution speed and competitive position",
                cost_of_inaction="Competitors may capture these opportunities before this business responds.",
                benchmark_reference="Industry trend analysis",
                data_source="Serper.dev industry trend search",
                quick_win=False,
            ))

        # Finding 4: Competitor threat (if competitors found)
        comps = structured.get("competitor_names") or memory.market_competitors
        if comps:
            comp_list = ", ".join(comps[:5])
            findings.append(AgentFinding(
                agent=self.name,
                category="Competitive Intelligence",
                severity="medium",
                title=f"{len(comps)} competitors identified in {memory.industry or 'this sector'}",
                detail=(
                    f"Market research identified the following competitors operating in the same space as {name}: "
                    f"{comp_list}. Understanding their positioning, pricing, and strengths is essential for "
                    f"maintaining competitive advantage."
                ),
                financial_impact="Unquantified — requires competitive pricing and feature analysis",
                recommendation=f"Conduct a structured competitive analysis against {comps[0] if comps else 'key competitors'} within 30 days.",
                roi_estimate="Competitive positioning typically improves win rates by 15-30%",
                cost_of_inaction="Without knowing competitors' moves, pricing and product decisions are made blind.",
                benchmark_reference="Competitive search results",
                data_source="Serper.dev competitor search",
                quick_win=True,
            ))

        return findings

    # ── Mock helpers ──────────────────────────────────────────────

    def _apply_mock(self, memory: SharedMemory, mock: dict):
        memory.market_visibility_score = mock["visibility_score"]
        memory.market_sentiment = mock["sentiment"]
        memory.market_news = mock["news"]
        memory.market_competitors = mock["competitors"]
        memory.market_opportunities = mock["opportunities"]
        memory.market_risks = mock["risks"]
        memory.market_total_results = mock["total_results"]
        memory.market_search_performed = True

    def _mock_findings(self, memory: SharedMemory) -> list[AgentFinding]:
        return [
            AgentFinding(
                agent=self.name,
                category="Market Intelligence",
                severity="medium",
                title=f"Market Visibility Score: {memory.market_visibility_score}/100",
                detail=(
                    f"{memory.business_name} has a below-average online visibility score of "
                    f"{memory.market_visibility_score}/100. The business has limited digital presence, "
                    f"reducing discoverability for potential customers and lenders."
                ),
                financial_impact="Estimated 15-25% revenue uplift potential from improved discoverability",
                recommendation="Build a Google Business Profile and implement a basic SEO strategy.",
                roi_estimate="Google Business Profile drives measurable inbound leads within 90 days",
                cost_of_inaction="Competitors with stronger digital presence capture inbound demand by default.",
                benchmark_reference="Market visibility 50+ = industry standard for SMEs",
                data_source="Demo mode — live search not active",
                quick_win=True,
            ),
            AgentFinding(
                agent=self.name,
                category="Market Opportunity",
                severity="medium",
                title=f"Growth opportunities identified in {memory.industry or 'target market'}",
                detail=(
                    "Market research identified: growing e-commerce adoption in target market; "
                    "underserved SME segment with limited direct competition. "
                    "First-mover advantage available in digital channels."
                ),
                financial_impact="Market opportunity value unquantified — sizing analysis recommended",
                recommendation="Prioritise digital channel development to capture e-commerce growth wave.",
                roi_estimate="Digital revenue channel typically contributes 20-35% of total revenue within 18 months",
                cost_of_inaction="Competitors may capture digital market share before this business responds.",
                benchmark_reference="Industry growth trend analysis",
                data_source="Demo mode",
                quick_win=False,
            ),
        ]
