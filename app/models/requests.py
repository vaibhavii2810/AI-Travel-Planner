"""API request models — what clients send to the server."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

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

    @model_validator(mode="after")
    def validate_action_fields(self) -> "ReviewRequest":
        """Enforce cross-field rules: reject requires feedback, modify requires modifications."""
        if self.action == "reject" and not self.feedback:
            raise ValueError("feedback is required and must be non-empty when action is 'reject'")
        if self.action == "modify" and not self.modifications:
            raise ValueError("modifications is required when action is 'modify'")
        return self
