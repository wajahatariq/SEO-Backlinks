"""
agent/backlink_search_agent.py — Module 6: Comprehensive Backlink Search

Runs 7 varied Tavily searches to surface as many backlink
opportunities as possible for a given query/niche.
"""

import json
import os
from typing import Any
from urllib.parse import urlparse

import litellm
from dotenv import load_dotenv

from tools import search_web

load_dotenv()

_MODEL = os.environ.get("LITELLM_MODEL", "gpt-4o-mini")


def _extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        domain = parsed.netloc.lower()
        return domain.lstrip("www.")
    except Exception:
        return url


def run_backlink_search(query: str) -> dict[str, Any]:
    """
    Run a comprehensive backlink opportunity search for *query*.
    Fires 7 Tavily searches across different angles and aggregates unique results.
    """
    search_angles = [
        f"{query} guest post write for us",
        f"{query} submit guest post site",
        f"{query} high DA directory list",
        f"{query} resource page link building",
        f"{query} community forum sites",
        f"best backlink sites for {query}",
        f"{query} blogs accepting contributors",
    ]

    seen_domains: set[str] = set()
    raw_hits: list[dict] = []

    for angle in search_angles:
        try:
            results = search_web(angle, max_results=10)
            for r in results:
                domain = _extract_domain(r.get("url", ""))
                if not domain or domain in seen_domains:
                    continue
                seen_domains.add(domain)
                raw_hits.append({
                    "url": r.get("url", ""),
                    "domain": domain,
                    "title": r.get("title", ""),
                    "snippet": (r.get("content") or "")[:120],
                })
        except Exception:
            continue

    if not raw_hits:
        return {"query": query, "results": [], "total": 0, "error": "No results found"}

    # ── LLM enrichment ────────────────────────────────────────────────────────
    entries_text = "\n".join(
        f"{i + 1}. domain={r['domain']} | title={r['title']} | url={r['url']}"
        for i, r in enumerate(raw_hits[:60])
    )

    prompt = f"""You are an SEO specialist. Classify and enrich these websites found for the niche query: "{query}"

WEBSITES:
{entries_text}

CRITICAL RULES:
1. Return ONLY a raw JSON object — no markdown, no code fences.
2. Every string value MUST be enclosed in double quotes.
3. Use the EXACT structure shown below.

EXAMPLE STRUCTURE:
{{
  "results": [
    {{
      "domain": "example.com",
      "url": "https://example.com/write-for-us",
      "da_estimate": 45,
      "type": "Guest Post",
      "relevance": "High",
      "how_to_get": "Submit a guest post pitch through their write-for-us page."
    }}
  ]
}}

Classify ALL {len(raw_hits[:60])} websites above.
- "type" must be one of: "Guest Post", "Directory", "Profile", "Forum", "Resource Page", "Blog", "Community"
- "relevance" must be: "High", "Medium", or "Low"
- "da_estimate" must be an integer 1-100
- "how_to_get" must be a short, actionable sentence in double quotes
- Preserve the original URL from the list above

Return ONLY the JSON object with the "results" array."""

    try:
        resp = litellm.completion(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw_out = resp.choices[0].message.content.strip()

        # Strip markdown fences if present
        if "```" in raw_out:
            for part in raw_out.split("```"):
                part = part.strip().lstrip("json").strip()
                if part.startswith("{"):
                    raw_out = part
                    break

        start = raw_out.find("{")
        end = raw_out.rfind("}") + 1
        if start != -1 and end > start:
            raw_out = raw_out[start:end]

        data = json.loads(raw_out)
        enriched: list[dict] = data.get("results", [])

        # If the model didn't return the expected key, try any list value
        if not enriched:
            for v in data.values():
                if isinstance(v, list) and v:
                    enriched = v
                    break

    except Exception:
        # Graceful fallback: return raw hits without enrichment
        enriched = [
            {
                "domain": r["domain"],
                "url": r["url"],
                "da_estimate": 0,
                "type": "Blog",
                "relevance": "Medium",
                "how_to_get": "Research their site and reach out with a relevant pitch.",
            }
            for r in raw_hits
        ]

    return {
        "query": query,
        "results": enriched,
        "total": len(enriched),
        "error": None,
    }
