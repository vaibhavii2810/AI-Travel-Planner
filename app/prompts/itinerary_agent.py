"""
Itinerary Planner Agent prompts.
"""

ITINERARY_SYSTEM_PROMPT = """You are a master travel planner. Your task is to generate or modify a realistic, enjoyable, and well-structured day-by-day travel itinerary.

## Tools
You MUST use the following tools to assist you:
- `budget_allocator_tool`: Generates a deterministic budget breakdown. Pass it the total budget and traveler count. You MUST use this tool to build your budget summary.
- `schedule_optimizer_tool`: Helps sequence and optimize the daily flow of activities.

## Guidelines
1. **Realistic Pacing:** Avoid scheduling an impossible number of activities in a single day. Allow time for meals, travel between locations, and rest.
2. **Contextual Awareness:** Use the provided research context (attractions, weather, local tips, safety). Respect the user's specific interests.
3. **Budget Compliance:** Keep the `total_estimated_cost` as close to the requested budget as possible. Ensure every activity cost is realistic. If the estimated total substantially exceeds the budget maximum, you MUST explain why in the `assumptions` or `notes` fields.
4. **Dates:** Every single date in the requested travel window must be represented EXACTLY once in the day-by-day plans. No missing dates, no duplicate dates, no dates outside the window.
5. **Estimates:** Clearly mark estimated costs as estimates.

## Revisions and Modifications
If you are revising an existing itinerary based on feedback or a targeted modification request:
- PRESERVE unaffected parts of the itinerary where possible. Do not unnecessarily regenerate or alter days or activities that the user did not complain about.
- Directly address the feedback provided.
"""

ITINERARY_HUMAN_PROMPT = """Create or update the travel itinerary based on the following context.

### Travel Request
- **Destination:** {destination}
- **Travel Dates:** {start_date} to {end_date} ({num_days} days)
- **Travelers:** {num_travelers}
- **Budget:** {budget_currency} {budget_min} - {budget_max}
- **Interests:** {interests}

### Research Context
{research_context}

{existing_itinerary_section}
{feedback_section}
{modification_section}
{validation_error_section}

Generate the final itinerary as a strictly typed JSON object matching the Itinerary schema.
"""

def build_itinerary_prompt(
    destination: str,
    start_date: str,
    end_date: str,
    num_days: int,
    num_travelers: int,
    budget_min: float,
    budget_max: float,
    budget_currency: str,
    interests: list[str],
    research_context: str,
    existing_itinerary: str | None = None,
    rejection_feedback: str | None = None,
    modification_request: str | None = None,
    validation_error: str | None = None,
    revision_count: int = 0,
) -> str:
    existing_itinerary_section = ""
    if existing_itinerary:
        existing_itinerary_section = (
            f"### Existing Itinerary (Revision {revision_count})\n"
            f"Here is the current draft of the itinerary:\n{existing_itinerary}\n"
        )

    feedback_section = ""
    if rejection_feedback:
        feedback_section = f"### Rejection Feedback\nThe previous plan was rejected with the following feedback:\n{rejection_feedback}\nPlease revise the itinerary to address this. Remember to preserve unaffected days/activities.\n"

    modification_section = ""
    if modification_request:
        modification_section = f"### Modification Request\nThe user requested the following specific modifications:\n{modification_request}\nPlease apply these targeted changes. Preserve the rest of the itinerary exactly as it is where possible.\n"
        
    validation_error_section = ""
    if validation_error:
        validation_error_section = f"### Validation Error\nYour previous JSON response failed schema validation:\n{validation_error}\nPlease correct the errors and try again.\n"

    return ITINERARY_HUMAN_PROMPT.format(
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        num_days=num_days,
        num_travelers=num_travelers,
        budget_min=budget_min,
        budget_max=budget_max,
        budget_currency=budget_currency,
        interests=", ".join(interests),
        research_context=research_context,
        existing_itinerary_section=existing_itinerary_section,
        feedback_section=feedback_section,
        modification_section=modification_section,
        validation_error_section=validation_error_section,
    )
