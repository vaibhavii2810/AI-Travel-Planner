"""
Budget allocator tool — pure computation, no external API.
Distributes total budget across trip categories using destination cost-of-living heuristics.
"""
from __future__ import annotations

import logging

from langchain_core.tools import tool

logger = logging.getLogger("app.tools.budget_allocator")

# Cost-of-living tiers: multiplier relative to global average
_DESTINATION_COST_TIERS: dict[str, float] = {
    # High-cost cities
    "tokyo": 1.4, "zurich": 1.6, "london": 1.5, "new york": 1.5, "singapore": 1.3,
    "paris": 1.4, "sydney": 1.3, "dubai": 1.3, "oslo": 1.6, "copenhagen": 1.5,
    # Mid-cost cities
    "barcelona": 1.0, "rome": 1.0, "amsterdam": 1.1, "berlin": 0.9, "prague": 0.8,
    "bangkok": 0.6, "istanbul": 0.7, "lisbon": 0.85, "kyoto": 1.2, "melbourne": 1.2,
    # Low-cost destinations
    "hanoi": 0.5, "bali": 0.55, "delhi": 0.45, "cairo": 0.5, "marrakech": 0.55,
    "ho chi minh": 0.5, "kathmandu": 0.4, "colombo": 0.5,
}

# Category weights: fraction of total budget
_DEFAULT_WEIGHTS = {
    "accommodation": 0.35,
    "transport": 0.20,
    "food": 0.25,
    "activities": 0.15,
    "contingency": 0.05,
}

# Interest-based activity weight boosts
_INTEREST_BOOSTS: dict[str, str] = {
    "food": "food",
    "culinary": "food",
    "dining": "food",
    "restaurants": "food",
    "adventure": "activities",
    "hiking": "activities",
    "sports": "activities",
    "nightlife": "activities",
    "museums": "activities",
    "culture": "activities",
    "art": "activities",
}


def _get_cost_multiplier(destination: str) -> float:
    dest_lower = destination.lower()
    for key, multiplier in _DESTINATION_COST_TIERS.items():
        if key in dest_lower:
            return multiplier
    return 1.0  # Default: global average


@tool
def budget_allocator_tool(
    budget_min: float,
    budget_max: float,
    num_travelers: int,
    num_days: int,
    destination: str,
    interests: str,
) -> str:
    """
    Allocate travel budget across categories: accommodation, transport, food, activities, contingency.

    Args:
        budget_min: Minimum total budget (all travelers combined).
        budget_max: Maximum total budget (all travelers combined).
        num_travelers: Number of travelers.
        num_days: Number of travel days.
        destination: Travel destination (used for cost-of-living adjustment).
        interests: Comma-separated list of traveler interests.

    Returns:
        Formatted budget allocation breakdown string.
    """
    # Use midpoint budget for planning
    total_budget = (budget_min + budget_max) / 2
    cost_multiplier = _get_cost_multiplier(destination)

    # Adjust weights based on interests
    weights = _DEFAULT_WEIGHTS.copy()
    interest_list = [i.strip().lower() for i in interests.split(",")]
    for interest in interest_list:
        boost_category = _INTEREST_BOOSTS.get(interest)
        if boost_category:
            weights[boost_category] = min(weights[boost_category] + 0.05, 0.40)
            # Normalize to keep sum = 1
            total_w = sum(weights.values())
            weights = {k: v / total_w for k, v in weights.items()}

    # Calculate allocations
    accommodation = round(total_budget * weights["accommodation"], 2)
    transport = round(total_budget * weights["transport"], 2)
    food = round(total_budget * weights["food"], 2)
    activities = round(total_budget * weights["activities"], 2)
    contingency = round(total_budget * weights["contingency"], 2)
    grand_total = accommodation + transport + food + activities + contingency
    per_person = round(grand_total / max(num_travelers, 1), 2)
    daily_per_person = round(per_person / max(num_days, 1), 2)
    within_budget = grand_total <= budget_max

    logger.info(
        f"budget_allocator | destination='{destination}' | "
        f"total={grand_total} | per_person={per_person} | within_budget={within_budget}"
    )

    lines = [
        f"Budget Allocation for {destination}",
        f"Total travelers: {num_travelers} | Days: {num_days}",
        f"Cost-of-living multiplier: {cost_multiplier}x",
        f"",
        f"ALLOCATION BREAKDOWN:",
        f"  Accommodation:  ${accommodation:,.2f}",
        f"  Transport:      ${transport:,.2f}",
        f"  Food & Dining:  ${food:,.2f}",
        f"  Activities:     ${activities:,.2f}",
        f"  Contingency:    ${contingency:,.2f}",
        f"  ─────────────────────────────",
        f"  Grand Total:    ${grand_total:,.2f}",
        f"  Per Person:     ${per_person:,.2f}",
        f"  Per Person/Day: ${daily_per_person:,.2f}",
        f"",
        f"Budget range: ${budget_min:,.2f} – ${budget_max:,.2f}",
        f"Within budget: {'YES ✓' if within_budget else 'NO — consider adjustments'}",
    ]
    return "\n".join(lines)
