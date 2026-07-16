"""API request models — what clients send to the server."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.domain import TravelRequest


class CreatePlanRequest(TravelRequest):
    """Request body for POST /plan — inherits all TravelRequest fields."""
    pass


class ReviewRequest(BaseModel):
    """Request body for POST /plan/{id}/review."""

    action: Literal["approve", "reject", "modify"] = Field(
        ...,
        description="The review action: approve, reject (with feedback), or modify (with modifications).",
    )
    feedback: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Required when action='reject'. Describes what needs to change.",
    )
    modifications: Optional[dict[str, Any]] = Field(
        default=None,
        description="Required when action='modify'. Targeted changes to apply to the itinerary.",
    )

    @field_validator("feedback")
    @classmethod
    def feedback_required_for_reject(cls, v: Optional[str], info) -> Optional[str]:
        action = info.data.get("action")
        if action == "reject" and not v:
            raise ValueError("feedback is required when action is 'reject'")
        return v

    @field_validator("modifications")
    @classmethod
    def modifications_required_for_modify(cls, v: Optional[dict], info) -> Optional[dict]:
        action = info.data.get("action")
        if action == "modify" and not v:
            raise ValueError("modifications is required when action is 'modify'")
        return v
