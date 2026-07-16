"""
Conditional routing — executed after hitl_review_node resumes.

Risk 4 bypass:
- MAX_REVISIONS guard is checked HERE (in the edge), before dispatching to any agent
- Uses dedicated max_revisions_node for clean termination
- Intelligent reject routing via keyword heuristic (tested with parametrize)
"""
from __future__ import annotations

import logging
import re

from app.core.config import get_settings
from app.graph.state import TravelPlanState

logger = logging.getLogger("app.graph.edges.routing")

# Keywords that suggest the feedback needs re-RESEARCH (not just re-planning)
_RESEARCH_TRIGGER_KEYWORDS = frozenset({
    "research", "weather", "safety", "season", "seasonal", "attraction",
    "information", "outdated", "accurate", "wrong area", "location",
    "facts", "verify", "check", "current", "recent", "update",
    "unsafe", "dangerous", "advisory", "warning", "festival", "event",
    "opening", "closed", "hours",
})


def _needs_re_research(feedback: str) -> bool:
    """
    Heuristic: does the rejection feedback indicate research-level issues?
    Returns True → route to research_node
    Returns False → route to planner_node only
    """
    feedback_lower = feedback.lower()
    for keyword in _RESEARCH_TRIGGER_KEYWORDS:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, feedback_lower):
            return True
    return False


def route_after_review(state: TravelPlanState) -> str:
    """
    Conditional edge function executed after hitl_review_node.

    Returns the name of the next node to route to.

    Priority:
    1. MAX_REVISIONS guard — checked first, always
    2. approve → finalize_node
    3. modify → planner_node
    4. reject → research_node (if research-level issues) or planner_node
    """
    plan_id = state.get("plan_id", "unknown")
    revision_count = state.get("revision_count", 0)
    max_revisions = get_settings().MAX_REVISIONS

    # ── Risk 4 guard: check BEFORE routing to any agent ───────────────────────
    if revision_count >= max_revisions:
        logger.warning(
            f"route_after_review | plan_id={plan_id} | "
            f"revision_count={revision_count} >= max={max_revisions} → max_revisions_node"
        )
        return "max_revisions_node"

    review_decision = state.get("review_decision") or {}
    action = review_decision.get("action", "")
    feedback = review_decision.get("feedback") or ""

    if action == "approve":
        logger.info(f"route_after_review | plan_id={plan_id} | action=approve → finalize_node")
        return "finalize_node"

    elif action == "modify":
        logger.info(f"route_after_review | plan_id={plan_id} | action=modify → planner_node")
        return "planner_node"

    elif action == "reject":
        if _needs_re_research(feedback):
            logger.info(
                f"route_after_review | plan_id={plan_id} | action=reject | "
                f"feedback triggers re-research → research_node"
            )
            return "research_node"
        else:
            logger.info(
                f"route_after_review | plan_id={plan_id} | action=reject | "
                f"feedback is planner-level → planner_node"
            )
            return "planner_node"

    # Fallback — should not normally reach here
    logger.error(
        f"route_after_review | plan_id={plan_id} | unknown action='{action}' → planner_node"
    )
    return "planner_node"
