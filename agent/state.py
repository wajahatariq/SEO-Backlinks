"""
agent/state.py — Shared state definition for the LangGraph agent.

The State TypedDict flows through every node. Each node reads
what it needs and writes back its outputs.
"""

from typing import Any, TypedDict


class AgentState(TypedDict):
    # --- Input ---
    target_domain: str          # The domain the user wants opportunities for

    # --- Node: analyze_competitors ---
    competitors: list[str]      # Competitor domains identified by the LLM

    # --- Node: fetch_dataforseo ---
    raw_referring_domains: list[dict[str, Any]]  # Raw API results per competitor

    # --- Node: filter_and_rank ---
    opportunities: list[dict[str, Any]]  # Final filtered & ranked link opportunities

    # --- Internal context (not returned to frontend) ---
    _target_content: str        # Raw text extracted from the target website by Tavily

    # --- Control ---
    error: str | None           # Populated if any node fails; halts the graph
