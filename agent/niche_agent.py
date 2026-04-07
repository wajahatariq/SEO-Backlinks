"""
agent/niche_agent.py — Module 2: Niche Outreach Finder

Searches the web for guest post / link-building opportunities in a given niche
and location, then uses the LLM to extract contact info, DA estimates, and
link type classification.
"""

import json
import os
from typing import Any

import litellm
from dotenv import load_dotenv

from tools import search_web

load_dotenv()

_MODEL = os.environ.get("LITELLM_MODEL", "gpt-4o-mini")


def run_niche_finder(query: str, location: str) -> dict[str, Any]:
    """
    Find niche-specific outreach opportunities.

    Args:
        query:    e.g. "High DA guest post sites for SaaS"
        location: e.g. "USA", "UK", "UAE" — empty string means global

    Returns:
        {"sites": [...], "error": None | str}
    """
    loc = location.strip() if location else "global"
    search_query = (
        f'{query} "write for us" OR "guest post" OR "submit article" OR "contribute" {loc}'
    )

    try:
        results = search_web(search_query, max_results=10)
    except Exception as exc:
        return {"sites": [], "error": f"Search failed: {exc}"}

    if not results:
        return {"sites": [], "error": "No results found. Try a different query."}

    raw = "\n".join(
        f"{i+1}. URL: {r['url']}\n   Title: {r['title']}\n   Preview: {r['content'][:200]}"
        for i, r in enumerate(results)
    )

    prompt = f"""You are an SEO outreach specialist. A user searched for: "{query}" in location: "{loc}".

Here are the search results:
{raw}

Analyse each result and return it as a structured link-building opportunity.
Return ONLY a valid JSON object with a single key "sites" containing an array.
Each object in the array must have:
- "domain": website domain (e.g. "techcrunch.com")
- "url": the specific page URL from the results
- "write_for_us_url": the likely "Write for Us" or "Contribute" page URL
- "contact_email": email if visible in the snippet, otherwise null
- "da_estimate": estimated domain authority 1-100 (integer)
- "type": exactly one of "Guest Post", "Directory", "Forum", "Web 2.0", "Resource Page"
- "dofollow": true or false (your best guess based on the site type)
- "reason": one sentence explaining why this is a good opportunity

No markdown fences — only the raw JSON object."""

    try:
        resp = litellm.completion(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        raw_out = resp.choices[0].message.content.strip()
        if raw_out.startswith("```"):
            raw_out = raw_out.split("```")[1]
            if raw_out.startswith("json"):
                raw_out = raw_out[4:]
        parsed = json.loads(raw_out.strip())
        if isinstance(parsed, list):
            sites: list[dict[str, Any]] = parsed
        else:
            sites = parsed.get("sites", list(parsed.values())[0] if parsed else [])
    except Exception as exc:
        return {"sites": [], "error": f"Processing failed: {exc}"}

    return {"sites": sites, "error": None}
