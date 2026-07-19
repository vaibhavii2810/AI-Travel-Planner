"""
Domain models — the canonical data shapes used throughout agents, tools, and the graph.
All LLM-generated objects are defined here with LLM-tolerant validators.
"""
from __future__ import annotations

from datetime import date as dt_date, datetime, timezone
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator


# ── Base config for all domain models ────────────────────────────────────────

class _DomainModel(BaseModel):
    """
    Shared config:
    - extra="ignore": LLM may add unexpected fields — silently drop them (Risk 5 bypass)
    - populate_by_name=True: Accept both alias and field name
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


# ── Travel Request ─────────────────────────────────────────────────────────────

class TravelRequest(_DomainModel):
    destination: str = Field(..., min_length=2, max_length=200)
    start_date: dt_date
    end_date: dt_date
    budget_min: float = Field(..., gt=0)
    budget_max: float = Field(..., gt=0)
    budget_currency: str = Field(default="USD", max_length=3)
    interests: list[str] = Field(..., min_length=1)
    num_travelers: int = Field(..., ge=1, le=50)

    @field_validator("interests", mode="before")
    @classmethod
    def normalize_interests(cls, v: list[str]) -> list[str]:
        if not isinstance(v, list):
            return v
        normalized = []
        seen = set()
        for item in v:
            if isinstance(item, str):
                cleaned = item.strip().lower()
                if cleaned and cleaned not in seen:
                    normalized.append(cleaned)
                    seen.add(cleaned)
            else:
                normalized.append(item)
        return normalized

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: dt_date, info) -> dt_date:
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v

    @field_validator("budget_max")
    @classmethod
    def max_gte_min(cls, v: float, info) -> float:
        if "budget_min" in info.data and v < info.data["budget_min"]:
            raise ValueError("budget_max must be >= budget_min")
        return v

    @property
    def num_days(self) -> int:
        return (self.end_date - self.start_date).days


# ── Research Output ────────────────────────────────────────────────────────────

class Attraction(_DomainModel):
    name: str = Field(..., max_length=300)
    description: str = Field(..., max_length=1000)
    category: str = Field(default="general", max_length=100)
    estimated_visit_duration_hours: Union[float, int, str] = Field(default=2.0)
    approximate_cost_per_person: Union[float, int, str] = Field(default=0.0)

    @field_validator("estimated_visit_duration_hours", "approximate_cost_per_person", mode="before")
    @classmethod
    def coerce_to_float(cls, v) -> float:
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0


class WeatherSummary(_DomainModel):
    avg_temp_celsius: Union[float, int, str] = Field(default=20.0)
    avg_temp_fahrenheit: Union[float, int, str] = Field(default=68.0)
    conditions: str = Field(default="Unknown", max_length=200)
    precipitation_chance_percent: Union[float, int, str] = Field(default=0.0)
    humidity_percent: Union[float, int, str] = Field(default=50.0)
    warnings: list[str] = Field(default_factory=list)
    data_available: bool = True

    @field_validator(
        "avg_temp_celsius", "avg_temp_fahrenheit",
        "precipitation_chance_percent", "humidity_percent",
        mode="before",
    )
    @classmethod
    def coerce_numeric(cls, v) -> float:
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0


class ResearchOutput(_DomainModel):
    attractions: list[Attraction] = Field(default_factory=list)
    local_tips: list[str] = Field(default_factory=list)
    safety_considerations: list[str] = Field(default_factory=list)
    weather_summary: WeatherSummary = Field(default_factory=WeatherSummary)
    seasonal_notes: str = Field(default="", max_length=2000)
    general_destination_info: str = Field(default="", max_length=3000)
    research_sources: list[str] = Field(default_factory=list)
    researched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Itinerary / Planner Output ─────────────────────────────────────────────────

class Activity(_DomainModel):
    name: str = Field(..., max_length=300)
    description: str = Field(default="", max_length=1000)
    location: str = Field(default="", max_length=300)
    duration_minutes: Union[float, int, str] = Field(default=60)
    estimated_cost_per_person: Union[float, int, str] = Field(default=0.0)
    booking_required: bool = False
    tips: str = Field(default="", max_length=500)

    @field_validator("duration_minutes", "estimated_cost_per_person", mode="before")
    @classmethod
    def coerce_numeric(cls, v) -> float:
        try:
            val = float(v)
        except (TypeError, ValueError):
            return 0.0
        if val < 0:
            raise ValueError("Cost and duration cannot be negative")
        return val

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cost_per_hour(self) -> float:
        """
        Derived, never stored — always recomputed from the current cost/duration.
        Any Modify that changes either field (replace, add, swap) automatically
        yields a correct cost_per_hour with no separate recalculation step.
        """
        duration_hours = self.duration_minutes / 60
        if duration_hours <= 0:
            return 0.0
        return round(self.estimated_cost_per_person / duration_hours, 2)


class DailyPlan(_DomainModel):
    day_number: Union[int, str] = Field(...)
    date: Union[dt_date, str] = Field(...)
    theme: str = Field(default="", max_length=200)
    morning: list[Activity] = Field(default_factory=list)
    afternoon: list[Activity] = Field(default_factory=list)
    evening: list[Activity] = Field(default_factory=list)
    accommodation: str = Field(default="", max_length=300)
    estimated_daily_cost_per_person: Union[float, int, str] = Field(default=0.0)
    # Prompt 5: "practical notes" — alias for backward compat with travel_notes
    practical_notes: str = Field(default="", max_length=500, alias="travel_notes")

    @field_validator("day_number", mode="before")
    @classmethod
    def coerce_day(cls, v) -> int:
        try:
            return int(v)
        except (TypeError, ValueError):
            return 1

    @field_validator("estimated_daily_cost_per_person", mode="before")
    @classmethod
    def coerce_cost(cls, v) -> float:
        try:
            val = float(v)
        except (TypeError, ValueError):
            return 0.0
        if val < 0:
            raise ValueError("Daily cost cannot be negative")
        return val


class BudgetAllocation(_DomainModel):
    accommodation_total: float = Field(default=0.0)
    transport_total: float = Field(default=0.0)
    food_total: float = Field(default=0.0)
    activities_total: float = Field(default=0.0)
    contingency_total: float = Field(default=0.0)
    grand_total: float = Field(default=0.0)
    per_person_total: float = Field(default=0.0)
    currency: str = Field(default="USD", max_length=3)
    within_budget: bool = True
    notes: str = Field(default="", max_length=500)

    @field_validator(
        "accommodation_total", "transport_total", "food_total",
        "activities_total", "contingency_total", "grand_total", "per_person_total",
        mode="before",
    )
    @classmethod
    def coerce_float(cls, v) -> float:
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0


class DraftItinerary(_DomainModel):
    version: int = Field(default=1)
    daily_plans: list[DailyPlan] = Field(default_factory=list)
    budget_allocation: BudgetAllocation = Field(default_factory=BudgetAllocation)
    overall_tips: list[str] = Field(default_factory=list)
    packing_suggestions: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Review ─────────────────────────────────────────────────────────────────────

class ReviewAction(str, Enum):
    """
    Human-in-the-Loop review actions.
    Inherits from str so values can be compared directly to strings:
        ReviewAction.APPROVE == "approve"  →  True
    """
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"


# ── Itinerary (used by itinerary_agent.py) ─────────────────────────────────────
# Note: DraftItinerary (above) is used by the active graph pipeline (planner_agent.py).
# Itinerary is the alternative schema used by the friend's itinerary_agent.py branch.
# Both schemas are retained for compatibility.

class Itinerary(_DomainModel):
    destination: str = Field(..., description="Destination of the trip")
    dates: str = Field(..., description="Dates of the travel")
    travelers: int = Field(default=1, ge=1, description="Number of travelers")
    budget_summary: BudgetAllocation = Field(..., description="Summary of the allocated budget")
    day_by_day_plans: list[DailyPlan] = Field(default_factory=list, description="Day-by-day travel plan")
    activities: list[Activity] = Field(default_factory=list, description="List of all scheduled activities")
    estimated_costs: float = Field(default=0.0, description="Estimated total cost")
    notes: list[str] = Field(default_factory=list, description="Notes and general tips")
    total_estimated_cost: float = Field(default=0.0, description="Total estimated cost of the trip")
    assumptions: list[str] = Field(default_factory=list, description="Assumptions made by the planner")
    budget_comparison: str = Field(default="", description="Comparison of estimated cost vs provided budget")

    @field_validator("total_estimated_cost", "estimated_costs", mode="before")
    @classmethod
    def coerce_total_cost(cls, v) -> float:
        try:
            val = float(v)
        except (TypeError, ValueError):
            return 0.0
        if val < 0:
            raise ValueError("Total cost cannot be negative")
        return val

    @field_validator("day_by_day_plans")
    @classmethod
    def validate_day_plans(cls, plans: list[DailyPlan], info) -> list[DailyPlan]:
        if not info.context or "travel_request" not in info.context:
            return plans

        req: TravelRequest = info.context["travel_request"]
        start = req.start_date
        end = req.end_date
        expected_days = (end - start).days + 1

        dates_seen = set()
        for plan in plans:
            plan_date = plan.date
            if isinstance(plan_date, str):
                try:
                    from datetime import datetime as _dt
                    plan_date = _dt.strptime(plan_date, "%Y-%m-%d").date()
                except ValueError:
                    pass

            if isinstance(plan_date, dt_date):
                if plan_date in dates_seen:
                    raise ValueError(f"Duplicate date found: {plan_date}")
                if plan_date < start or plan_date > end:
                    raise ValueError(
                        f"Invalid itinerary date {plan_date} falls outside requested range {start} to {end}"
                    )
                dates_seen.add(plan_date)

        if len(dates_seen) < expected_days:
            raise ValueError(f"Missing days: expected {expected_days} days, got {len(dates_seen)}")

        return plans

    @model_validator(mode="wrap")
    @classmethod
    def check_budget_explanation(cls, values, handler, info):
        """
        Enforce that substantially overbudget itineraries include an explanation.
        """
        result = handler(values)

        if not info.context or "travel_request" not in info.context:
            return result

        req: TravelRequest = info.context["travel_request"]

        if result.total_estimated_cost > (req.budget_max * 1.2):
            all_text = " ".join(
                result.notes + result.assumptions + [result.budget_comparison]
            ).lower()
            if not any(kw in all_text for kw in ("budget", "cost", "exceed", "expensive")):
                raise ValueError(
                    "Estimated total substantially exceeds budget max without explanation "
                    "in notes or assumptions"
                )
        return result

