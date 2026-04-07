"""
agent/gap_agent.py — Module 4: Gap Analysis & Strategy Roadmap

3-node LangGraph pipeline:
  extract_sites → research_competitor → generate_gap_report → END

Uses Tavily to read both sites and search for competitor authority data,
then the LLM produces a full gap report with link gaps, content gaps,
authority gap, and a step-by-step action plan.
"""

import json
import os
from typing import Any, TypedDict

import litellm
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

from tools import extract_website, search_web

load_dotenv()

_MODEL = os.environ.get("LITELLM_MODEL", "gpt-4o-mini")


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class GapState(TypedDict):
    your_domain: str
    competitor_domain: str
    your_content: str
    competitor_content: str
    competitor_research: str
    link_gaps: list[dict[str, Any]]
    content_gaps: list[dict[str, Any]]
    action_plan: list[dict[str, Any]]
    authority_gap: dict[str, Any]
    error: str | None


# ---------------------------------------------------------------------------
# Node 1 — Extract both websites
# ---------------------------------------------------------------------------

def extract_sites(state: GapState) -> GapState:
    your_content = extract_website(f"https://{state['your_domain']}")
    comp_content = extract_website(f"https://{state['competitor_domain']}")
    return {
        **state,
        "your_content": your_content[:2000] if your_content else "",
        "competitor_content": comp_content[:2000] if comp_content else "",
        "error": None,
    }


# ---------------------------------------------------------------------------
# Node 2 — Research competitor authority & backlinks via Tavily
# ---------------------------------------------------------------------------

def research_competitor(state: GapState) -> GapState:
    if state.get("error"):
        return state

    competitor = state["competitor_domain"]
    try:
        results = search_web(
            f"{competitor} backlinks domain authority referring domains SEO profile",
            max_results=5,
        )
        context = "\n".join(
            f"- {r['title']}: {r['content'][:250]}" for r in results
        )
    except Exception as exc:
        context = f"Research unavailable: {exc}"

    return {**state, "competitor_research": context, "error": None}


# ---------------------------------------------------------------------------
# Node 3 — LLM generates the full gap report
# ---------------------------------------------------------------------------

def generate_gap_report(state: GapState) -> GapState:
    if state.get("error"):
        return state

    prompt = f"""You are a senior SEO strategist. Perform a complete gap analysis.

YOUR SITE: {state['your_domain']}
Content extracted: {state['your_content'][:600] or 'Could not extract — use your SEO knowledge.'}

COMPETITOR: {state['competitor_domain']}
Content extracted: {state['competitor_content'][:600] or 'Could not extract — use your SEO knowledge.'}

Web research on competitor authority:
{state['competitor_research'][:500]}

Return ONLY a valid JSON object with these exact keys:

"authority_gap": {{
  "your_estimated_da": integer,
  "competitor_estimated_da": integer,
  "links_needed": integer (estimated quality links to close the gap),
  "summary": one sentence
}}

"link_gaps": array of 10 objects, each:
  "domain": specific site where competitor likely has a link but you don't
  "da_estimate": integer
  "type": one of "Guest Post", "Directory", "Profile", "Forum", "Mention", "Resource Page"
  "how_to_get": one clear action sentence

"content_gaps": array of 8 objects, each:
  "topic": topic or keyword competitor covers that you're missing
  "content_type": "Blog Post", "Landing Page", "Tool", "Guide", "Case Study", "FAQ"
  "priority": "High", "Medium", or "Low"
  "why_important": one sentence

"action_plan": array of 15 step-by-step actions, each:
  "step": integer 1-15
  "action": exactly what to do
  "type": "Profile", "Guest Post", "Content", "Directory", "Outreach", "Technical"
  "priority": "High", "Medium", or "Low"
  "timeline": one of "Week 1", "Week 2", "Month 1", "Month 2", "Month 3"

No markdown — only the raw JSON object."""

    try:
        resp = litellm.completion(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        raw_out = resp.choices[0].message.content.strip()
        # Strip markdown fences
        if "```" in raw_out:
            parts = raw_out.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    raw_out = part
                    break
        # Find the outermost JSON object
        start = raw_out.find("{")
        end   = raw_out.rfind("}") + 1
        if start != -1 and end > start:
            raw_out = raw_out[start:end]
        data: dict[str, Any] = json.loads(raw_out)
    except Exception as exc:
        return {**state, "error": f"Gap report failed: {exc}"}

    return {
        **state,
        "link_gaps": data.get("link_gaps", []),
        "content_gaps": data.get("content_gaps", []),
        "action_plan": data.get("action_plan", []),
        "authority_gap": data.get("authority_gap", {}),
        "error": None,
    }


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def _should_continue(state: GapState) -> str:
    return "end" if state.get("error") else "continue"


def build_gap_graph() -> StateGraph:
    graph = StateGraph(GapState)
    graph.add_node("extract_sites", extract_sites)
    graph.add_node("research_competitor", research_competitor)
    graph.add_node("generate_gap_report", generate_gap_report)
    graph.set_entry_point("extract_sites")
    graph.add_conditional_edges(
        "extract_sites", _should_continue,
        {"continue": "research_competitor", "end": END},
    )
    graph.add_conditional_edges(
        "research_competitor", _should_continue,
        {"continue": "generate_gap_report", "end": END},
    )
    graph.add_edge("generate_gap_report", END)
    return graph.compile()


gap_agent = build_gap_graph()
