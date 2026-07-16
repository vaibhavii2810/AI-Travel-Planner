"""
Finalize Node — stamps the approved itinerary and marks the plan as complete.
No LLM call — pure state transformation.
"""
from __future__ import annotations

import logging
from datetime import datetime

from app.core.logging import log_node_entry, log_node_exit
from app.graph.state import STATUS_FINALIZED, TravelPlanState

logger = logging.getLogger("app.graph.nodes.finalize_node")


def finalize_node(state: TravelPlanState) -> dict:
    """
    LangGraph node: Finalizes the approved itinerary.

    Copies draft_itinerary → final_itinerary.
    Sets status to 'finalized'.
    No LLM call.
    """
    plan_id = state.get("plan_id", "unknown")
    log_node_entry(logger, "finalize_node", plan_id, {"status": STATUS_FINALIZED})

    draft = state.get("draft_itinerary")

    if draft is None:
        logger.error(f"finalize_node | plan_id={plan_id} | draft_itinerary is None — cannot finalize")
        return {
            "status": "error",
            "error_message": "Cannot finalize: draft itinerary is missing.",
            "updated_at": datetime.utcnow(),
        }

    log_node_exit(logger, "finalize_node", plan_id, STATUS_FINALIZED)
    draft_version = draft.version if hasattr(draft, "version") else draft.get("version", "unknown")
    logger.info(f"finalize_node | plan_id={plan_id} | PLAN FINALIZED ✓ | version={draft_version}")

    return {
        "final_itinerary": draft,
        "status": STATUS_FINALIZED,
        "updated_at": datetime.utcnow(),
    }
