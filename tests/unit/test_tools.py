"""
Unit tests for tools — mocked HTTP, no external API calls.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.tools.budget_allocator import budget_allocator_tool
from app.tools.schedule_optimizer import schedule_optimizer_tool


class TestBudgetAllocator:

    def test_basic_allocation(self):
        result = budget_allocator_tool.invoke({
            "budget_min": 2000.0,
            "budget_max": 3000.0,
            "num_travelers": 2,
            "num_days": 7,
            "destination": "Kyoto, Japan",
            "interests": "temples, food",
        })
        assert "Accommodation" in result
        assert "Grand Total" in result
        assert "Per Person" in result
        assert "Within budget" in result

    def test_known_destination_cost_tier(self):
        result_cheap = budget_allocator_tool.invoke({
            "budget_min": 1000, "budget_max": 2000,
            "num_travelers": 2, "num_days": 5,
            "destination": "Bali", "interests": "beach",
        })
        result_expensive = budget_allocator_tool.invoke({
            "budget_min": 1000, "budget_max": 2000,
            "num_travelers": 2, "num_days": 5,
            "destination": "Zurich", "interests": "culture",
        })
        # Both should produce allocations without crashing
        assert "Bali" in result_cheap
        assert "Zurich" in result_expensive

    def test_food_interest_boosts_food_allocation(self):
        result = budget_allocator_tool.invoke({
            "budget_min": 2000, "budget_max": 3000,
            "num_travelers": 1, "num_days": 7,
            "destination": "Paris", "interests": "culinary, dining, restaurants",
        })
        assert "Food" in result


class TestScheduleOptimizer:

    def test_basic_optimization(self):
        import json
        activities = json.dumps([
            {"name": "Temple Visit", "description": "Historic shrine", "duration_hours": 2},
            {"name": "Dinner at restaurant", "description": "Local cuisine", "duration_hours": 1.5},
            {"name": "Hiking trail", "description": "Mountain hike", "duration_hours": 4},
        ])
        result = schedule_optimizer_tool.invoke({
            "activities_json": activities,
            "destination": "Kyoto",
            "num_days": 2,
            "preferences": "temples, hiking",
        })
        assert "Day 1" in result
        assert "Morning" in result or "morning" in result.lower()

    def test_invalid_json_gracefully_handled(self):
        result = schedule_optimizer_tool.invoke({
            "activities_json": "not valid json!!!",
            "destination": "Kyoto",
            "num_days": 3,
            "preferences": "food",
        })
        assert "invalid" in result.lower() or "error" in result.lower()

    def test_empty_activities(self):
        import json
        result = schedule_optimizer_tool.invoke({
            "activities_json": json.dumps([]),
            "destination": "Tokyo",
            "num_days": 2,
            "preferences": "culture",
        })
        assert "no activities" in result.lower()


class TestWebSearchTool:

    @patch("app.tools.web_search.httpx.Client")
    def test_successful_search(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "organic": [
                {"title": "Kyoto Travel Guide", "link": "https://example.com", "snippet": "Top things to do in Kyoto"},
                {"title": "Best Temples", "link": "https://example2.com", "snippet": "Famous temples in Kyoto"},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client_class.return_value.__enter__.return_value.post.return_value = mock_response

        from app.tools.web_search import web_search_tool
        result = web_search_tool.invoke({"query": "Kyoto Japan travel guide"})

        assert "Kyoto Travel Guide" in result
        assert "Best Temples" in result

    @patch("app.tools.web_search.httpx.Client")
    def test_timeout_degrades_gracefully(self, mock_client_class):
        import httpx
        mock_client_class.return_value.__enter__.return_value.post.side_effect = httpx.TimeoutException("timeout")

        from app.tools.web_search import web_search_tool
        result = web_search_tool.invoke({"query": "test query"})

        # Should not raise — should return a graceful error message
        assert "failed" in result.lower() or "error" in result.lower()


class TestWeatherTool:

    @patch("app.tools.weather.httpx.Client")
    def test_successful_weather(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "main": {"temp": 295.15, "humidity": 65},  # 22°C
            "weather": [{"description": "partly cloudy"}],
        }
        mock_response.raise_for_status = MagicMock()
        mock_client_class.return_value.__enter__.return_value.get.return_value = mock_response

        from app.tools.weather import weather_tool
        result = weather_tool.invoke({
            "destination": "Kyoto, Japan",
            "start_date": "2025-04-10",
            "end_date": "2025-04-17",
        })
        assert "Kyoto" in result
        assert "°C" in result

    @patch("app.tools.weather.httpx.Client")
    def test_api_failure_degrades_gracefully(self, mock_client_class):
        import httpx
        mock_client_class.return_value.__enter__.return_value.get.side_effect = httpx.TimeoutException("timeout")

        from app.tools.weather import weather_tool
        result = weather_tool.invoke({
            "destination": "Kyoto",
            "start_date": "2025-04-10",
            "end_date": "2025-04-17",
        })
        # Must not raise — graceful degradation
        assert "unavailable" in result.lower() or "could not" in result.lower()
