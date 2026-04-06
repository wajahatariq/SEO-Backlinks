"""
agent/graph.py — Assembles the LangGraph StateGraph and compiles it.

Graph topology:
  analyze_competitors → fetch_dataforseo → filter_and_rank → END
"""

from langgraph.graph import END, StateGraph

from agent.nodes import analyze_competitors, fetch_dataforseo, filter_and_rank
from agent.state import AgentState


def _should_continue(state: AgentState) -> str:
    """Conditional edge: halt the graph early if an error was set."""
    return "end" if state.get("error") else "continue"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("analyze_competitors", analyze_competitors)
    graph.add_node("fetch_dataforseo", fetch_dataforseo)
    graph.add_node("filter_and_rank", filter_and_rank)

    # Entry point
    graph.set_entry_point("analyze_competitors")

    # Edges with error short-circuit after node 1
    graph.add_conditional_edges(
        "analyze_competitors",
        _should_continue,
        {"continue": "fetch_dataforseo", "end": END},
    )
    graph.add_conditional_edges(
        "fetch_dataforseo",
        _should_continue,
        {"continue": "filter_and_rank", "end": END},
    )
    graph.add_edge("filter_and_rank", END)

    return graph.compile()


# Singleton compiled graph — imported by main.py
seo_agent = build_graph()
