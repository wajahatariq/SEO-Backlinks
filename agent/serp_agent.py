"""
agent/serp_agent.py — Module 3: Keyword SERP Analyzer

Searches a keyword in real-time via Tavily, returns the top 10 ranking
competitors with DA estimates, content type, and why they rank.
"""

import json
import os
from typing import Any

import litellm
from dotenv import load_dotenv

from tools import search_web

load_dotenv()

_MODEL = os.environ.get("LITELLM_MODEL", "gpt-4o-mini")


def run_serp_analyzer(keyword: str) -> dict[str, Any]:
    """
    Analyse the top 10 SERP results for a keyword.

    Args:
        keyword: The search term to analyse (e.g. "best CRM for small business")

    Returns:
        {"competitors": [...], "insights": "...", "error": None | str}
    """
    try:
        results = search_web(keyword, max_results=10)
    except Exception as exc:
        return {"competitors": [], "insights": "", "error": f"Search failed: {exc}"}

    if not results:
        return {"competitors": [], "insights": "", "error": "No SERP results found."}

    raw = "\n".join(
        f"{i+1}. URL: {r['url']}\n   Title: {r['title']}\n   Preview: {r['content'][:250]}"
        for i, r in enumerate(results)
    )

    prompt = f"""You are a senior SEO analyst. Analyse these top search results for the keyword: "{keyword}"

{raw}

Return ONLY a valid JSON object with exactly two keys:
- "competitors": array of up to 10 objects, each with:
  - "rank": position 1-10 (integer)
  - "domain": domain name only (e.g. "hubspot.com")
  - "url": full page URL
  - "title": page title
  - "da_estimate": estimated domain authority 1-100 (integer)
  - "content_type": one of "Article/Blog", "Product Page", "Homepage", "Tool/App", "Directory", "Forum", "Video", "Other"
  - "why_ranking": one clear sentence explaining the likely ranking factor
- "insights": 2-3 sentences summarising the SERP landscape — difficulty, dominant content types, and what a new entrant must do to rank

No markdown — only the raw JSON object."""

    try:
        resp = litellm.completion(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw_out = resp.choices[0].message.content.strip()
        if raw_out.startswith("```"):
            raw_out = raw_out.split("```")[1]
            if raw_out.startswith("json"):
                raw_out = raw_out[4:]
        data: dict[str, Any] = json.loads(raw_out.strip())
    except Exception as exc:
        return {"competitors": [], "insights": "", "error": f"Processing failed: {exc}"}

    return {
        "competitors": data.get("competitors", []),
        "insights": data.get("insights", ""),
        "error": None,
    }
