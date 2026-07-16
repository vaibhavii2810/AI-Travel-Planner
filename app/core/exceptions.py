"""
Custom exception hierarchy.
Each exception maps to a specific HTTP status code.
FastAPI exception handlers in main.py consume these.
"""
from __future__ import annotations


class TravelPlannerError(Exception):
    """Base exception for all application errors."""

    http_status: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, plan_id: str | None = None):
        super().__init__(message)
        self.message = message
        self.plan_id = plan_id

    def to_dict(self) -> dict:
        payload: dict = {"error": self.error_code, "message": self.message}
        if self.plan_id:
            payload["plan_id"] = self.plan_id
        return payload


# ── 404 ──────────────────────────────────────────────────────────────────────

class PlanNotFoundError(TravelPlannerError):
    """Raised when a plan_id does not exist in the metadata store."""

    http_status = 404
    error_code = "PLAN_NOT_FOUND"

    def __init__(self, plan_id: str):
        super().__init__(f"Plan '{plan_id}' not found.", plan_id=plan_id)


# ── 409 ──────────────────────────────────────────────────────────────────────

class InvalidStateError(TravelPlannerError):
    """Raised when an action is invalid given the plan's current status."""

    http_status = 409
    error_code = "INVALID_STATE_TRANSITION"

    def __init__(self, plan_id: str, current_status: str, required_status: str):
        super().__init__(
            f"Plan '{plan_id}' is in status '{current_status}', "
            f"not '{required_status}'. Cannot perform this action.",
            plan_id=plan_id,
        )
        self.current_status = current_status
        self.required_status = required_status


class PlanNotFinalizedError(TravelPlannerError):
    """Raised when GET /final is called but the plan hasn't been approved yet."""

    http_status = 409
    error_code = "PLAN_NOT_FINALIZED"

    def __init__(self, plan_id: str, current_status: str):
        super().__init__(
            f"Plan '{plan_id}' has not been approved yet. "
            f"Current status: '{current_status}'.",
            plan_id=plan_id,
        )
        self.current_status = current_status


# ── 422 ──────────────────────────────────────────────────────────────────────

class MaxRevisionsError(TravelPlannerError):
    """Raised when the plan has exceeded the maximum allowed revision count."""

    http_status = 422
    error_code = "MAX_REVISIONS_EXCEEDED"

    def __init__(self, plan_id: str, max_revisions: int):
        super().__init__(
            f"Plan '{plan_id}' has exceeded the maximum of {max_revisions} revisions. "
            "Please start a new plan with more specific requirements.",
            plan_id=plan_id,
        )


# ── 500 ──────────────────────────────────────────────────────────────────────

class ToolExecutionError(TravelPlannerError):
    """Raised when an external tool (Serper, Weather API) fails after retries."""

    http_status = 500
    error_code = "TOOL_EXECUTION_ERROR"

    def __init__(self, tool_name: str, reason: str):
        super().__init__(f"Tool '{tool_name}' failed: {reason}")
        self.tool_name = tool_name


class LLMOutputParseError(TravelPlannerError):
    """Raised when the LLM fails to produce valid structured output after retries."""

    http_status = 500
    error_code = "LLM_OUTPUT_PARSE_ERROR"

    def __init__(self, schema_name: str, attempts: int):
        super().__init__(
            f"LLM failed to produce valid '{schema_name}' output after {attempts} attempt(s)."
        )


class GraphExecutionError(TravelPlannerError):
    """Raised when an unexpected error occurs during LangGraph execution."""

    http_status = 500
    error_code = "GRAPH_EXECUTION_ERROR"


# ── 503 ──────────────────────────────────────────────────────────────────────

class CheckpointerError(TravelPlannerError):
    """Raised when the LangGraph checkpointer (database) is unreachable."""

    http_status = 503
    error_code = "CHECKPOINTER_UNAVAILABLE"

    def __init__(self, reason: str):
        super().__init__(f"Checkpoint store unavailable: {reason}")
