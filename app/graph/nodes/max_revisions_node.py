"""
Max Revisions Node — clean terminal state when revision limit is exceeded.
No LLM call. Routes to END cleanly (Risk 4 bypass).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.logging import log_node_entry, log_node_exit
from app.graph.state import STATUS_MAX_REVISIONS, TravelPlanState

logger = logging.getLogger("app.graph.nodes.max_revisions_node")


def max_revisions_node(state: TravelPlanState) -> dict:
    """
    LangGraph node: Terminates the graph cleanly when MAX_REVISIONS is exceeded.

    Sets status to 'max_revisions_exceeded' with a descriptive error message.
    Routes to END — no infinite loop possible.
    """
    plan_id = state.get("plan_id", "unknown")
    revision_count = state.get("revision_count", 0)
    max_revisions = get_settings().MAX_REVISIONS

    log_node_entry(logger, "max_revisions_node", plan_id, {"revision_count": revision_count})

    error_message = (
        f"Maximum revision limit ({max_revisions}) has been reached after {revision_count} revision(s). "
        "The planning workflow has been terminated. "
        "Please start a new plan (POST /plan) with more specific requirements."
    )

    logger.warning(f"max_revisions_node | plan_id={plan_id} | limit={max_revisions} reached")
    log_node_exit(logger, "max_revisions_node", plan_id, STATUS_MAX_REVISIONS)

    return {
        "status": STATUS_MAX_REVISIONS,
        "error_message": error_message,
        "updated_at": datetime.now(timezone.utc),
    }
