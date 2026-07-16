"""
Research Node — invokes the Research Agent and updates graph state.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.agents.research_agent import invoke_research_agent
from app.core.logging import log_node_entry, log_node_exit
from app.graph.state import STATUS_RESEARCHING, STATUS_REVISING, TravelPlanState
from app.models.domain import TravelRequest

logger = logging.getLogger("app.graph.nodes.research_node")


async def research_node(state: TravelPlanState) -> dict:
    """
    LangGraph node: Runs the Research Agent.

    Reads from state:
        - travel_request
        - rejection_feedback (set if re-researching after reject)
        - plan_id (for logging)

    Writes to state:
        - research_output
        - status
        - updated_at
    """
    plan_id = state.get("plan_id", "unknown")
    travel_request: TravelRequest = state["travel_request"]
    rejection_feedback: str | None = state.get("rejection_feedback")

    # Mark as revising (not fresh research) when re-running after rejection
    active_status = STATUS_REVISING if rejection_feedback else STATUS_RESEARCHING
    log_node_entry(logger, "research_node", plan_id, {"status": active_status})

    research_output = await invoke_research_agent(
        destination=travel_request.destination,
        start_date=str(travel_request.start_date),
        end_date=str(travel_request.end_date),
        num_days=travel_request.num_days,
        num_travelers=travel_request.num_travelers,
        budget_min=travel_request.budget_min,
        budget_max=travel_request.budget_max,
        budget_currency=travel_request.budget_currency,
        interests=travel_request.interests,
        rejection_feedback=rejection_feedback,
    )

    log_node_exit(logger, "research_node", plan_id, active_status)

    return {
        "research_output": research_output,
        "status": active_status,
        "updated_at": datetime.now(timezone.utc),
        # Clear rejection feedback once processed
        "rejection_feedback": None,
    }
