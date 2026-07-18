"""
TravelPlannerGraph — StateGraph assembly, node registration, edge wiring.

Risk 1 + Risk 2 bypass:
- Graph is compiled with checkpointer (MANDATORY — without this, interrupt() has no backend)
- build_graph() raises immediately if checkpointer is None (fail-fast)
- All nodes and edges are registered here, nowhere else

Graph topology:
    START → research_node → planner_node → hitl_review_node
                ↑               ↑                   │ (interrupt here)
                │               │            route_after_review()
                │               │           /        |           \
          research_node   planner_node  finalize_node  max_revisions_node
                                              │                │
                                             END              END
"""
from __future__ import annotations

import logging

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.core.config import get_settings
from app.graph.edges.routing import route_after_review
from app.graph.nodes.finalize_node import finalize_node
from app.graph.nodes.hitl_review_node import hitl_review_node
from app.graph.nodes.max_revisions_node import max_revisions_node
from app.graph.nodes.planner_node import planner_node
from app.graph.nodes.rejected_node import rejected_node
from app.graph.nodes.research_node import research_node
from app.graph.state import TravelPlanState

logger = logging.getLogger("app.graph.graph")


def build_graph(checkpointer: BaseCheckpointSaver):
    """
    Assembles and compiles the TravelPlannerGraph.

    Args:
        checkpointer: A LangGraph checkpoint saver instance.
                      MUST NOT be None — graph requires persistence for interrupt().

    Returns:
        A compiled LangGraph CompiledGraph ready for ainvoke().

    Raises:
        RuntimeError: If checkpointer is None (fail-fast guard).
    """
    if checkpointer is None:
        raise RuntimeError(
            "Graph cannot be compiled without a checkpointer. "
            "interrupt() requires a persistence backend. "
            "Pass a MemorySaver (test/dev) or AsyncPostgresSaver (production)."
        )

    settings = get_settings()

    # ── StateGraph definition ─────────────────────────────────────────────────
    graph = StateGraph(TravelPlanState)

    # ── Register nodes ────────────────────────────────────────────────────────
    graph.add_node("research_node", research_node)
    graph.add_node("planner_node", planner_node)
    graph.add_node("hitl_review_node", hitl_review_node)
    graph.add_node("finalize_node", finalize_node)
    graph.add_node("max_revisions_node", max_revisions_node)
    graph.add_node("rejected_node", rejected_node)

    # ── Register edges ────────────────────────────────────────────────────────

    # Entry point
    graph.add_edge(START, "research_node")

    # Linear: research → plan → review (where interrupt fires)
    graph.add_edge("research_node", "planner_node")
    graph.add_edge("planner_node", "hitl_review_node")

    # Conditional routing after HITL resume
    graph.add_conditional_edges(
        "hitl_review_node",
        route_after_review,
        {
            "finalize_node": "finalize_node",
            "planner_node": "planner_node",
            "research_node": "research_node",
            "max_revisions_node": "max_revisions_node",
            "rejected_node": "rejected_node",
        },
    )

    # Terminal edges
    graph.add_edge("finalize_node", END)
    graph.add_edge("max_revisions_node", END)
    graph.add_edge("rejected_node", END)

    # ── Compile with checkpointer (REQUIRED for interrupt() persistence) ───────
    compiled = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=[],    # We use interrupt() inside the node, not interrupt_before
        interrupt_after=[],
    )

    logger.info(
        f"TravelPlannerGraph compiled | "
        f"checkpointer={type(checkpointer).__name__} | "
        f"recursion_limit={settings.GRAPH_RECURSION_LIMIT}"
    )

    return compiled
