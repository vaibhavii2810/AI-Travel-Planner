"""
Domain models — the canonical data shapes used throughout agents, tools, and the graph.
All LLM-generated objects are defined here with LLM-tolerant validators.
"""
from __future__ import annotations

from datetime import date as dt_date, datetime, timezone
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
            return float(v)
        except (TypeError, ValueError):
            return 0.0


class DailyPlan(_DomainModel):
    day_number: Union[int, str] = Field(...)
    date: Union[dt_date, str] = Field(...)
    theme: str = Field(default="", max_length=200)
    morning: list[Activity] = Field(default_factory=list)
    afternoon: list[Activity] = Field(default_factory=list)
    evening: list[Activity] = Field(default_factory=list)
    accommodation: str = Field(default="", max_length=300)
    estimated_daily_cost_per_person: Union[float, int, str] = Field(default=0.0)
    travel_notes: str = Field(default="", max_length=500)

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
            return float(v)
        except (TypeError, ValueError):
            return 0.0


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
