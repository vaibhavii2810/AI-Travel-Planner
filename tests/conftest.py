"""
Test configuration and fixtures.
Uses MemorySaver + FakeListChatModel for fast, deterministic tests.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import Settings
from app.graph.graph import build_graph
from app.graph.state import initial_state
from app.models.domain import (
    Activity,
    Attraction,
    BudgetAllocation,
    DailyPlan,
    DraftItinerary,
    ResearchOutput,
    TravelRequest,
    WeatherSummary,
)
from app.services.plan_repository import PlanRepository
from app.services.planning_service import PlanningService


# ── Settings override for tests ───────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_settings():
    """Override settings for test environment."""
    import os
    os.environ.setdefault("ENV", "test")
    os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake-key-for-testing")
    os.environ.setdefault("SERPER_API_KEY", "fake-serper-key")
    os.environ.setdefault("WEATHER_API_KEY", "fake-weather-key")
    # Reset cached settings
    from app.core.config import get_settings
    get_settings.cache_clear()
    return get_settings()


# ── Domain fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def sample_travel_request() -> TravelRequest:
    return TravelRequest(
        destination="Kyoto, Japan",
        start_date=date(2025, 4, 10),
        end_date=date(2025, 4, 17),
        budget_min=2000.0,
        budget_max=3500.0,
        budget_currency="USD",
        interests=["temples", "food", "hiking"],
        num_travelers=2,
    )


@pytest.fixture
def sample_research_output() -> ResearchOutput:
    return ResearchOutput(
        attractions=[
            Attraction(
                name="Fushimi Inari Shrine",
                description="Famous torii gate mountain trail",
                category="temple",
                estimated_visit_duration_hours=3.0,
                approximate_cost_per_person=0.0,
            ),
            Attraction(
                name="Arashiyama Bamboo Grove",
                description="Iconic bamboo forest walk",
                category="nature",
                estimated_visit_duration_hours=1.5,
                approximate_cost_per_person=0.0,
            ),
        ],
        local_tips=["Buy an IC card for transit", "Bow when entering temples"],
        safety_considerations=["Very safe city", "Watch for pickpockets in crowded areas"],
        weather_summary=WeatherSummary(
            avg_temp_celsius=18.0,
            avg_temp_fahrenheit=64.4,
            conditions="Partly cloudy with mild temperatures",
            precipitation_chance_percent=20.0,
            humidity_percent=60.0,
            warnings=[],
            data_available=True,
        ),
        seasonal_notes="April is cherry blossom season — very crowded but beautiful",
        general_destination_info="Kyoto is Japan's former imperial capital",
        research_sources=["https://www.japan-guide.com/e/e3900.html"],
        researched_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_draft_itinerary() -> DraftItinerary:
    return DraftItinerary(
        version=1,
        daily_plans=[
            DailyPlan(
                day_number=1,
                date=date(2025, 4, 10),
                theme="Ancient Temples",
                morning=[
                    Activity(
                        name="Fushimi Inari Shrine",
                        description="Walk through thousands of torii gates",
                        location="Fushimi Ward",
                        duration_minutes=180,
                        estimated_cost_per_person=0.0,
                    )
                ],
                afternoon=[
                    Activity(
                        name="Lunch at Nishiki Market",
                        description="Sample local street food",
                        location="Central Kyoto",
                        duration_minutes=90,
                        estimated_cost_per_person=15.0,
                    )
                ],
                evening=[
                    Activity(
                        name="Gion District Walk",
                        description="Evening stroll through geisha district",
                        location="Gion",
                        duration_minutes=120,
                        estimated_cost_per_person=0.0,
                    )
                ],
                accommodation="Traditional Ryokan, Central Kyoto",
                estimated_daily_cost_per_person=150.0,
                travel_notes="Use subway for most travel",
            )
        ],
        budget_allocation=BudgetAllocation(
            accommodation_total=1050.0,
            transport_total=600.0,
            food_total=750.0,
            activities_total=450.0,
            contingency_total=150.0,
            grand_total=3000.0,
            per_person_total=1500.0,
            currency="USD",
            within_budget=True,
        ),
        overall_tips=["Book accommodations well in advance for cherry blossom season"],
        packing_suggestions=["Comfortable walking shoes", "Light rain jacket"],
        generated_at=datetime.utcnow(),
    )


# ── Graph / LangGraph fixtures ────────────────────────────────────────────────

@pytest.fixture
def memory_checkpointer() -> MemorySaver:
    return MemorySaver()


@pytest.fixture
def compiled_graph(memory_checkpointer):
    """A compiled graph with MemorySaver — for integration tests."""
    return build_graph(checkpointer=memory_checkpointer)


# ── FastAPI test client ───────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def async_client(test_settings) -> AsyncGenerator[AsyncClient, None]:
    """
    Full FastAPI test client with mocked graph execution.
    Lifespan is bypassed in favor of direct app.state injection.
    """
    from app.main import create_app

    test_app = create_app()

    # Wire app.state manually (bypass lifespan for speed)
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    plan_repo = PlanRepository()
    planning_service = PlanningService(graph=graph, plan_repo=plan_repo)

    test_app.state.checkpointer = checkpointer
    test_app.state.graph = graph
    test_app.state.plan_repo = plan_repo
    test_app.state.planning_service = planning_service

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        yield client
