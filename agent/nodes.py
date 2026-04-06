"""
agent/nodes.py — The three processing nodes of the SEO backlink agent.

Node execution order:
  analyze_competitors → fetch_dataforseo → filter_and_rank
"""

import json
import os
from typing import Any

import litellm
from dotenv import load_dotenv

from agent.state import AgentState
from tools import fetch_referring_domains

load_dotenv()

# LiteLLM model — override via LITELLM_MODEL env var (default: gpt-4o-mini)
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

    prompt = f"""You are an SEO expert. List the top 5 organic search competitors
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
# Node 2 — Fetch DataForSEO
# ---------------------------------------------------------------------------

def fetch_dataforseo(state: AgentState) -> AgentState:
    """
    Call the DataForSEO Backlinks API to fetch referring domains for each competitor.

    Writes:  state["raw_referring_domains"]
    """
    if state.get("error"):
        return state  # Short-circuit on prior error

    competitors = state.get("competitors", [])
    all_results: list[dict[str, Any]] = []

    for domain in competitors:
        try:
            data = fetch_referring_domains(target=domain, limit=50)
            # DataForSEO wraps results in tasks[0].result
            tasks = data.get("tasks", [])
            if tasks and tasks[0].get("result"):
                items: list[dict[str, Any]] = tasks[0]["result"][0].get("items", [])
                for item in items:
                    item["source_competitor"] = domain  # Tag the origin
                all_results.extend(items)
        except Exception as exc:
            # Log the failure for this competitor but continue
            all_results.append({"error": str(exc), "source_competitor": domain})

    return {**state, "raw_referring_domains": all_results, "error": None}


# ---------------------------------------------------------------------------
# Node 3 — Filter & Rank
# ---------------------------------------------------------------------------

def filter_and_rank(state: AgentState) -> AgentState:
    """
    Use the LLM to filter noise and rank the referring domains by opportunity quality.

    Writes:  state["opportunities"]
    """
    if state.get("error"):
        return state  # Short-circuit on prior error

    raw = state.get("raw_referring_domains", [])
    target = state["target_domain"]

    # Trim payload to keep token usage manageable (top 100 by rank)
    sortable = [r for r in raw if "error" not in r]
    sortable.sort(key=lambda x: x.get("rank", 0), reverse=True)
    trimmed = sortable[:100]

    prompt = f"""You are an SEO link-building expert. The target site is '{target}'.

Below is a JSON list of referring domains that link to competitors.
Your task:
1. Remove spam, low-quality, or irrelevant domains.
2. Keep only domains that represent realistic link-building opportunities.
3. Return the filtered list as a JSON array. Each object must have:
   - "domain": the referring domain
   - "rank": its domain rank (higher = better)
   - "backlinks_num": number of backlinks
   - "source_competitor": which competitor it links to
   - "reason": one sentence explaining why it's a good opportunity

Return ONLY valid JSON. No markdown fences.

Data:
{json.dumps(trimmed, indent=2)}"""

    try:
        response = litellm.completion(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        raw_output = response.choices[0].message.content.strip()
        opportunities: list[dict[str, Any]] = json.loads(raw_output)
    except Exception as exc:
        return {**state, "error": f"filter_and_rank failed: {exc}"}

    return {**state, "opportunities": opportunities, "error": None}
