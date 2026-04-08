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

CRITICAL RULES:
1. Return ONLY a raw JSON object — no markdown, no code fences, no explanation.
2. Every string value MUST be wrapped in double quotes. No unquoted text.
3. Use the EXACT structure shown in the example below.

EXAMPLE OUTPUT STRUCTURE (replace example values with real analysis):
{{
  "authority_gap": {{
    "your_estimated_da": 20,
    "competitor_estimated_da": 55,
    "links_needed": 120,
    "summary": "Your site has a significant authority gap and needs quality backlinks to compete."
  }},
  "link_gaps": [
    {{
      "domain": "example-blog.com",
      "da_estimate": 45,
      "type": "Guest Post",
      "how_to_get": "Reach out to their editor with a relevant article pitch via their contact page."
    }}
  ],
  "content_gaps": [
    {{
      "topic": "beginner tutorials",
      "content_type": "Guide",
      "priority": "High",
      "why_important": "Competitor ranks for this topic and it drives significant organic traffic."
    }}
  ],
  "action_plan": [
    {{
      "step": 1,
      "action": "Conduct a technical SEO audit to fix crawl errors and page speed issues.",
      "type": "Technical",
      "priority": "High",
      "timeline": "Week 1"
    }}
  ]
}}

Now produce the REAL analysis for {state['your_domain']} vs {state['competitor_domain']} with:
- "authority_gap": exactly as shown (4 keys, summary must be a quoted string)
- "link_gaps": array of 10 objects (domain, da_estimate, type, how_to_get — all strings quoted)
- "content_gaps": array of 8 objects (topic, content_type, priority, why_important — all strings quoted)
- "action_plan": array of 15 objects with steps 1-15 (step is integer, action/type/priority/timeline are quoted strings)

type options for link_gaps: "Guest Post", "Directory", "Profile", "Forum", "Mention", "Resource Page"
content_type options: "Blog Post", "Landing Page", "Tool", "Guide", "Case Study", "FAQ"
priority options: "High", "Medium", "Low"
timeline options: "Week 1", "Week 2", "Month 1", "Month 2", "Month 3"
action type options: "Profile", "Guest Post", "Content", "Directory", "Outreach", "Technical"

Return ONLY the JSON object. Every string value must be in double quotes."""

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
