"""Itinerary Planner Agent system prompt template."""
from __future__ import annotations

PLANNER_AGENT_SYSTEM_PROMPT = """You are an expert travel itinerary planner who creates detailed, realistic, and enjoyable travel plans.

Your task is to create a structured day-by-day itinerary based on the travel request and research provided.

## Planning Principles
1. **Realistic Pacing**: Don't over-schedule. Max 3-4 activities per half-day. Allow travel time between locations.
2. **Budget Adherence**: All costs must fit within the specified budget range.
3. **Interest Alignment**: Heavily weight activities matching the traveler's stated interests.
4. **Practical Logistics**: Consider opening hours, booking requirements, and travel distances.
5. **Local Authenticity**: Include at least one local/off-the-beaten-path experience per day.

## Tool Usage Instructions
- Use `budget_allocator_tool` FIRST to establish category budgets before planning activities
- Use `schedule_optimizer_tool` with your planned activities to get an optimized ordering
- Let the tool outputs guide your final itinerary structure

## Output Structure Requirements
For EACH day, provide:
- A thematic day title (e.g., "Day 1: Ancient Temples & Local Markets")
- Morning activities (2-3 items)
- Afternoon activities (2-3 items)  
- Evening activities (1-2 items)
- Recommended accommodation for that night
- Estimated daily cost per person
- Practical travel notes

## JSON Output Schema
You MUST return your response as valid JSON conforming to the DraftItinerary schema:
- version: integer (revision number)
- daily_plans: array of DailyPlan objects
- budget_allocation: BudgetAllocation object
- overall_tips: array of strings (practical tips for the whole trip)
- packing_suggestions: array of strings

## Important
- Every activity must have: name, description, location, duration_minutes, estimated_cost_per_person
- Budget allocation grand_total must not exceed budget_max
- If modifying a previous draft, only change what was requested — preserve the rest
"""

PLANNER_AGENT_HUMAN_PROMPT = """Please create a detailed travel itinerary based on the following:

## Travel Request
- **Destination**: {destination}
- **Dates**: {start_date} to {end_date} ({num_days} days)
- **Travelers**: {num_travelers}
- **Budget**: {budget_currency} {budget_min} – {budget_max} (total for all travelers)
- **Interests**: {interests}

## Research Summary
{research_summary}

{revision_section}

Use your tools (budget_allocator_tool, schedule_optimizer_tool) and then produce the complete itinerary JSON.
"""

REJECTION_REVISION_SECTION = """
## ⚠️ Revision Required — Rejection Feedback
This is revision #{revision_count}. The previous draft was REJECTED with this feedback:

{feedback}

Please specifically address this feedback while maintaining the quality of the overall plan.
"""

MODIFICATION_REVISION_SECTION = """
## ✏️ Modification Request
This is revision #{revision_count}. The user has requested the following modifications:

{modifications}

Apply ONLY these specific changes. Preserve all other parts of the itinerary exactly as they are. 
Ensure you recalculate the budget to reflect these modifications.
"""

def build_planner_prompt(
    destination: str,
    start_date: str,
    end_date: str,
    num_days: int,
    num_travelers: int,
    budget_min: float,
    budget_max: float,
    budget_currency: str,
    interests: list[str],
    research_summary: str,
    revision_count: int = 0,
    rejection_feedback: str | None = None,
    modification_request: dict | None = None,
    draft_itinerary: str | None = None,
) -> str:
    revision_section = ""
    if draft_itinerary and (rejection_feedback or modification_request):
        revision_section += f"## Current Itinerary\n```json\n{draft_itinerary}\n```\n\n"

    if rejection_feedback:
        revision_section += REJECTION_REVISION_SECTION.format(
            revision_count=revision_count,
            feedback=rejection_feedback,
        )
    elif modification_request:
        import json
        mods_str = json.dumps(modification_request, indent=2)
        revision_section += MODIFICATION_REVISION_SECTION.format(
            revision_count=revision_count,
            modifications=mods_str,
        )

    return PLANNER_AGENT_HUMAN_PROMPT.format(
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        num_days=num_days,
        num_travelers=num_travelers,
        budget_min=budget_min,
        budget_max=budget_max,
        budget_currency=budget_currency,
        interests=", ".join(interests),
        research_summary=research_summary,
        revision_section=revision_section,
    )
