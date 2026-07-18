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
        description="The review action: approve, reject, or modify.",
    )
    feedback: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Required when action='reject' or 'modify'. Describes what needs to change.",
    )
    # Keeping modifications for backward compatibility but making it fully optional
    modifications: Optional[dict[str, Any]] = Field(
        default=None,
        description="Legacy field for structured modifications.",
    )

    @model_validator(mode="after")
    def validate_action_fields(self) -> "ReviewRequest":
        """Enforce cross-field rules: reject and modify require feedback."""
        if self.action in ("reject", "modify"):
            # Check if feedback exists OR if legacy modifications is provided
            if not self.feedback and not self.modifications:
                raise ValueError("feedback is required when action is 'reject' or 'modify'")
        return self
