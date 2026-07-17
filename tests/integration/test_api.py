"""
Integration tests for the FastAPI layer.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.graph.state import STATUS_RESEARCHING


@pytest.mark.asyncio
async def test_create_plan_endpoint(async_client: AsyncClient):
    """Test that POST /plan returns 201 and a plan_id immediately."""
    payload = {
        "destination": "Kyoto, Japan",
        "start_date": "2025-04-10",
        "end_date": "2025-04-17",
        "budget_min": 2000,
        "budget_max": 3500,
        "budget_currency": "USD",
        "interests": ["temples", "food"],
        "num_travelers": 2
    }
    
    response = await async_client.post("/api/v1/plan", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert "plan_id" in data
    assert data["status"] == STATUS_RESEARCHING
    
    # Verify the plan exists in the repo
    plan_id = data["plan_id"]
    status_resp = await async_client.get(f"/api/v1/plan/{plan_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == STATUS_RESEARCHING


@pytest.mark.asyncio
async def test_get_plan_status_not_found(async_client: AsyncClient):
    """Test 404 behavior."""
    response = await async_client.get("/api/v1/plan/fake-id")
    assert response.status_code == 404
    assert response.json()["error"] == "PLAN_NOT_FOUND"


@pytest.mark.asyncio
async def test_review_invalid_state(async_client: AsyncClient):
    """Test 409 behavior when submitting a review before the plan is ready."""
    # Create a plan
    payload = {
        "destination": "Kyoto, Japan",
        "start_date": "2025-04-10",
        "end_date": "2025-04-17",
        "budget_min": 2000,
        "budget_max": 3500,
        "budget_currency": "USD",
        "interests": ["temples", "food"],
        "num_travelers": 2
    }
    
    create_resp = await async_client.post("/api/v1/plan", json=payload)
    plan_id = create_resp.json()["plan_id"]
    
    # Try to review immediately (it's in 'researching' status)
    review_payload = {
        "action": "approve"
    }
    review_resp = await async_client.post(f"/api/v1/plan/{plan_id}/review", json=review_payload)
    
    assert review_resp.status_code == 409
    assert review_resp.json()["error"] == "INVALID_STATE_TRANSITION"


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    """Test the health check endpoint."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_reject_without_feedback_is_422(async_client: AsyncClient):
    """Spec: reject requires non-empty feedback — must return 422."""
    # Create a plan first (we need a real plan_id; don't care about reaching review state)
    payload = {
        "destination": "Kyoto, Japan",
        "start_date": "2025-04-10",
        "end_date": "2025-04-17",
        "budget_min": 2000,
        "budget_max": 3500,
        "budget_currency": "USD",
        "interests": ["temples"],
        "num_travelers": 1,
    }
    create = await async_client.post("/api/v1/plan", json=payload)
    plan_id = create.json()["plan_id"]

    r = await async_client.post(
        f"/api/v1/plan/{plan_id}/review",
        json={"action": "reject"},  # missing feedback
    )
    assert r.status_code == 422
    body = r.json()
    # Must use consistent error schema, not raw FastAPI detail
    assert "error" in body
    assert body["error"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_modify_without_modifications_is_422(async_client: AsyncClient):
    """Spec: modify requires modification instructions — must return 422."""
    payload = {
        "destination": "Kyoto, Japan",
        "start_date": "2025-04-10",
        "end_date": "2025-04-17",
        "budget_min": 2000,
        "budget_max": 3500,
        "budget_currency": "USD",
        "interests": ["temples"],
        "num_travelers": 1,
    }
    create = await async_client.post("/api/v1/plan", json=payload)
    plan_id = create.json()["plan_id"]

    r = await async_client.post(
        f"/api/v1/plan/{plan_id}/review",
        json={"action": "modify"},  # missing modifications
    )
    assert r.status_code == 422
    body = r.json()
    assert "error" in body
    assert body["error"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_get_final_plan_not_finalized_is_409(async_client: AsyncClient):
    """Spec: GET /plan/{id}/final returns 409 if plan exists but is not finalized."""
    payload = {
        "destination": "Kyoto, Japan",
        "start_date": "2025-04-10",
        "end_date": "2025-04-17",
        "budget_min": 2000,
        "budget_max": 3500,
        "budget_currency": "USD",
        "interests": ["temples"],
        "num_travelers": 1,
    }
    create = await async_client.post("/api/v1/plan", json=payload)
    plan_id = create.json()["plan_id"]

    # Plan is in 'researching' state — not finalized
    r = await async_client.get(f"/api/v1/plan/{plan_id}/final")
    assert r.status_code == 409
    body = r.json()
    assert body["error"] == "PLAN_NOT_FINALIZED"
    assert body["plan_id"] == plan_id


@pytest.mark.asyncio
async def test_invalid_travel_request_body_is_422(async_client: AsyncClient):
    """Spec: validate input — bad request body returns 422 with consistent schema."""
    # end_date before start_date + budget_max < budget_min
    r = await async_client.post("/api/v1/plan", json={
        "destination": "Tokyo",
        "start_date": "2025-01-10",
        "end_date": "2025-01-09",   # before start
        "budget_min": 1000,
        "budget_max": 500,           # less than min
        "interests": ["food"],
        "num_travelers": 1,
    })
    assert r.status_code == 422
    body = r.json()
    assert "error" in body
    assert body["error"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_full_workflow_api_endpoints(async_client: AsyncClient):
    """
    Test the full workflow:
    1. POST /plan to create a plan
    2. Poll GET /plan/{plan_id} until status is awaiting_review
    3. POST /plan/{plan_id}/review to approve
    4. Poll GET /plan/{plan_id} until status is finalized
    5. GET /plan/{plan_id}/final to get the finalized itinerary
    """
    import asyncio
    from unittest.mock import patch
    from app.graph.state import STATUS_AWAITING_REVIEW, STATUS_FINALIZED

    payload = {
        "destination": "Kyoto, Japan",
        "start_date": "2025-04-10",
        "end_date": "2025-04-17",
        "budget_min": 2000,
        "budget_max": 3500,
        "budget_currency": "USD",
        "interests": ["temples", "food"],
        "num_travelers": 2
    }

    # Mock the agents to bypass LLM calls and return immediately
    with patch("app.graph.nodes.research_node.invoke_research_agent") as mock_research, \
         patch("app.graph.nodes.planner_node.invoke_planner_agent") as mock_planner, \
         patch("app.graph.nodes.finalize_node.finalize_node") as mock_finalize:
        
        mock_research.return_value = {"dummy": "research"}
        mock_planner.return_value = {"dummy": "itinerary", "version": 1}
        mock_finalize.return_value = {"status": STATUS_FINALIZED}

        # 1. Create plan
        response = await async_client.post("/api/v1/plan", json=payload)
        assert response.status_code == 201
        plan_id = response.json()["plan_id"]

        # 2. Wait for graph to reach hitl_review_node (awaiting_review)
        max_polls = 10
        status = ""
        for _ in range(max_polls):
            resp = await async_client.get(f"/api/v1/plan/{plan_id}")
            assert resp.status_code == 200
            data = resp.json()
            status = data["status"]
            if status == STATUS_AWAITING_REVIEW:
                # We should have the draft itinerary in the response
                assert "draft_itinerary" in data
                break
            await asyncio.sleep(0.1)
        
        assert status == STATUS_AWAITING_REVIEW

        # 3. Submit review decision
        review_payload = {"action": "approve"}
        review_resp = await async_client.post(f"/api/v1/plan/{plan_id}/review", json=review_payload)
        assert review_resp.status_code == 200
        assert review_resp.json()["status"] == STATUS_FINALIZED

        # 4. Wait for finalization to complete
        for _ in range(max_polls):
            resp = await async_client.get(f"/api/v1/plan/{plan_id}")
            assert resp.status_code == 200
            data = resp.json()
            status = data["status"]
            if status == STATUS_FINALIZED:
                break
            await asyncio.sleep(0.1)
            
        assert status == STATUS_FINALIZED

        # 5. Fetch final itinerary
        final_resp = await async_client.get(f"/api/v1/plan/{plan_id}/final")
        assert final_resp.status_code == 200
        final_data = final_resp.json()
        assert final_data["status"] == STATUS_FINALIZED
        assert "final_itinerary" in final_data
