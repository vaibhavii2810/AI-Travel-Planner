"""
Planner Node — invokes the Itinerary Planner Agent and updates graph state.
Increments revision_count here (single source of truth for Risk 4 guard).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.agents.planner_agent import invoke_planner_agent
from app.core.logging import log_node_entry, log_node_exit
from app.graph.state import STATUS_AWAITING_REVIEW, STATUS_PLANNING, STATUS_REVISING, TravelPlanState
from app.models.domain import ResearchOutput, TravelRequest

logger = logging.getLogger("app.graph.nodes.planner_node")


async def planner_node(state: TravelPlanState) -> dict:
    """
    LangGraph node: Runs the Itinerary Planner Agent.

    Reads from state:
        - travel_request
        - research_output
        - revision_count
        - rejection_feedback (if revising after reject)
        - modification_request (if revising after modify)
        - plan_id (for logging)

    Writes to state:
        - draft_itinerary
        - revision_count (incremented)
        - status
        - modification_request (cleared)
        - updated_at
    """
    plan_id = state.get("plan_id", "unknown")
    current_revision = state.get("revision_count", 0)
    is_revision = current_revision > 0
    # Correctly distinguish first pass (planning) vs subsequent passes (revising)
    active_status = STATUS_REVISING if is_revision else STATUS_PLANNING
    log_node_entry(
        logger, "planner_node", plan_id,
        {"revision": current_revision, "status": active_status}
    )

    travel_request: TravelRequest = state["travel_request"]
    research_output: ResearchOutput = state["research_output"]
    rejection_feedback: str | None = state.get("rejection_feedback")
    modification_request: dict | None = state.get("modification_request")

    draft_itinerary = await invoke_planner_agent(
        travel_request=travel_request,
        research_output=research_output,
        revision_count=current_revision,
        rejection_feedback=rejection_feedback,
        modification_request=modification_request,
    )

    new_revision_count = current_revision + 1
    log_node_exit(logger, "planner_node", plan_id, STATUS_AWAITING_REVIEW)
    logger.info(f"planner_node | plan_id={plan_id} | revision_count now={new_revision_count}")

    return {
        "draft_itinerary": draft_itinerary,
        "revision_count": new_revision_count,
        "status": STATUS_AWAITING_REVIEW,
        "updated_at": datetime.now(timezone.utc),
        # Clear feedback/modification once processed
        "rejection_feedback": None,
        "modification_request": None,
    }
