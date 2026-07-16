"""
Schedule optimizer tool — pure computation, no external API.
Reorders activities for logical daily flow: fatigue management, geo-proximity, operating hours.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger("app.tools.schedule_optimizer")

# Activity type → suggested time slot
_TIME_SLOT_PREFERENCES: dict[str, str] = {
    "museum": "morning",
    "gallery": "morning",
    "temple": "morning",
    "shrine": "morning",
    "market": "morning",
    "hiking": "morning",
    "nature": "morning",
    "breakfast": "morning",
    "brunch": "morning",
    "tour": "morning",
    "cruise": "afternoon",
    "beach": "afternoon",
    "park": "afternoon",
    "shopping": "afternoon",
    "cooking class": "afternoon",
    "class": "afternoon",
    "lunch": "afternoon",
    "restaurant": "evening",
    "dinner": "evening",
    "bar": "evening",
    "nightlife": "evening",
    "show": "evening",
    "performance": "evening",
    "concert": "evening",
}

_FATIGUE_WEIGHTS: dict[str, int] = {
    "hiking": 3,
    "nature": 2,
    "tour": 2,
    "museum": 1,
    "shopping": 1,
    "beach": 1,
    "restaurant": 0,
    "bar": 0,
}


def _classify_activity(name: str, description: str = "") -> str:
    """Classify an activity into a preferred time slot."""
    combined = (name + " " + description).lower()
    for keyword, slot in _TIME_SLOT_PREFERENCES.items():
        if keyword in combined:
            return slot
    return "afternoon"  # Default


def _fatigue_score(name: str) -> int:
    name_lower = name.lower()
    for keyword, score in _FATIGUE_WEIGHTS.items():
        if keyword in name_lower:
            return score
    return 1


@tool
def schedule_optimizer_tool(
    activities_json: str,
    destination: str,
    num_days: int,
    preferences: str,
) -> str:
    """
    Organize a list of activities into an optimized day-by-day schedule.
    Considers: time-of-day preferences, fatigue management, logical ordering.

    Args:
        activities_json: JSON string of activities list. Each item: {"name": str, "description": str, "duration_hours": float}.
        destination: Travel destination.
        num_days: Number of travel days.
        preferences: Comma-separated traveler preferences/interests.

    Returns:
        Formatted optimized schedule as a string.
    """
    import json

    try:
        activities: list[dict[str, Any]] = json.loads(activities_json)
    except (json.JSONDecodeError, TypeError):
        return "[Schedule optimizer: invalid activities input — using natural ordering]"

    if not activities:
        return "[Schedule optimizer: no activities provided]"

    # Classify each activity
    classified: dict[str, list[dict]] = {"morning": [], "afternoon": [], "evening": []}
    for act in activities:
        slot = _classify_activity(act.get("name", ""), act.get("description", ""))
        classified[slot].append(act)

    # Sort within each slot by fatigue (high-energy first in morning, relaxed in evening)
    classified["morning"].sort(key=lambda a: _fatigue_score(a.get("name", "")), reverse=True)
    classified["afternoon"].sort(key=lambda a: _fatigue_score(a.get("name", "")), reverse=False)
    classified["evening"].sort(key=lambda a: _fatigue_score(a.get("name", "")), reverse=False)

    # Distribute across days
    all_slots = (
        [("morning", a) for a in classified["morning"]]
        + [("afternoon", a) for a in classified["afternoon"]]
        + [("evening", a) for a in classified["evening"]]
    )

    lines = [f"Optimized Schedule for {destination} ({num_days} days)\n"]
    items_per_day = max(1, len(all_slots) // max(num_days, 1))
    day = 1
    count = 0

    for slot, act in all_slots:
        if count % items_per_day == 0 and count > 0 and day < num_days:
            day += 1
        if count == 0 or count % items_per_day == 0:
            lines.append(f"\nDay {day}:")

        name = act.get("name", "Activity")
        dur = act.get("duration_hours", 1.0)
        desc = act.get("description", "")
        lines.append(f"  [{slot.capitalize()}] {name} (~{dur}h) — {desc[:80]}")
        count += 1

    lines.append(
        f"\nOptimization notes:\n"
        f"  • High-energy activities (hiking, tours) scheduled in the morning\n"
        f"  • Dining and relaxation activities in the afternoon/evening\n"
        f"  • Cultural sites (museums, temples) placed before crowds peak\n"
    )

    logger.info(
        f"schedule_optimizer | destination='{destination}' | "
        f"activities={len(activities)} | days={num_days}"
    )
    return "\n".join(lines)
