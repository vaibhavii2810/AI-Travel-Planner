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

    def test_interests_normalized(self):
        req = TravelRequest(
            destination="Tokyo, Japan",
            start_date=date(2025, 5, 1),
            end_date=date(2025, 5, 8),
            budget_min=1500.0,
            budget_max=3000.0,
            interests=["  Food ", "FOOD", "culture"],
            num_travelers=2,
        )
        assert req.interests == ["food", "culture"]

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

    def test_cost_per_hour_computed_from_cost_and_duration(self):
        act = Activity(name="Museum Tour", estimated_cost_per_person=45, duration_minutes=90)
        assert act.cost_per_hour == 30.0
        assert act.model_dump()["cost_per_hour"] == 30.0

    def test_cost_per_hour_zero_when_duration_zero(self):
        act = Activity(name="Free Walk", estimated_cost_per_person=0, duration_minutes=0)
        assert act.cost_per_hour == 0.0

    def test_cost_per_hour_recomputes_when_fields_change(self):
        """The whole point: no separate recalculation step is needed after a Modify."""
        act = Activity(name="Spa Day", estimated_cost_per_person=100, duration_minutes=60)
        assert act.cost_per_hour == 100.0
        act.estimated_cost_per_person = 50
        act.duration_minutes = 30
        assert act.cost_per_hour == 100.0
        act.duration_minutes = 120
        assert act.cost_per_hour == 25.0


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


class TestItineraryValidation:

    @pytest.fixture
    def mock_travel_req(self):
        return TravelRequest(
            destination="Kyoto",
            start_date=date(2025, 5, 1),
            end_date=date(2025, 5, 3),
            budget_min=1000,
            budget_max=2000,
            interests=["temples"],
            num_travelers=1
        )

    def test_negative_costs_raise_error(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            Activity(name="A", duration_minutes=60, estimated_cost_per_person=-10)

        with pytest.raises(ValueError, match="cannot be negative"):
            DailyPlan(day_number=1, date=date(2025, 5, 1), estimated_daily_cost_per_person=-50)

    def test_missing_days_raises_error(self, mock_travel_req):
        from app.models.domain import Itinerary, BudgetAllocation
        plans = [
            DailyPlan(day_number=1, date=date(2025, 5, 1)),
            # missing day 2 and 3
        ]
        
        with pytest.raises(ValueError, match="Missing days: expected 3 days, got 1"):
            Itinerary.model_validate({
                "destination": "Kyoto",
                "dates": "May 1-3",
                "budget_summary": BudgetAllocation(),
                "day_by_day_plans": plans
            }, context={"travel_request": mock_travel_req})

    def test_duplicate_dates_raises_error(self, mock_travel_req):
        from app.models.domain import Itinerary, BudgetAllocation
        plans = [
            DailyPlan(day_number=1, date=date(2025, 5, 1)),
            DailyPlan(day_number=2, date=date(2025, 5, 1)), # duplicate
            DailyPlan(day_number=3, date=date(2025, 5, 3)),
        ]
        
        with pytest.raises(ValueError, match="Duplicate date"):
            Itinerary.model_validate({
                "destination": "Kyoto",
                "dates": "May 1-3",
                "budget_summary": BudgetAllocation(),
                "day_by_day_plans": plans
            }, context={"travel_request": mock_travel_req})

    def test_invalid_dates_raises_error(self, mock_travel_req):
        from app.models.domain import Itinerary, BudgetAllocation
        plans = [
            DailyPlan(day_number=1, date=date(2025, 5, 1)),
            DailyPlan(day_number=2, date=date(2025, 5, 2)),
            DailyPlan(day_number=3, date=date(2025, 5, 4)), # outside range
        ]
        
        with pytest.raises(ValueError, match="falls outside requested range"):
            Itinerary.model_validate({
                "destination": "Kyoto",
                "dates": "May 1-3",
                "budget_summary": BudgetAllocation(),
                "day_by_day_plans": plans
            }, context={"travel_request": mock_travel_req})

    def test_budget_overrun_without_explanation_raises_error(self, mock_travel_req):
        from app.models.domain import Itinerary, BudgetAllocation
        plans = [
            DailyPlan(day_number=1, date=date(2025, 5, 1)),
            DailyPlan(day_number=2, date=date(2025, 5, 2)),
            DailyPlan(day_number=3, date=date(2025, 5, 3)),
        ]
        
        with pytest.raises(ValueError, match="Estimated total substantially exceeds budget max without explanation"):
            Itinerary.model_validate({
                "destination": "Kyoto",
                "dates": "May 1-3",
                "budget_summary": BudgetAllocation(),
                "day_by_day_plans": plans,
                "total_estimated_cost": 3000.0, # max is 2000, 3000 > 2400 (1.2x)
                "notes": ["Great trip!"],
                "assumptions": ["Standard rates"]
            }, context={"travel_request": mock_travel_req})
            
    def test_budget_overrun_with_explanation_passes(self, mock_travel_req):
        from app.models.domain import Itinerary, BudgetAllocation
        plans = [
            DailyPlan(day_number=1, date=date(2025, 5, 1)),
            DailyPlan(day_number=2, date=date(2025, 5, 2)),
            DailyPlan(day_number=3, date=date(2025, 5, 3)),
        ]
        
        # Should not raise
        Itinerary.model_validate({
            "destination": "Kyoto",
            "dates": "May 1-3",
            "budget_summary": BudgetAllocation(),
            "day_by_day_plans": plans,
            "total_estimated_cost": 3000.0,
            "notes": ["Great trip!"],
            "assumptions": ["Costs exceed budget because of requested luxury ryokan."]
        }, context={"travel_request": mock_travel_req})
