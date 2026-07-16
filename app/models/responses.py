"""API response models — what the server sends back to clients."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.domain import DraftItinerary, ResearchOutput, TravelRequest


class CreatePlanResponse(BaseModel):
    plan_id: str
    status: str
    message: str
    created_at: datetime


class PlanStatusResponse(BaseModel):
    plan_id: str
    status: str
    revision_count: int = 0
    travel_request: Optional[TravelRequest] = None
    research_summary: Optional[ResearchOutput] = None
    draft_itinerary: Optional[DraftItinerary] = None
    final_itinerary: Optional[DraftItinerary] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ReviewResponse(BaseModel):
    plan_id: str
    status: str
    action_received: str
    message: str


class FinalPlanResponse(BaseModel):
    plan_id: str
    status: str
    final_itinerary: DraftItinerary
    approved_at: Optional[datetime] = None


class ErrorResponse(BaseModel):
    error: str
    message: str
    plan_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    environment: str
    checkpointer: str
