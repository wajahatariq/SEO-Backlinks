"""
agent/nodes.py — The three processing nodes of the SEO backlink agent.

Node execution order:
  analyze_competitors → enrich_with_tavily → generate_opportunities

Tavily provides real-time web data at every stage:
  - Node 1: searches the web to find actual competitors
  - Node 2: extracts the target site + searches competitor link profiles
  - Node 3: LLM generates opportunities grounded in real scraped data
"""

import json
import os
from typing import Any

import litellm
from dotenv import load_dotenv

from agent.state import AgentState
from tools import extract_website, search_web

load_dotenv()

_MODEL = os.environ.get("LITELLM_MODEL", "gpt-4o-mini")


# ---------------------------------------------------------------------------
# Node 1 — Analyze Competitors (Tavily-powered)
# ---------------------------------------------------------------------------

def analyze_competitors(state: AgentState) -> AgentState:
    """
    Use Tavily to search the web for actual competitors of the target domain,
    then use the LLM to extract clean domain names from the results.

    Writes:  state["competitors"]
    """
    target = state["target_domain"]

    # Real-time web search for competitors
    try:
        results = search_web(f"top competitors and alternatives to {target}", max_results=5)
        search_context = "\n".join(
            f"- {r['title']}: {r['content'][:200]}" for r in results
        )
    except Exception as exc:
        return {**state, "error": f"Tavily search failed: {exc}"}

    prompt = f"""You are an SEO expert. Based on the web search results below,
identify the top 3 competitor domains for '{target}'.

Search results:
{search_context}

Return ONLY a JSON array of domain strings (no www, no https).
Example: ["competitor1.com", "competitor2.com", "competitor3.com"]
No explanation, just the array."""

    try:
        response = litellm.completion(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        competitors: list[str] = json.loads(raw)
    except Exception as exc:
        return {**state, "error": f"analyze_competitors failed: {exc}"}

    return {**state, "competitors": competitors, "error": None}


# ---------------------------------------------------------------------------
# Node 2 — Enrich with Tavily
# ---------------------------------------------------------------------------

def fetch_backlink_stats(state: AgentState) -> AgentState:
    """
    Use Tavily to:
      1. Extract the target website's content (understand what it does).
      2. Search for real backlink/authority data for each competitor.

    Writes:  state["raw_referring_domains"]  (enriched profiles)
    """
    if state.get("error"):
        return state

    target = state["target_domain"]
    competitors = state.get("competitors", [])

    # 1. Extract target website to understand its niche and content
    target_content = extract_website(f"https://{target}")

    # 2. Search for competitor backlink profiles (one combined search)
    competitor_list = ", ".join(competitors)
    try:
        link_results = search_web(
            f"backlinks domain authority referring domains {competitor_list} SEO analysis",
            max_results=5,
        )
        link_context = "\n".join(
            f"- {r['title']}: {r['content'][:300]}" for r in link_results
        )
    except Exception as exc:
        link_context = f"Search failed: {exc}"

    # 3. Ask LLM to build structured profiles from the real data
    prompt = f"""You are an SEO data analyst. Using the web data below, build a backlink profile for each competitor.

Target site '{target}' content:
{target_content[:1000] if target_content else 'Could not extract — use your knowledge.'}

Web data about competitor link profiles:
{link_context}

Competitors: {json.dumps(competitors)}

Return ONLY a valid JSON array. Each object must have:
- "domain": competitor domain
- "da": estimated domain authority 1-100 (integer)
- "ref_domains": estimated referring domains (integer)
- "total_backlinks": estimated total backlinks (integer)
- "niche": one phrase describing their primary niche
- "top_link_sources": array of 3 strings — types of sites that link to them

Base your estimates on the real web data above. No markdown — just the JSON array."""

    try:
        response = litellm.completion(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        profiles: list[dict[str, Any]] = json.loads(raw.strip())
    except Exception as exc:
        return {**state, "error": f"enrich_with_tavily failed: {exc}"}

    # Attach target site context for use in node 3
    return {
        **state,
        "raw_referring_domains": profiles,
        "error": None,
        "_target_content": target_content[:500] if target_content else "",
    }


# ---------------------------------------------------------------------------
# Node 3 — Generate Opportunities
# ---------------------------------------------------------------------------

def filter_and_rank(state: AgentState) -> AgentState:
    """
    Use the LLM — grounded in real Tavily data — to generate 15 ranked,
    actionable link-building opportunities for the target site.

    Writes:  state["opportunities"]
    """
    if state.get("error"):
        return state

    profiles = state.get("raw_referring_domains", [])
    target = state["target_domain"]
    target_content = state.get("_target_content", "")

    if not profiles:
        return {**state, "error": "Could not build competitor profiles."}

    # Search for niche-specific link building opportunities
    try:
        niche_results = search_web(
            f"link building opportunities guest posts {target} niche backlinks 2024",
            max_results=5,
        )
        niche_context = "\n".join(
            f"- {r['url']}: {r['content'][:200]}" for r in niche_results
        )
    except Exception:
        niche_context = ""

    prompt = f"""You are a senior SEO link-building strategist.

CLIENT WEBSITE: '{target}'
{f"What the site does: {target_content}" if target_content else ""}

COMPETITOR BACKLINK PROFILES (from real web data):
{json.dumps(profiles, indent=2)}

NICHE LINK-BUILDING OPPORTUNITIES FOUND ONLINE:
{niche_context if niche_context else "Use your expert knowledge."}

Generate exactly 15 high-quality, actionable link-building opportunities for '{target}'.
Each must be a SPECIFIC, REAL website the client can get a backlink from.
Prioritise sites that actually appear in the data above.

Return ONLY a valid JSON array. Each object must have:
- "domain": specific real website (e.g. "producthunt.com")
- "rank": domain authority 1-100 (integer)
- "backlinks_num": estimated monthly referral visits (integer)
- "source_competitor": which competitor inspired this
- "reason": one sentence — exact strategy to get the link and why it fits '{target}'

No markdown, no explanation — only the JSON array."""

    try:
        response = litellm.completion(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        raw_output = response.choices[0].message.content.strip()
        if raw_output.startswith("```"):
            raw_output = raw_output.split("```")[1]
            if raw_output.startswith("json"):
                raw_output = raw_output[4:]
        opportunities: list[dict[str, Any]] = json.loads(raw_output.strip())
    except Exception as exc:
        return {**state, "error": f"generate_opportunities failed: {exc}"}

    return {**state, "opportunities": opportunities, "error": None}
