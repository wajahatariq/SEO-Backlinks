"""
agent/backlink_search_agent.py — Module 6: Comprehensive Backlink Search

Multi-phase pipeline designed for maximum coverage:
  Phase 1: LLM generates 40 diverse search queries
  Phase 2: All 40+ queries run concurrently via Tavily (up to 450 raw URLs)
  Phase 3: Detect & extract "mega-list" pages — each page can yield 100-300 domains
  Phase 4: Batch LLM enrichment (50 per batch, parallelised)
  Phase 5: Sort by relevance + DA estimate
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import urlparse

import litellm
from dotenv import load_dotenv

from tools import extract_website, search_web

load_dotenv()

_MODEL = os.environ.get("LITELLM_MODEL", "gpt-4o-mini")
_MAX_EXTRACT_PAGES = 8   # list pages to deep-extract
_BATCH_SIZE = 50         # domains per LLM enrichment call


# ── Helpers ───────────────────────────────────────────────────────────────────

def _domain(url: str) -> str:
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        return parsed.netloc.lower().lstrip("www.")
    except Exception:
        return url


# ── Phase 1: LLM-generated query set ─────────────────────────────────────────

def _generate_queries(query: str) -> list[str]:
    """Ask the LLM to produce 40 highly varied search queries for maximum coverage."""
    prompt = f"""Generate exactly 40 diverse Google search queries to find backlink opportunities for the niche: "{query}"

Cover ALL of these angles with multiple queries each:
- "write for us" and guest post submission pages
- High DA niche directories and listing sites
- Resource pages and curated link roundups
- Forums, Slack communities, Reddit subreddits
- Niche blogs accepting contributor articles
- .edu and .gov resource or reference pages
- Industry association and membership sites
- Podcast guest and interview opportunities
- Product review and comparison sites
- Web 2.0 and social bookmarking platforms
- Infographic submission sites
- Q&A platforms (Quora, StackExchange niches)

CRITICAL RULES:
1. Return ONLY a raw JSON object — no markdown, no code fences.
2. Every string value MUST be in double quotes.
3. Use EXACTLY this structure:

{{"queries": ["query one here", "query two here", "query three here"]}}

Make every query unique and specific. Vary the phrasing widely.
Return exactly 40 queries inside the "queries" array."""

    try:
        resp = litellm.completion(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content.strip()
        data = json.loads(raw)
        queries = data.get("queries", [])
        if isinstance(queries, list) and len(queries) >= 10:
            return [str(q) for q in queries[:40]]
    except Exception:
        pass

    # Fallback static set
    return [
        f"{query} guest post write for us",
        f"{query} submit a guest post",
        f"{query} high DA directory list",
        f"{query} resource page link building",
        f"{query} forum community sites",
        f"{query} blogs accepting contributors",
        f"best backlink sites {query}",
        f"{query} .edu resource pages",
        f"{query} industry association sites",
        f"{query} web 2.0 sites list",
    ]


# ── Phase 2: Concurrent Tavily searches ───────────────────────────────────────

def _run_search(q: str) -> list[dict]:
    try:
        return search_web(q, max_results=10)
    except Exception:
        return []


# ── Phase 3: Extract domains from mega-list pages ─────────────────────────────

_LIST_KEYWORDS = [
    "top 100", "top 50", "top 200", "top 500", "500 sites", "200 sites",
    "list of", "best sites", "guest post sites", "directories", "mega list",
    "complete list", "ultimate list", "massive list", "link building sites",
]


def _is_list_page(r: dict) -> bool:
    haystack = " ".join([
        (r.get("title") or ""),
        (r.get("url") or ""),
        (r.get("content") or ""),
    ]).lower()
    return any(kw in haystack for kw in _LIST_KEYWORDS)


def _mine_list_page(url: str, query: str) -> list[str]:
    """Extract + parse a list page, returning raw domain strings."""
    content = extract_website(url)
    if not content or len(content) < 200:
        return []

    prompt = f"""You are an SEO expert. Extract every website domain or URL mentioned in the text below that could serve as a backlink opportunity for the niche: "{query}".

TEXT:
{content[:4000]}

CRITICAL RULES:
1. Return ONLY a raw JSON object — no markdown, no code fences.
2. Every string value MUST be in double quotes.
3. Use EXACTLY this structure:

{{"domains": ["domain1.com", "domain2.com", "domain3.net"]}}

Include every real domain you can find. No duplicates. Aim for maximum extraction."""

    try:
        resp = litellm.completion(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content.strip()
        data = json.loads(raw)
        return [str(d) for d in data.get("domains", [])]
    except Exception:
        return []


# ── Phase 4: Batch LLM enrichment ────────────────────────────────────────────

def _enrich_batch(batch: list[dict], query: str) -> list[dict]:
    entries = "\n".join(
        f"{i + 1}. domain={r['domain']} | title={r.get('title', '')} | url={r['url']}"
        for i, r in enumerate(batch)
    )

    prompt = f"""You are an SEO specialist. Classify and enrich these {len(batch)} websites for the niche: "{query}"

