"""
Integration tests for the FastAPI layer.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.graph.state import STATUS_RESEARCHING


@pytest.mark.asyncio
async def test_create_plan_endpoint(async_client: AsyncClient):
    """Test that POST /plan returns 202 and a plan_id immediately."""
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
    assert response.status_code == 202
    
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
