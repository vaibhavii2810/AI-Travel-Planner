"""
HITL Review Node — the genuine Human-in-the-Loop gate.

Risk 1 bypass (HITL genuineness):
- interrupt() is called INSIDE this node
- The return value of interrupt() IS the Command(resume=...) payload
- This node does NOT resume until Command(resume=...) is passed to graph.ainvoke()
- The graph MUST be compiled with a checkpointer for this to work

Canonical pattern:
    review_decision = interrupt({"draft": ..., "status": "awaiting_review"})
    # Execution pauses here ↑ until Command(resume=review_decision) is received
    return {"review_decision": review_decision, "status": "revising"}
"""
from __future__ import annotations

import logging
from datetime import datetime

from langgraph.types import interrupt

from app.core.logging import log_node_entry, log_node_exit
from app.graph.state import STATUS_AWAITING_REVIEW, TravelPlanState

logger = logging.getLogger("app.graph.nodes.hitl_review_node")


def hitl_review_node(state: TravelPlanState) -> dict:
    """
    LangGraph node: Genuinely pauses graph execution for human review.

    This is a SYNCHRONOUS node (interrupt() is sync by design in LangGraph).

    What happens:
    1. Marks status as 'awaiting_review' in the yielded interrupt value
    2. Calls interrupt() — LangGraph saves checkpoint and SUSPENDS execution
    3. Returns only after Command(resume=...) is passed to graph.ainvoke()
    4. The return value of interrupt() is the review decision dict
    5. Parses review decision and routes via conditional edge

    IMPORTANT: This node must only be reached AFTER a draft_itinerary exists.
    """
    plan_id = state.get("plan_id", "unknown")
    log_node_entry(logger, "hitl_review_node", plan_id, {"status": STATUS_AWAITING_REVIEW})

    draft_itinerary = state.get("draft_itinerary")
    revision_count = state.get("revision_count", 0)

    # ── GENUINE INTERRUPT — execution halts here ──────────────────────────────
    # The dict passed to interrupt() is surfaced to the caller (graph.ainvoke returns it).
    # The return value of interrupt() is the payload from Command(resume=...).
    review_decision = interrupt(
        {
            "message": "Draft itinerary ready for review. Submit your decision via POST /plan/{id}/review",
            "status": STATUS_AWAITING_REVIEW,
            "revision_count": revision_count,
            "draft_itinerary": (
                draft_itinerary.model_dump()
                if hasattr(draft_itinerary, "model_dump")
                else draft_itinerary
            ) if draft_itinerary else None,
        }
    )
    # ── Execution resumes HERE after Command(resume=review_decision) ──────────

    log_node_exit(logger, "hitl_review_node", plan_id, f"resumed:{review_decision.get('action', 'unknown')}")
    logger.info(f"hitl_review_node | plan_id={plan_id} | action={review_decision.get('action')}")

    # Extract feedback/modifications from the review decision
    action = review_decision.get("action", "")
    rejection_feedback = review_decision.get("feedback") if action == "reject" else None
    modification_request = review_decision.get("modifications") if action == "modify" else None

    return {
        "review_decision": review_decision,
        "rejection_feedback": rejection_feedback,
        "modification_request": modification_request,
        "status": STATUS_AWAITING_REVIEW,  # routing.py will set the next status
        "updated_at": datetime.utcnow(),
    }
