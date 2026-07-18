"""
Integration test: Modify × 2 → Reject via POST /plan/{id}/review.

Assertions:
  (a) each modify routes to planner, version increments, other days preserved
  (b) state persists correctly across calls (revision_count, draft)
  (c) reject routes to rejected_node, status == "rejected", no re-planning
  (d) correct HTTP status codes throughout
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.graph.state import (
    STATUS_AWAITING_REVIEW,
    STATUS_REJECTED,
    STATUS_REVISING,
)
from app.models.domain import (
    Activity,
    Attraction,
    BudgetAllocation,
    DailyPlan,
    DraftItinerary,
    ResearchOutput,
    WeatherSummary,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_draft(version: int, day1_theme: str = "Day 1 Theme", day2_theme: str = "Day 2 Theme") -> DraftItinerary:
    """Build a minimal two-day DraftItinerary for mocking."""
    def _activity(name: str) -> Activity:
        return Activity(
            name=name,
            description=f"Description of {name}",
            location="Goa, India",
            duration_minutes=60,
            estimated_cost_per_person=10.0,
        )

    return DraftItinerary(
        version=version,
        daily_plans=[
            DailyPlan(
                day_number=1,
                date=date(2025, 12, 1),
                theme=day1_theme,
                morning=[_activity("Scuba Diving")],
                afternoon=[_activity("Beach Walk")],
                evening=[_activity("Sunset Dinner")],
                accommodation="Beach Hotel",
                estimated_daily_cost_per_person=200.0,
                travel_notes="Original Day 1 notes",
            ),
            DailyPlan(
                day_number=2,
                date=date(2025, 12, 2),
                theme=day2_theme,
                morning=[_activity("Yoga at Sunrise")],
                afternoon=[_activity("Spice Tour")],
                evening=[_activity("Night Market")],
                accommodation="Beach Hotel",
                estimated_daily_cost_per_person=180.0,
                travel_notes="Original Day 2 notes",
            ),
        ],
        budget_allocation=BudgetAllocation(
            accommodation_total=800.0,
            transport_total=200.0,
            food_total=300.0,
            activities_total=400.0,
            contingency_total=100.0,
            grand_total=1800.0,
            per_person_total=900.0,
            currency="INR",
            within_budget=True,
        ),
        overall_tips=["Tip 1"],
        packing_suggestions=["Sunscreen"],
        generated_at=datetime.utcnow(),
    )


async def _poll_for_status(client, plan_id: str, target_status: str, max_polls: int = 20) -> dict:
    """Poll GET /plan/{id} until the target_status is reached or timeout."""
    for _ in range(max_polls):
        resp = await client.get(f"/api/v1/plan/{plan_id}")
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] == target_status:
            return data
        await asyncio.sleep(0.1)
    raise AssertionError(
        f"Timed out waiting for status={target_status!r}. Last status: {data.get('status')!r}"
    )

def _make_research() -> ResearchOutput:
    """Build a real ResearchOutput object for mocking."""
    return ResearchOutput(
        attractions=[
            Attraction(
                name="Baga Beach",
                description="Popular beach in North Goa",
                category="beach",
                estimated_visit_duration_hours=3.0,
                approximate_cost_per_person=0.0,
            )
        ],
        local_tips=["Bargain at local markets"],
        safety_considerations=["Relatively safe"],
        weather_summary=WeatherSummary(
            avg_temp_celsius=30.0,
            avg_temp_fahrenheit=86.0,
            conditions="Sunny",
            precipitation_chance_percent=10.0,
            humidity_percent=70.0,
            warnings=[],
            data_available=True,
        ),
        seasonal_notes="December is peak season in Goa",
        general_destination_info="Goa is famous for its beaches and nightlife",
        research_sources=["https://www.goa.gov.in"],
        researched_at=datetime.now(timezone.utc),
    )

# ─── Test ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_modify_twice_then_reject(async_client):
    """
    Full HITL sequence:
      1. Create plan  →  poll until awaiting_review
      2. Modify #1    →  planner runs, version=2, Day 2 UNCHANGED
      3. Modify #2    →  planner runs, version=3, Day 1 UNCHANGED
      4. Reject       →  status=rejected, NO re-planning, graph terminates
    """

    # ── 1. Create Plan ─────────────────────────────────────────────────────────
    create_payload = {
        "destination": "Goa, India",
        "start_date": "2025-12-01",
        "end_date": "2025-12-02",
        "budget_min": 1000,
        "budget_max": 2000,
        "budget_currency": "INR",
        "interests": ["beach", "food"],
        "num_travelers": 2,
    }

    draft_v1 = _make_draft(version=1)
    draft_v2 = _make_draft(version=2, day1_theme="✏️ Modified Day 1")
    # draft_v3 simulates planner preserving Day 1 (from v2) and only modifying Day 2
    draft_v3 = _make_draft(version=3, day1_theme="✏️ Modified Day 1", day2_theme="✏️ Modified Day 2")

    planner_responses = [draft_v1, draft_v2, draft_v3]
    planner_call_count = 0

    async def mock_planner(*args, **kwargs):
        nonlocal planner_call_count
        result = planner_responses[min(planner_call_count, len(planner_responses) - 1)]
        planner_call_count += 1
        return result

    with patch("app.graph.nodes.research_node.invoke_research_agent") as mock_research, \
         patch("app.graph.nodes.planner_node.invoke_planner_agent", side_effect=mock_planner):

        mock_research.return_value = _make_research()

        # POST /plan — should return 202
        resp = await async_client.post("/api/v1/plan", json=create_payload)
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        plan_id = resp.json()["plan_id"]
        assert plan_id, "plan_id must be returned"

        # Poll until awaiting_review
        status_data = await _poll_for_status(async_client, plan_id, STATUS_AWAITING_REVIEW)
        assert status_data["status"] == STATUS_AWAITING_REVIEW
        # (d) HTTP 200 for GET
        resp_get = await async_client.get(f"/api/v1/plan/{plan_id}")
        assert resp_get.status_code == 200

        # ── 2. Modify #1 — target Day 1 ────────────────────────────────────────
        modify1_payload = {
            "action": "modify",
            "feedback": "[Target: Day 1] Replace Scuba Diving with Jet Skiing.",
        }
        resp_m1 = await async_client.post(f"/api/v1/plan/{plan_id}/review", json=modify1_payload)
        # (d) 200 on review submission
        assert resp_m1.status_code == 200, f"Modify#1 failed: {resp_m1.text}"
        review_body_m1 = resp_m1.json()
        assert review_body_m1["action_received"] == "modify"
        assert review_body_m1["status"] == STATUS_REVISING

        # Poll until back to awaiting_review (planner has run)
        status_after_m1 = await _poll_for_status(async_client, plan_id, STATUS_AWAITING_REVIEW)

        # (a) version incremented to 2
        draft_after_m1 = status_after_m1.get("draft_itinerary")
        assert draft_after_m1 is not None, "draft_itinerary missing after modify#1"
        assert draft_after_m1["version"] == 2, f"Expected version=2, got {draft_after_m1['version']}"

        # (a) Day 1 theme changed
        day1_after_m1 = draft_after_m1["daily_plans"][0]
        assert "Modified" in day1_after_m1["theme"], (
            f"Day 1 theme should reflect modification, got: {day1_after_m1['theme']}"
        )

        # (a) Day 2 preserved — theme unchanged from original
        day2_after_m1 = draft_after_m1["daily_plans"][1]
        assert day2_after_m1["theme"] == "Day 2 Theme", (
            f"Day 2 should be UNCHANGED after modify#1, got: {day2_after_m1['theme']}"
        )

        # (b) revision_count == 2 (initial plan=1, modify1=2)
        assert status_after_m1["revision_count"] == 2

        # ── 3. Modify #2 — target Day 2 ────────────────────────────────────────
        modify2_payload = {
            "action": "modify",
            "feedback": "[Target: Day 2] Replace Spice Tour with Dolphin Watching.",
        }
        resp_m2 = await async_client.post(f"/api/v1/plan/{plan_id}/review", json=modify2_payload)
        assert resp_m2.status_code == 200, f"Modify#2 failed: {resp_m2.text}"
        assert resp_m2.json()["action_received"] == "modify"

        status_after_m2 = await _poll_for_status(async_client, plan_id, STATUS_AWAITING_REVIEW)

        draft_after_m2 = status_after_m2.get("draft_itinerary")
        assert draft_after_m2 is not None, "draft_itinerary missing after modify#2"
        assert draft_after_m2["version"] == 3, f"Expected version=3, got {draft_after_m2['version']}"

        # (a) Day 2 theme now modified
        day2_after_m2 = draft_after_m2["daily_plans"][1]
        assert "Modified" in day2_after_m2["theme"], (
            f"Day 2 theme should reflect modification, got: {day2_after_m2['theme']}"
        )

        # (a) Day 1 preserved from modify#2 perspective
        day1_after_m2 = draft_after_m2["daily_plans"][0]
        assert day1_after_m2["theme"] == "✏️ Modified Day 1", (
            f"Day 1 should be preserved after modify#2, got: {day1_after_m2['theme']}"
        )

        # (b) revision_count == 3 (initial=1, modify1=2, modify2=3)
        assert status_after_m2["revision_count"] == 3

        # (b) plan_id unchanged throughout
        assert status_after_m2["plan_id"] == plan_id

        # ── 4. Reject ───────────────────────────────────────────────────────────
        reject_payload = {
            "action": "reject",
            "feedback": "This plan doesn't suit my budget at all. Please start over.",
        }
        resp_r = await async_client.post(f"/api/v1/plan/{plan_id}/review", json=reject_payload)
        # (d) 200 on reject submission
        assert resp_r.status_code == 200, f"Reject failed: {resp_r.text}"
        reject_body = resp_r.json()
        assert reject_body["action_received"] == "reject"
        # Response immediately reflects rejected status
        assert reject_body["status"] == STATUS_REJECTED

        # Poll until rejected status is persisted
        status_after_reject = await _poll_for_status(async_client, plan_id, STATUS_REJECTED)
        # (c) status is rejected
        assert status_after_reject["status"] == STATUS_REJECTED

        # (c) no further re-planning — planner was called only 3 times (once per plan + 2 modifies)
        # reject goes to rejected_node, NOT planner_node
        assert planner_call_count == 3, (
            f"Planner should have been called exactly 3 times (initial+modify1+modify2), "
            f"got {planner_call_count} — reject must NOT trigger re-planning"
        )

        # (c) revision_count is still 3 — reject does not increment it
        assert status_after_reject["revision_count"] == 3

        # (d) GET after reject returns 200 (plan record still readable)
        resp_get_final = await async_client.get(f"/api/v1/plan/{plan_id}")
        assert resp_get_final.status_code == 200
        assert resp_get_final.json()["status"] == STATUS_REJECTED


@pytest.mark.asyncio
async def test_reject_with_no_prior_approval_sets_rejected(async_client):
    """
    (c) Edge case: reject on a brand-new plan (no approved version).
    Status must be 'rejected'. No crash, no infinite loop.
    """
    create_payload = {
        "destination": "Paris, France",
        "start_date": "2025-06-01",
        "end_date": "2025-06-02",
        "budget_min": 500,
        "budget_max": 1000,
        "budget_currency": "EUR",
        "interests": ["culture"],
        "num_travelers": 1,
    }

    draft_v1 = _make_draft(version=1)

    with patch("app.graph.nodes.research_node.invoke_research_agent") as mock_research, \
         patch("app.graph.nodes.planner_node.invoke_planner_agent", return_value=draft_v1):

        mock_research.return_value = _make_research()

        resp = await async_client.post("/api/v1/plan", json=create_payload)
        assert resp.status_code == 201
        plan_id = resp.json()["plan_id"]

        await _poll_for_status(async_client, plan_id, STATUS_AWAITING_REVIEW)

        reject_payload = {
            "action": "reject",
            "feedback": "I changed my mind entirely.",
        }
        resp_r = await async_client.post(f"/api/v1/plan/{plan_id}/review", json=reject_payload)
        assert resp_r.status_code == 200
        assert resp_r.json()["status"] == STATUS_REJECTED

        status_after = await _poll_for_status(async_client, plan_id, STATUS_REJECTED)
        assert status_after["status"] == STATUS_REJECTED
