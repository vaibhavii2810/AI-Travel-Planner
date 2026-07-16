"""
Travel planning API routes — thin handlers only.
All business logic lives in PlanningService.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_planning_service
from app.models.requests import CreatePlanRequest, ReviewRequest
from app.models.responses import (
    CreatePlanResponse,
    FinalPlanResponse,
    PlanStatusResponse,
    ReviewResponse,
)
from app.services.planning_service import PlanningService

logger = logging.getLogger("app.api.routes.plans")

router = APIRouter(prefix="/plan", tags=["Travel Planning"])


@router.post(
    "",
    response_model=CreatePlanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a new travel planning request",
    description=(
        "Creates a new AI-powered travel plan. Returns a plan_id immediately. "
        "Poll GET /plan/{plan_id} for status updates. "
        "When status is 'awaiting_review', submit your decision via POST /plan/{plan_id}/review."
    ),
)
async def create_plan(
    request: CreatePlanRequest,
    service: PlanningService = Depends(get_planning_service),
) -> CreatePlanResponse:
    logger.info(f"POST /plan | destination={request.destination} | travelers={request.num_travelers}")
    return await service.create_plan(travel_request=request)


@router.get(
    "/{plan_id}",
    response_model=PlanStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current plan status and draft itinerary",
    description=(
        "Returns the current workflow status, research summary, and draft itinerary (if available). "
        "Poll this endpoint until status is 'awaiting_review' to see the draft. "
        "Status values: queued → researching → planning → awaiting_review → revising → finalized / error"
    ),
)
async def get_plan_status(
    plan_id: str,
    service: PlanningService = Depends(get_planning_service),
) -> PlanStatusResponse:
    logger.info(f"GET /plan/{plan_id}")
    return await service.get_plan_status(plan_id=plan_id)


@router.post(
    "/{plan_id}/review",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit a HITL review decision",
    description=(
        "Submit your review decision for the draft itinerary. "
        "Only valid when plan status is 'awaiting_review'. "
        "Actions:\n"
        "- **approve**: Finalize the plan as-is\n"
        "- **reject**: Provide feedback; the system will intelligently re-plan or re-research\n"
        "- **modify**: Provide targeted modifications; the planner will revise accordingly"
    ),
)
async def review_plan(
    plan_id: str,
    review: ReviewRequest,
    service: PlanningService = Depends(get_planning_service),
) -> ReviewResponse:
    logger.info(f"POST /plan/{plan_id}/review | action={review.action}")
    return await service.submit_review(plan_id=plan_id, review=review)


@router.get(
    "/{plan_id}/final",
    response_model=FinalPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the finalized itinerary",
    description=(
        "Returns the final approved itinerary. "
        "Only returns data when plan status is 'finalized'. "
        "Returns 409 if the plan has not been approved yet."
    ),
)
async def get_final_plan(
    plan_id: str,
    service: PlanningService = Depends(get_planning_service),
) -> FinalPlanResponse:
    logger.info(f"GET /plan/{plan_id}/final")
    return await service.get_final_plan(plan_id=plan_id)