WEBSITES:
{entries}

CRITICAL RULES:
1. Return ONLY a raw JSON object — no markdown, no code fences.
2. Every string value MUST be enclosed in double quotes.
3. Use EXACTLY this structure (example shows one entry — return ALL {len(batch)}):

{{
  "results": [
    {{
      "domain": "example.com",
      "url": "https://example.com/write-for-us",
      "da_estimate": 45,
      "type": "Guest Post",
      "relevance": "High",
      "how_to_get": "Submit a guest post pitch via their write-for-us page."
    }}
  ]
}}

Allowed values:
- type: "Guest Post", "Directory", "Profile", "Forum", "Resource Page", "Blog", "Community", "Web 2.0", "Q&A"
- relevance: "High", "Medium", or "Low"
- da_estimate: integer 1-100
- how_to_get: short actionable sentence in double quotes

Return ALL {len(batch)} entries in the "results" array."""

    try:
        resp = litellm.completion(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content.strip()
        if "```" in raw:
            for part in raw.split("```"):
                part = part.strip().lstrip("json").strip()
                if part.startswith("{"):
                    raw = part
                    break
        s, e = raw.find("{"), raw.rfind("}") + 1
        if s != -1 and e > s:
            raw = raw[s:e]
        data = json.loads(raw)
        enriched = data.get("results", [])
        if not enriched:
            for v in data.values():
                if isinstance(v, list) and v:
                    enriched = v
                    break
        return enriched
    except Exception:
        return [
            {
                "domain": r["domain"],
                "url": r["url"],
                "da_estimate": 0,
                "type": "Blog",
                "relevance": "Medium",
                "how_to_get": "Research their site and reach out with a relevant pitch.",
            }
            for r in batch
        ]


# ── Main entry point ──────────────────────────────────────────────────────────

def run_backlink_search(query: str) -> dict[str, Any]:
    """
    Comprehensive multi-phase backlink search.
    Typically returns 300–1000+ unique opportunities depending on niche.
    """

    # ── Phase 1: Query generation ─────────────────────────────────────────────
    queries = _generate_queries(query)

    # Append hard-coded list-hunting queries for Phase 3 seeding
    list_hunting = [
        f"top 100 guest post sites {query} 2024",
        f"200 backlink opportunities {query} list",
        f"complete list {query} directories submissions",
        f"best {query} link building sites mega list",
        f"{query} 500 backlinks free list",
    ]
    all_queries = queries + list_hunting   # 45 total

    # ── Phase 2: Concurrent searches ─────────────────────────────────────────
    raw_results: list[dict] = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(_run_search, q): q for q in all_queries}
        for fut in as_completed(futs):
            try:
                raw_results.extend(fut.result())
            except Exception:
                pass

    # Deduplicate and flag list pages
    seen: set[str] = set()
    unique_hits: list[dict] = []
    list_page_candidates: list[str] = []

    for r in raw_results:
        dom = _domain(r.get("url", ""))
        if not dom:
            continue
        if _is_list_page(r) and len(list_page_candidates) < _MAX_EXTRACT_PAGES:
            list_page_candidates.append(r.get("url", ""))
        if dom not in seen:
            seen.add(dom)
            unique_hits.append({
                "url": r.get("url", ""),
                "domain": dom,
                "title": r.get("title", ""),
            })

    # ── Phase 3: Mine list pages for bulk domains ─────────────────────────────
    extra_hits: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(_mine_list_page, url, query): url for url in list_page_candidates}
        for fut in as_completed(futs):
            try:
                for raw_dom in fut.result():
                    clean = _domain(raw_dom)
                    if clean and clean not in seen:
                        seen.add(clean)
                        extra_hits.append({
                            "url": f"https://{clean}",
                            "domain": clean,
                            "title": "",
                        })
            except Exception:
                pass

    all_unique = unique_hits + extra_hits

    if not all_unique:
        return {"query": query, "results": [], "total": 0, "error": "No results found"}

    # ── Phase 4: Batch enrichment ─────────────────────────────────────────────
    batches = [all_unique[i:i + _BATCH_SIZE] for i in range(0, len(all_unique), _BATCH_SIZE)]
    enriched_all: list[dict] = []

    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(_enrich_batch, b, query) for b in batches]
        for fut in as_completed(futs):
            try:
                enriched_all.extend(fut.result())
            except Exception:
                pass

    # ── Phase 5: Sort by relevance → DA ──────────────────────────────────────
    _rel = {"High": 0, "Medium": 1, "Low": 2}
    enriched_all.sort(key=lambda x: (
        _rel.get(x.get("relevance", "Low"), 2),
        -(x.get("da_estimate") or 0),
    ))

    return {
        "query": query,
        "results": enriched_all,
        "total": len(enriched_all),
        "error": None,
    }
