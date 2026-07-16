"""
Unit tests for routing logic (Risk 4 bypass verification).
Tests all action/feedback combinations exhaustively.
"""
from __future__ import annotations

import pytest

from app.graph.edges.routing import _needs_re_research, route_after_review
from app.graph.state import TravelPlanState


def _make_state(action: str, feedback: str = "", revision_count: int = 0) -> dict:
    return {
        "plan_id": "test-plan-001",
        "revision_count": revision_count,
        "review_decision": {
            "action": action,
            "feedback": feedback,
            "modifications": {"day": 1, "change": "swap museum"} if action == "modify" else None,
        },
    }


# ── _needs_re_research ────────────────────────────────────────────────────────

@pytest.mark.parametrize("feedback,expected", [
    # Should trigger re-research
    ("The weather information is wrong", True),
    ("Please research the safety situation more", True),
    ("The seasonal notes are outdated", True),
    ("Check current travel advisories", True),
    ("The attraction hours are wrong", True),
    ("Please verify the temple opening times", True),
    ("The festival dates need to be updated", True),
    ("Area safety concerns are off", True),
    ("Information seems outdated from last year", True),
    # Should NOT trigger re-research (planner-level only)
    ("Day 3 is too expensive", False),
    ("Add more restaurant options", False),
    ("The budget allocation seems off", False),
    ("I want more hiking activities", False),
    ("Swap museum visit with cooking class", False),
    ("The schedule is too packed", False),
    ("I need more free time in the evenings", False),
    ("", False),  # Empty feedback → planner default
])
def test_needs_re_research(feedback: str, expected: bool):
    assert _needs_re_research(feedback) == expected


# ── route_after_review ────────────────────────────────────────────────────────

class TestRouteAfterReview:

    def test_approve_routes_to_finalize(self):
        state = _make_state("approve")
        assert route_after_review(state) == "finalize_node"

    def test_modify_routes_to_planner(self):
        state = _make_state("modify")
        assert route_after_review(state) == "planner_node"

    def test_reject_with_research_feedback_routes_to_research(self):
        state = _make_state("reject", feedback="The weather data seems wrong and outdated")
        assert route_after_review(state) == "research_node"

    def test_reject_with_planner_feedback_routes_to_planner(self):
        state = _make_state("reject", feedback="Day 2 is too expensive, please cut costs")
        assert route_after_review(state) == "planner_node"

    def test_reject_empty_feedback_routes_to_planner(self):
        state = _make_state("reject", feedback="")
        assert route_after_review(state) == "planner_node"

    def test_max_revisions_guard_fires_before_approve(self, test_settings):
        """MAX_REVISIONS guard has priority — even approve is overridden."""
        max_rev = test_settings.MAX_REVISIONS
        state = _make_state("approve", revision_count=max_rev)
        assert route_after_review(state) == "max_revisions_node"

    def test_max_revisions_guard_fires_before_reject(self, test_settings):
        max_rev = test_settings.MAX_REVISIONS
        state = _make_state("reject", feedback="wrong weather", revision_count=max_rev)
        assert route_after_review(state) == "max_revisions_node"

    def test_below_max_revisions_does_not_trigger_guard(self, test_settings):
        max_rev = test_settings.MAX_REVISIONS
        state = _make_state("approve", revision_count=max_rev - 1)
        assert route_after_review(state) == "finalize_node"

    def test_unknown_action_falls_back_to_planner(self):
        state = _make_state("unknown_action")
        assert route_after_review(state) == "planner_node"
