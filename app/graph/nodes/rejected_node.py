"""
Rejected Node — clean terminal state when the user explicitly rejects the plan.

Behaviour:
- Does NOT re-invoke any agent (no re-planning).
- Reverts draft_itinerary to the last approved version if one exists (final_itinerary).
- If no approved version exists, sets draft_itinerary to None.
- Sets status = "rejected" and routes to END.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.core.logging import log_node_entry, log_node_exit
from app.graph.state import STATUS_REJECTED, TravelPlanState

logger = logging.getLogger("app.graph.nodes.rejected_node")


def rejected_node(state: TravelPlanState) -> dict:
    """
    LangGraph node: Terminates the graph when the user rejects the current draft.

    - If a final_itinerary exists (i.e. a previously approved version), revert to it.
    - Otherwise, mark draft as None and set status = rejected.
    - Routes to END — no further planning.
    """
    plan_id = state.get("plan_id", "unknown")
    review_decision = state.get("review_decision") or {}
    feedback = review_decision.get("feedback", "No feedback provided.")

    log_node_entry(logger, "rejected_node", plan_id, {"feedback": feedback[:80]})

    # Revert to last approved version if it exists
    last_approved = state.get("final_itinerary")

    if last_approved:
        logger.info(
            f"rejected_node | plan_id={plan_id} | "
            f"reverting draft to last approved version"
        )
        revert_draft = last_approved
        message = "Plan rejected. Draft reverted to the last approved version."
    else:
        logger.info(
            f"rejected_node | plan_id={plan_id} | "
            f"no approved version — marking plan as fully rejected"
        )
        revert_draft = None
        message = (
            "Plan rejected. No approved version exists. "
            "Start a new plan (POST /plan) with updated requirements."
        )

    log_node_exit(logger, "rejected_node", plan_id, STATUS_REJECTED)

    return {
        "draft_itinerary": revert_draft,
        "status": STATUS_REJECTED,
        "error_message": message,
        "rejection_feedback": None,
        "modification_request": None,
        "updated_at": datetime.now(timezone.utc),
    }
