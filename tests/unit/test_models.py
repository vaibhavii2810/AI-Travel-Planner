"""
Unit tests for domain models — validation, coercion, and edge cases.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.models.domain import (
    Activity,
    Attraction,
    BudgetAllocation,
    DailyPlan,
    DraftItinerary,
    TravelRequest,
    WeatherSummary,
)


class TestTravelRequest:

    def test_valid_request(self):
        req = TravelRequest(
            destination="Tokyo, Japan",
            start_date=date(2025, 5, 1),
            end_date=date(2025, 5, 8),
            budget_min=1500.0,
            budget_max=3000.0,
            interests=["food", "culture"],
            num_travelers=2,
        )
        assert req.num_days == 7

    def test_end_before_start_raises(self):
        with pytest.raises(ValueError, match="end_date must be after start_date"):
            TravelRequest(
                destination="Paris",
                start_date=date(2025, 5, 10),
                end_date=date(2025, 5, 5),
                budget_min=1000,
                budget_max=2000,
                interests=["art"],
                num_travelers=1,
            )

    def test_budget_max_less_than_min_raises(self):
        with pytest.raises(ValueError, match="budget_max must be >= budget_min"):
            TravelRequest(
                destination="Paris",
                start_date=date(2025, 5, 1),
                end_date=date(2025, 5, 8),
                budget_min=3000,
                budget_max=1000,
                interests=["art"],
                num_travelers=1,
            )

    def test_single_day_trip_raises(self):
        with pytest.raises(ValueError):
            TravelRequest(
                destination="Paris",
                start_date=date(2025, 5, 1),
                end_date=date(2025, 5, 1),  # same day
                budget_min=1000,
                budget_max=2000,
                interests=["art"],
                num_travelers=1,
            )


class TestActivityCoercion:
    """Tests Risk 5 bypass: LLM often sends strings where numbers expected."""

    def test_string_duration_coerced(self):
        act = Activity(
            name="Museum Visit",
            duration_minutes="90",       # string → should coerce to 90.0
            estimated_cost_per_person="25",
        )
        assert act.duration_minutes == 90.0
        assert act.estimated_cost_per_person == 25.0

    def test_invalid_duration_defaults_to_zero(self):
        act = Activity(
            name="Museum Visit",
            duration_minutes="not-a-number",
        )
        assert act.duration_minutes == 0.0

    def test_extra_fields_ignored(self):
        """extra='ignore' must silently drop LLM-added fields."""
        act = Activity(
            name="Hike",
            llm_confidence=0.95,   # LLM hallucinated field
            some_extra_key="value",
        )
        assert not hasattr(act, "llm_confidence")


class TestWeatherSummaryCoercion:

    def test_string_temperature_coerced(self):
        ws = WeatherSummary(
            avg_temp_celsius="22.5",
            avg_temp_fahrenheit="72.5",
        )
        assert ws.avg_temp_celsius == 22.5

    def test_unavailable_weather_has_data_available_false(self):
        ws = WeatherSummary(
            conditions="Weather data unavailable",
            data_available=False,
        )
        assert ws.data_available is False


class TestAttractionCoercion:

    def test_string_cost_coerced(self):
        attr = Attraction(
            name="Temple",
            description="Historic temple",
            approximate_cost_per_person="10",
        )
        assert attr.approximate_cost_per_person == 10.0

    def test_free_attraction_cost_zero(self):
        attr = Attraction(
            name="Park",
            description="Free public park",
            approximate_cost_per_person=0,
        )
        assert attr.approximate_cost_per_person == 0.0
