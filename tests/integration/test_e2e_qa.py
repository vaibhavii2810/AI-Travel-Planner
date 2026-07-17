"""
Prompt 8 — End-to-End QA: Tests covering the gaps identified in the specification review.

Gaps covered:
- Edge cases at the API boundary (blank destination, zero travelers, negative budget)
- Serper auth error (HTTP 401) graceful degradation
- Graph flow: reject with re-research trigger
- Duplicate review after finalization (409)
- _store isolation is guaranteed by the autouse clear_plan_repo fixture in conftest.py
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch

from app.graph.state import (
    STATUS_AWAITING_REVIEW,
    STATUS_FINALIZED,
    initial_state,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

VALID_PAYLOAD = {
    "destination": "Kyoto, Japan",
    "start_date": "2025-04-10",
    "end_date": "2025-04-17",
    "budget_min": 2000,
    "budget_max": 3500,
    "budget_currency": "USD",
    "interests": ["temples", "food"],
    "num_travelers": 2,
}


# ── Edge cases: input validation (API layer) ──────────────────────────────────

class TestInputValidationEdgeCases:
    """
    Prompt 8 edge cases that must be rejected at the API layer with 422 + consistent schema.
    """

    @pytest.mark.asyncio
    async def test_blank_destination_is_422(self, async_client: AsyncClient):
        """Empty string destination must fail (min_length=2)."""
        payload = {**VALID_PAYLOAD, "destination": ""}
        r = await async_client.post("/api/v1/plan", json=payload)
        assert r.status_code == 422
        assert r.json()["error"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_one_char_destination_is_422(self, async_client: AsyncClient):
        """Single-char destination must fail (min_length=2)."""
        payload = {**VALID_PAYLOAD, "destination": "X"}
        r = await async_client.post("/api/v1/plan", json=payload)
        assert r.status_code == 422
        assert r.json()["error"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_zero_travelers_is_422(self, async_client: AsyncClient):
        """num_travelers=0 must fail (ge=1)."""
        payload = {**VALID_PAYLOAD, "num_travelers": 0}
        r = await async_client.post("/api/v1/plan", json=payload)
        assert r.status_code == 422
        assert r.json()["error"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_negative_budget_min_is_422(self, async_client: AsyncClient):
        """budget_min <= 0 must fail (gt=0)."""
        payload = {**VALID_PAYLOAD, "budget_min": -100, "budget_max": 100}
        r = await async_client.post("/api/v1/plan", json=payload)
        assert r.status_code == 422
        assert r.json()["error"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_zero_budget_min_is_422(self, async_client: AsyncClient):
        """budget_min=0 must fail (gt=0 means strictly positive)."""
        payload = {**VALID_PAYLOAD, "budget_min": 0, "budget_max": 100}
        r = await async_client.post("/api/v1/plan", json=payload)
        assert r.status_code == 422
        assert r.json()["error"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_end_date_before_start_date_is_422(self, async_client: AsyncClient):
        """end_date < start_date must fail."""
        payload = {**VALID_PAYLOAD, "start_date": "2025-04-10", "end_date": "2025-04-09"}
        r = await async_client.post("/api/v1/plan", json=payload)
        assert r.status_code == 422
        assert r.json()["error"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_max_budget_below_min_budget_is_422(self, async_client: AsyncClient):
        """budget_max < budget_min must fail."""
        payload = {**VALID_PAYLOAD, "budget_min": 3000, "budget_max": 500}
        r = await async_client.post("/api/v1/plan", json=payload)
        assert r.status_code == 422
        assert r.json()["error"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_invalid_review_action_is_422(self, async_client: AsyncClient):
        """action not in Literal['approve','reject','modify'] must fail."""
        # Create a plan first so we have a real plan_id
        create = await async_client.post("/api/v1/plan", json=VALID_PAYLOAD)
        plan_id = create.json()["plan_id"]

        r = await async_client.post(
            f"/api/v1/plan/{plan_id}/review",
            json={"action": "YOLO"},
        )
        assert r.status_code == 422
        assert r.json()["error"] == "VALIDATION_ERROR"


# ── Edge case: duplicate review after finalization ────────────────────────────

class TestDuplicateReviewAfterFinalization:
    """
    Prompt 8: "duplicate review after finalization" must return 409.
    The plan repo status is 'finalized'; submit_review enforces awaiting_review.
    """

    @pytest.mark.asyncio
    async def test_review_after_finalization_is_409(self, async_client: AsyncClient):
        import asyncio

        with patch("app.graph.nodes.research_node.invoke_research_agent") as mock_research, \
             patch("app.graph.nodes.planner_node.invoke_planner_agent") as mock_planner, \
             patch("app.graph.nodes.finalize_node.finalize_node") as mock_finalize:

            mock_research.return_value = {"dummy": "research"}
            mock_planner.return_value = {"dummy": "itinerary", "version": 1}
            mock_finalize.return_value = {"status": STATUS_FINALIZED}

            # Create plan
            create_resp = await async_client.post("/api/v1/plan", json=VALID_PAYLOAD)
            assert create_resp.status_code == 201
            plan_id = create_resp.json()["plan_id"]

            # Wait until awaiting_review
            for _ in range(20):
                resp = await async_client.get(f"/api/v1/plan/{plan_id}")
                if resp.json()["status"] == STATUS_AWAITING_REVIEW:
                    break
                await asyncio.sleep(0.05)

            assert resp.json()["status"] == STATUS_AWAITING_REVIEW

            # First review: approve → should succeed
            approve_resp = await async_client.post(
                f"/api/v1/plan/{plan_id}/review",
                json={"action": "approve"},
            )
            assert approve_resp.status_code == 200

            # Wait for finalization
            for _ in range(20):
                resp = await async_client.get(f"/api/v1/plan/{plan_id}")
                if resp.json()["status"] == STATUS_FINALIZED:
                    break
                await asyncio.sleep(0.05)

            # Second review: must be rejected with 409
            duplicate_resp = await async_client.post(
                f"/api/v1/plan/{plan_id}/review",
                json={"action": "approve"},
            )
            assert duplicate_resp.status_code == 409
            body = duplicate_resp.json()
            assert body["error"] == "INVALID_STATE_TRANSITION"
            assert body["plan_id"] == plan_id


# ── Tool: Serper auth error graceful degradation ──────────────────────────────

class TestSerperAuthError:
    """
    Prompt 8: "Serper authentication error" must degrade gracefully (no crash/500).
    Simulates HTTP 401 from Serper API.
    """

    @patch("app.tools.web_search.httpx.Client")
    def test_serper_401_degrades_gracefully(self, mock_client_class):
        """HTTP 401 from Serper must be caught and returned as a user-friendly string."""
        import httpx
        from app.tools.web_search import web_search_tool

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=mock_response,
        )
        mock_client_class.return_value.__enter__.return_value.post.return_value = mock_response

        result = web_search_tool.invoke({"query": "Kyoto Japan travel"})

        # Must NOT raise — must return a graceful error string
        assert isinstance(result, str)
        assert "failed" in result.lower() or "error" in result.lower() or "401" in result

    @patch("app.tools.web_search.httpx.Client")
    def test_serper_403_degrades_gracefully(self, mock_client_class):
        """HTTP 403 from Serper (invalid plan, over quota) must degrade gracefully."""
        import httpx
        from app.tools.web_search import web_search_tool

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden: quota exceeded"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "403 Forbidden",
            request=MagicMock(),
            response=mock_response,
        )
        mock_client_class.return_value.__enter__.return_value.post.return_value = mock_response

        result = web_search_tool.invoke({"query": "Tokyo attractions"})
        assert isinstance(result, str)
        assert "failed" in result.lower() or "403" in result


# ── Graph: reject with re-research routing ────────────────────────────────────

class TestRejectWithReResearch:
    """
    Prompt 8 Flow B full graph path: reject with research-triggering feedback
    must route back through research_node (not just planner_node).
    """

    @pytest.mark.asyncio
    async def test_reject_triggers_research_node(self, compiled_graph, sample_travel_request):
        """
        Verify that feedback mentioning weather/safety/outdated info causes
        the graph to call research_node again on resume.
        """
        plan_id = "test-flow-b-re-research"
        config = {"configurable": {"thread_id": plan_id}}
        state = initial_state(plan_id, sample_travel_request)

        from langgraph.types import Command

        with patch("app.graph.nodes.research_node.invoke_research_agent") as mock_research, \
             patch("app.graph.nodes.planner_node.invoke_planner_agent") as mock_planner:

            mock_research.return_value = {"dummy": "research"}
            mock_planner.return_value = {"dummy": "itinerary", "version": 1}

            # Run to first HITL pause
            result = await compiled_graph.ainvoke(state, config=config)
            assert result.get("status") == STATUS_AWAITING_REVIEW

            # Reject with feedback that triggers re-research
            research_feedback = {
                "action": "reject",
                "feedback": "The weather information is completely wrong and outdated",
                "modifications": None,
            }

            resumed = await compiled_graph.ainvoke(
                Command(resume=research_feedback), config=config
            )

            # After re-research + re-plan it should be back at awaiting_review
            assert resumed.get("status") == STATUS_AWAITING_REVIEW
            assert resumed.get("revision_count") == 2

            # Research must have been called TWICE (initial + re-research)
            assert mock_research.call_count == 2
            # Planner must have been called TWICE (initial + revision)
            assert mock_planner.call_count == 2
