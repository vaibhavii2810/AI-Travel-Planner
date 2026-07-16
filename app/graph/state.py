"""
TravelPlanState — the single source of truth for the LangGraph graph.

Design notes:
- Top-level is TypedDict (required by LangGraph StateGraph)
- Nested objects use Pydantic domain models
- status field mirrors graph position; used by FastAPI without parsing graph internals
- revision_count enables max-revision guardrail (Risk 4 bypass)
- plan_id is stored IN state so nodes can use it for logging
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from typing_extensions import TypedDict

from app.models.domain import DraftItinerary, ResearchOutput, TravelRequest


class TravelPlanState(TypedDict, total=False):
    # ── Core input ───────────────────────────────────────────────────────────
    plan_id: str                          # == thread_id, stored for logging convenience
    travel_request: TravelRequest

    # ── Agent outputs ─────────────────────────────────────────────────────────
    research_output: Optional[ResearchOutput]
    draft_itinerary: Optional[DraftItinerary]
    final_itinerary: Optional[DraftItinerary]

    # ── HITL control ──────────────────────────────────────────────────────────
    review_decision: Optional[dict[str, Any]]   # Injected by Command(resume=...)
    rejection_feedback: Optional[str]
    modification_request: Optional[dict[str, Any]]

    # ── Routing & metadata ────────────────────────────────────────────────────
    status: str                           # see STATUS_* constants below
    revision_count: int
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


# ── Status constants ──────────────────────────────────────────────────────────
# Single source of truth for all status strings used across nodes and service layer

STATUS_QUEUED = "queued"
STATUS_RESEARCHING = "researching"
STATUS_PLANNING = "planning"
STATUS_AWAITING_REVIEW = "awaiting_review"
STATUS_REVISING = "revising"
STATUS_FINALIZING = "finalizing"
STATUS_FINALIZED = "finalized"
STATUS_ERROR = "error"
STATUS_MAX_REVISIONS = "max_revisions_exceeded"


def initial_state(plan_id: str, travel_request: TravelRequest) -> TravelPlanState:
    """Build the initial state dict for a new graph run."""
    now = datetime.utcnow()
    return TravelPlanState(
        plan_id=plan_id,
        travel_request=travel_request,
        research_output=None,
        draft_itinerary=None,
        final_itinerary=None,
        review_decision=None,
        rejection_feedback=None,
        modification_request=None,
        status=STATUS_RESEARCHING,
        revision_count=0,
        error_message=None,
        created_at=now,
        updated_at=now,
    )
