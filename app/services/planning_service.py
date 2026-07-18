"""
PlanningService — the bridge between FastAPI routes and LangGraph.

This is the only component that knows about both layers.
FastAPI routes do NOT import LangGraph directly.

Risk 1 bypass: Command(resume=...) used correctly in submit_review()
Risk 2 bypass: graph is injected (already compiled with checkpointer)
Risk 3 bypass: metadata written BEFORE background task; get_plan_status reads metadata first
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4

from langgraph.types import Command

from app.core.config import get_settings
from app.core.exceptions import (
    GraphExecutionError,
    InvalidStateError,
    PlanNotFinalizedError,
    PlanNotFoundError,
)
from app.graph.state import (
    STATUS_AWAITING_REVIEW,
    STATUS_ERROR,
    STATUS_FINALIZED,
    STATUS_MAX_REVISIONS,
    STATUS_QUEUED,
    STATUS_RESEARCHING,
    STATUS_REVISING,
    initial_state,
)
from app.models.domain import TravelRequest
from app.models.requests import ReviewRequest
from app.models.responses import (
    CreatePlanResponse,
    FinalPlanResponse,
    PlanStatusResponse,
    ReviewResponse,
)
from app.services.plan_repository import PlanRepository

logger = logging.getLogger("app.services.planning_service")


class PlanningService:
    """
    Service layer for the travel planning workflow.
    All public methods are async-safe.
    """

    def __init__(self, graph, plan_repo: PlanRepository):
        self._graph = graph
        self._repo = plan_repo
        self._settings = get_settings()

    # ── Public API ────────────────────────────────────────────────────────────

    async def create_plan(self, travel_request: TravelRequest) -> CreatePlanResponse:
        """
        Creates a new travel plan and launches graph execution in the background.

        Risk 3 bypass:
        1. Metadata record created IMMEDIATELY → GET /plan/{id} works right away
        2. Graph runs in background → POST /plan returns fast (no LLM blocking)
        """
        plan_id = str(uuid4())
        logger.info(f"PlanningService.create_plan | plan_id={plan_id} | destination={travel_request.destination}")

        # ① Write metadata BEFORE launching graph — GET responses work immediately
        await self._repo.create(plan_id=plan_id, status=STATUS_RESEARCHING)

        # ② Launch graph in background — don't await it here
        asyncio.create_task(
            self._run_graph(plan_id=plan_id, travel_request=travel_request),
            name=f"graph-{plan_id}",
        )

        return CreatePlanResponse(
            plan_id=plan_id,
            status=STATUS_RESEARCHING,
            message=(
                f"Your travel plan for {travel_request.destination} is being created. "
                f"Poll GET /api/v1/plan/{plan_id} for updates."
            ),
            created_at=datetime.now(timezone.utc),
        )

    async def get_plan_status(self, plan_id: str) -> PlanStatusResponse:
        """
        Returns the current status of a plan.

        Risk 3 bypass:
        - Reads metadata first (always fast, exists from create_plan)
        - If graph has run, reads richer state from LangGraph checkpoint
        - Never blocks on graph execution
        """
        meta = await self._repo.get(plan_id)
        if not meta:
            raise PlanNotFoundError(plan_id)

        # Build base response from metadata
        base = PlanStatusResponse(
            plan_id=plan_id,
            status=meta.status,
            revision_count=0,
            error_message=meta.error_message,
            created_at=meta.created_at,
            updated_at=meta.updated_at,
        )

        # If graph has run, enrich from checkpoint
        if meta.status not in (STATUS_QUEUED, STATUS_RESEARCHING):
            try:
                config = {"configurable": {"thread_id": plan_id}}
                snapshot = await self._graph.aget_state(config)
                if snapshot and snapshot.values:
                    sv = snapshot.values
                    checkpoint_status = sv.get("status")
                    # Only let the checkpoint override the DB status if the DB status is
                    # not already in a forward-moving state. This prevents the HITL node
                    # (which sets status=awaiting_review in its return dict) from
                    # overwriting the 'revising' state we just wrote when the user
                    # submitted reject/modify.
                    NON_OVERRIDABLE = (STATUS_FINALIZED, STATUS_REVISING, STATUS_ERROR, STATUS_MAX_REVISIONS)
                    if checkpoint_status and meta.status not in NON_OVERRIDABLE:
                        base.status = checkpoint_status
                    base.revision_count = sv.get("revision_count", 0)
                    base.travel_request = sv.get("travel_request")
                    base.research_summary = sv.get("research_output")
                    base.draft_itinerary = sv.get("draft_itinerary")
                    base.final_itinerary = sv.get("final_itinerary")
                    base.error_message = sv.get("error_message")
                    base.updated_at = sv.get("updated_at", meta.updated_at)
            except Exception as exc:
                logger.warning(f"Could not read checkpoint for plan_id={plan_id}: {exc}")
                # Fall back to metadata — don't fail the GET request

        return base

    async def submit_review(self, plan_id: str, review: ReviewRequest) -> ReviewResponse:
        """
        Submits a HITL review decision and resumes graph execution.

        Risk 1 bypass: Uses Command(resume=...) — NOT a new graph.ainvoke() with new state.
        The graph resumes from the EXACT line after interrupt() in hitl_review_node.
        """
        meta = await self._repo.get(plan_id)
        if not meta:
            raise PlanNotFoundError(plan_id)

        if meta.status != STATUS_AWAITING_REVIEW:
            raise InvalidStateError(
                plan_id=plan_id,
                current_status=meta.status,
                required_status=STATUS_AWAITING_REVIEW,
            )

        logger.info(
            f"PlanningService.submit_review | plan_id={plan_id} | action={review.action}"
        )

        # Update metadata immediately
        new_status = STATUS_FINALIZED if review.action == "approve" else STATUS_REVISING
        await self._repo.update(plan_id, status=new_status)

        # Resume graph in background using Command(resume=...)
        asyncio.create_task(
            self._resume_graph(plan_id=plan_id, review=review),
            name=f"resume-{plan_id}",
        )

        action_messages = {
            "approve": "Plan approved! Finalizing your itinerary.",
            "reject": "Feedback received. Re-planning in progress. Poll GET /plan/{id} for the revised draft.",
            "modify": "Modifications received. Revising itinerary. Poll GET /plan/{id} for the updated draft.",
        }

        return ReviewResponse(
            plan_id=plan_id,
            status=new_status,
            action_received=review.action,
            message=action_messages.get(review.action, "Review submitted."),
        )

    async def get_final_plan(self, plan_id: str) -> FinalPlanResponse:
        """
        Returns the finalized plan. Raises if not yet approved.
        """
        meta = await self._repo.get(plan_id)
        if not meta:
            raise PlanNotFoundError(plan_id)

        if meta.status != STATUS_FINALIZED:
            raise PlanNotFinalizedError(plan_id=plan_id, current_status=meta.status)

        config = {"configurable": {"thread_id": plan_id}}
        try:
            snapshot = await self._graph.aget_state(config)
        except Exception as exc:
            raise GraphExecutionError(f"Failed to read final state for plan {plan_id}: {exc}") from exc

        if not snapshot or not snapshot.values:
            raise GraphExecutionError(f"No checkpoint found for finalized plan {plan_id}")

        sv = snapshot.values
        final_itinerary = sv.get("final_itinerary")

        if not final_itinerary:
            raise PlanNotFinalizedError(plan_id=plan_id, current_status="finalizing")

        return FinalPlanResponse(
            plan_id=plan_id,
            status=STATUS_FINALIZED,
            final_itinerary=final_itinerary,
            approved_at=sv.get("updated_at"),
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _run_graph(self, plan_id: str, travel_request: TravelRequest) -> None:
        """
        Runs the LangGraph graph for a new plan.
        Background task — errors update metadata, never bubble to HTTP layer.
        """
        config = {
            "configurable": {"thread_id": plan_id},
            "recursion_limit": self._settings.GRAPH_RECURSION_LIMIT,
        }
        state = initial_state(plan_id=plan_id, travel_request=travel_request)

        try:
            logger.info(f"_run_graph | plan_id={plan_id} | STARTING")
            async for chunk in self._graph.astream(state, config=config):
                # Update metadata status in real-time from graph chunks
                for node_name, node_output in chunk.items():
                    if isinstance(node_output, dict) and "status" in node_output:
                        new_status = node_output["status"]
                        await self._repo.update(plan_id, status=new_status)
                        logger.debug(f"_run_graph | plan_id={plan_id} | node={node_name} | status→{new_status}")

            # Post-stream: determine if we paused at HITL or truly completed
            # aget_state() inspects the checkpoint to see what nodes are pending
            try:
                snapshot = await self._graph.aget_state(config)
                if snapshot and snapshot.next == ("hitl_review_node",):
                    # Genuine interrupt pause — status already set to awaiting_review by node
                    await self._repo.update(plan_id, status=STATUS_AWAITING_REVIEW)
                    logger.info(f"_run_graph | plan_id={plan_id} | PAUSED at hitl_review_node")
                else:
                    logger.info(f"_run_graph | plan_id={plan_id} | COMPLETED | next={getattr(snapshot, 'next', None)}")
            except Exception as snap_exc:
                logger.warning(f"_run_graph | plan_id={plan_id} | Could not inspect post-stream snapshot: {snap_exc}")

        except Exception as exc:
            logger.exception(f"_run_graph | plan_id={plan_id} | FAILED: {exc}")
            await self._repo.update(plan_id, status=STATUS_ERROR, error_message=str(exc))

    async def _resume_graph(self, plan_id: str, review: ReviewRequest) -> None:
        """
        Resumes the LangGraph graph after a HITL review decision.

        Risk 1 bypass: Uses Command(resume=review_payload) — the canonical LangGraph pattern.
        The graph loads the checkpoint for thread_id=plan_id and resumes from interrupt().
        """
        config = {
            "configurable": {"thread_id": plan_id},
            "recursion_limit": self._settings.GRAPH_RECURSION_LIMIT,
        }
        review_payload = {
            "action": review.action,
            "feedback": review.feedback,
            "modifications": review.modifications,
        }

        # Immediately set status to revising so frontend polling sees the transition
        await self._repo.update(plan_id, status=STATUS_REVISING)

        try:
            logger.info(
                f"_resume_graph | plan_id={plan_id} | action={review.action} | RESUMING"
            )
            # Command(resume=...) is the canonical LangGraph HITL resume mechanism
            async for chunk in self._graph.astream(
                Command(resume=review_payload),
                config=config,
            ):
                for node_name, node_output in chunk.items():
                    if isinstance(node_output, dict) and "status" in node_output:
                        new_status = node_output["status"]
                        # Only write forward-moving statuses — never let a node
                        # accidentally downgrade finalized → revising
                        if new_status not in (STATUS_FINALIZED,):
                            await self._repo.update(plan_id, status=new_status)
                        logger.debug(f"_resume_graph | plan_id={plan_id} | node={node_name} | status→{new_status}")

            # Post-stream: determine if we paused at HITL or completed
            try:
                snapshot = await self._graph.aget_state(config)
                if snapshot and snapshot.next == ("hitl_review_node",):
                    await self._repo.update(plan_id, status=STATUS_AWAITING_REVIEW)
                    logger.info(f"_resume_graph | plan_id={plan_id} | PAUSED at hitl_review_node")
                elif review.action == "approve":
                    await self._repo.update(plan_id, status=STATUS_FINALIZED)
                    logger.info(f"_resume_graph | plan_id={plan_id} | FINALIZED")
                else:
                    # Shouldn't happen — but safety net: if graph ended without
                    # pausing at HITL during a revise, push to awaiting_review
                    current_meta = await self._repo.get(plan_id)
                    if current_meta and current_meta.status == STATUS_REVISING:
                        await self._repo.update(plan_id, status=STATUS_AWAITING_REVIEW)
                    logger.info(f"_resume_graph | plan_id={plan_id} | COMPLETED | next={getattr(snapshot, 'next', None)}")
            except Exception as snap_exc:
                logger.warning(f"_resume_graph | plan_id={plan_id} | Could not inspect post-stream snapshot: {snap_exc}")
                # Safety net: ensure we don't leave it stuck on revising
                try:
                    await self._repo.update(plan_id, status=STATUS_AWAITING_REVIEW)
                except Exception:
                    pass

        except Exception as exc:
            logger.exception(f"_resume_graph | plan_id={plan_id} | FAILED: {exc}")
            await self._repo.update(plan_id, status=STATUS_ERROR, error_message=str(exc))

