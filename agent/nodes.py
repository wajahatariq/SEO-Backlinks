"""
agent/nodes.py — The three processing nodes of the SEO backlink agent.

Node execution order:
  analyze_competitors → enrich_competitors → generate_opportunities
"""

import json
import os
from typing import Any

import litellm
from dotenv import load_dotenv

from agent.state import AgentState

load_dotenv()

_MODEL = os.environ.get("LITELLM_MODEL", "gpt-4o-mini")


# ---------------------------------------------------------------------------
# Node 1 — Analyze Competitors
# ---------------------------------------------------------------------------

def analyze_competitors(state: AgentState) -> AgentState:
    """
    Use the LLM to identify the top 3 organic competitors for the target domain.

    Writes:  state["competitors"]
    """
    target = state["target_domain"]

    prompt = f"""You are an SEO expert. List the top 3 organic search competitors
for the domain '{target}'. Return ONLY a JSON array of domain strings.
Example: ["competitor1.com", "competitor2.com"]
No explanation, just the array."""

    try:
        response = litellm.completion(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
        competitors: list[str] = json.loads(raw)
    except Exception as exc:
        return {**state, "error": f"analyze_competitors failed: {exc}"}

    return {**state, "competitors": competitors, "error": None}


# ---------------------------------------------------------------------------
# Node 2 — Enrich Competitors (LLM-powered, no external API)
# ---------------------------------------------------------------------------

def fetch_backlink_stats(state: AgentState) -> AgentState:
    """
    Use the LLM to describe the backlink profile of each competitor
    (niche, authority, typical link sources) without any external API call.

    Writes:  state["raw_referring_domains"]
    """
    if state.get("error"):
        return state

    competitors = state.get("competitors", [])
    target = state["target_domain"]

    prompt = f"""You are an SEO data analyst. For each of the following competitor domains,
provide a brief backlink profile summary based on your knowledge.

Target site: '{target}'
Competitors: {json.dumps(competitors)}

Return ONLY a valid JSON array. Each object must have:
- "domain": the competitor domain
- "da": estimated domain authority 1-100 (integer)
- "ref_domains": estimated number of referring domains (integer)
- "total_backlinks": estimated total backlinks (integer)
- "niche": one phrase describing their primary niche
- "top_link_sources": array of 3 strings — types of sites that typically link to them

No markdown, no explanation — just the JSON array."""

    try:
        response = litellm.completion(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        profiles: list[dict[str, Any]] = json.loads(raw.strip())
    except Exception as exc:
        return {**state, "error": f"enrich_competitors failed: {exc}"}

    return {**state, "raw_referring_domains": profiles, "error": None}


# ---------------------------------------------------------------------------
# Node 3 — Generate Opportunities
# ---------------------------------------------------------------------------

def filter_and_rank(state: AgentState) -> AgentState:
    """
    Use the LLM to generate a ranked list of concrete link-building
    opportunities based on competitor profiles.

    Writes:  state["opportunities"]
    """
    if state.get("error"):
        return state

    profiles = state.get("raw_referring_domains", [])
    target = state["target_domain"]

    if not profiles:
        return {**state, "error": "Could not build competitor profiles."}

    prompt = f"""You are a senior SEO link-building strategist. The client's website is '{target}'.

Here are the backlink profiles of their top competitors:
{json.dumps(profiles, indent=2)}

Generate exactly 15 high-quality, actionable link-building opportunities for '{target}'.
Each must be a SPECIFIC, REAL website the client can realistically get a backlink from,
inspired by what works for these competitors.

Return ONLY a valid JSON array. Each object must have these exact keys:
- "domain": specific website (e.g. "producthunt.com")
- "rank": estimated domain authority 1-100 (integer)
- "backlinks_num": estimated monthly referral visits potential (integer)
- "source_competitor": which competitor inspired this opportunity
- "reason": one clear sentence — how to get the link and why it fits '{target}'

No markdown, no explanation — just the JSON array."""

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
