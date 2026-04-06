"""
agent/nodes.py — The three processing nodes of the SEO backlink agent.

Node execution order:
  analyze_competitors → fetch_backlink_stats → generate_opportunities
"""

import json
import os
import time
from typing import Any

import litellm
from dotenv import load_dotenv

from agent.state import AgentState
from tools import fetch_backlink_summary

load_dotenv()

_MODEL = os.environ.get("LITELLM_MODEL", "gpt-4o-mini")

# ---------------------------------------------------------------------------
# Node 1 — Analyze Competitors
# ---------------------------------------------------------------------------

def analyze_competitors(state: AgentState) -> AgentState:
    """
    Use the LLM to identify the top 5 organic competitors for the target domain.

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
# Node 2 — Fetch Backlink Stats
# ---------------------------------------------------------------------------

def fetch_backlink_stats(state: AgentState) -> AgentState:
    """
    Fetch backlink profile summary for each competitor via RapidAPI.

    Writes:  state["raw_referring_domains"]  (list of competitor profile dicts)
    """
    if state.get("error"):
        return state

    competitors = state.get("competitors", [])
    profiles: list[dict[str, Any]] = []

    for i, domain in enumerate(competitors):
        if i > 0:
            time.sleep(2)  # Respect RapidAPI free tier rate limit
        try:
            summary = fetch_backlink_summary(domain)
            profiles.append(summary)
        except Exception as exc:
            # Surface the first real error so it appears in the UI
            if not profiles:
                return {**state, "error": f"Backlink API failed for '{domain}': {exc}"}
            profiles.append({"domain": domain, "error": str(exc)})

    return {**state, "raw_referring_domains": profiles, "error": None}


# ---------------------------------------------------------------------------
# Node 3 — Generate Opportunities
# ---------------------------------------------------------------------------

def filter_and_rank(state: AgentState) -> AgentState:
    """
    Use the LLM to analyse competitor backlink profiles and generate
    a ranked list of concrete link-building opportunities for the target.

    Writes:  state["opportunities"]
    """
    if state.get("error"):
        return state

    profiles = [p for p in state.get("raw_referring_domains", []) if "error" not in p]
    target = state["target_domain"]

    if not profiles:
        return {**state, "error": "No competitor backlink data could be retrieved."}

    prompt = f"""You are a senior SEO link-building strategist. The client's website is '{target}'.

Below are the backlink profiles of their top competitors (domain authority, referring domains, top anchor texts, monthly trends):

{json.dumps(profiles, indent=2)}

Using this competitive intelligence, generate exactly 15 high-quality, actionable link-building opportunities for '{target}'.

Each opportunity must be a SPECIFIC, REAL website or type of website that the client can realistically get a link from, based on what is working for their competitors.

Return ONLY a valid JSON array. Each object must have these exact keys:
- "domain": a specific website or platform (e.g. "producthunt.com", "designmodo.com")
- "rank": estimated domain authority score 1-100 (integer)
- "backlinks_num": estimated monthly referral visits potential (integer)
- "source_competitor": which competitor inspired this opportunity
- "reason": one clear sentence on how to get the link and why it fits '{target}'

No markdown, no explanation — just the JSON array."""

    try:
        response = litellm.completion(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        raw_output = response.choices[0].message.content.strip()
        # Strip markdown fences if model adds them anyway
        if raw_output.startswith("```"):
            raw_output = raw_output.split("```")[1]
            if raw_output.startswith("json"):
                raw_output = raw_output[4:]
        opportunities: list[dict[str, Any]] = json.loads(raw_output.strip())
    except Exception as exc:
        return {**state, "error": f"generate_opportunities failed: {exc}"}

    return {**state, "opportunities": opportunities, "error": None}
