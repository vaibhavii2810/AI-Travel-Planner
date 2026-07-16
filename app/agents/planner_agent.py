"""
Itinerary Planner Agent — single-pass with tool assistance and structured output.
Uses structured output with retry wrapper (Risk 5 bypass).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import get_settings
from app.core.exceptions import LLMOutputParseError
from app.models.domain import DraftItinerary, ResearchOutput, TravelRequest
from app.prompts.planner_agent import PLANNER_AGENT_SYSTEM_PROMPT, build_planner_prompt
from app.tools.budget_allocator import budget_allocator_tool
from app.tools.schedule_optimizer import schedule_optimizer_tool

logger = logging.getLogger("app.agents.planner_agent")

_PLANNER_TOOLS = [budget_allocator_tool, schedule_optimizer_tool]


def _build_planner_llm() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        timeout=settings.LLM_TIMEOUT_SECONDS,
        api_key=settings.OPENAI_API_KEY.get_secret_value(),
    )


def _research_to_summary(research: ResearchOutput) -> str:
    """Convert ResearchOutput to a concise string for the planner prompt."""
    lines = [
        f"## Weather",
        f"{research.weather_summary.conditions}, avg {research.weather_summary.avg_temp_celsius}°C",
        f"Precipitation: {research.weather_summary.precipitation_chance_percent}%",
        "",
        f"## Top Attractions ({len(research.attractions)} found)",
    ]
    for attr in research.attractions[:12]:
        lines.append(f"- {attr.name}: {attr.description[:150]} (~{attr.estimated_visit_duration_hours}h, ~${attr.approximate_cost_per_person}/person)")

    lines += ["", "## Local Tips"]
    for tip in research.local_tips[:8]:
        lines.append(f"- {tip}")

    lines += ["", "## Safety Considerations"]
    for safety in research.safety_considerations[:5]:
        lines.append(f"- {safety}")

    lines += ["", f"## Seasonal Notes", research.seasonal_notes[:500]]
    lines += ["", f"## General Info", research.general_destination_info[:500]]

    return "\n".join(lines)


async def invoke_planner_agent(
    travel_request: TravelRequest,
    research_output: ResearchOutput,
    revision_count: int = 0,
    rejection_feedback: str | None = None,
    modification_request: dict | None = None,
    max_retries: int = 2,
) -> DraftItinerary:
    """
    Runs the Itinerary Planner Agent.

    Risk 5 bypass: include_raw=True + retry with error correction prompt.
    """
    llm = _build_planner_llm()
    llm_with_tools = llm.bind_tools(_PLANNER_TOOLS)
    structured_llm = llm.with_structured_output(DraftItinerary, include_raw=True)

    research_summary = _research_to_summary(research_output)

    human_prompt = build_planner_prompt(
        destination=travel_request.destination,
        start_date=str(travel_request.start_date),
        end_date=str(travel_request.end_date),
        num_days=travel_request.num_days,
        num_travelers=travel_request.num_travelers,
        budget_min=travel_request.budget_min,
        budget_max=travel_request.budget_max,
        budget_currency=travel_request.budget_currency,
        interests=travel_request.interests,
        research_summary=research_summary,
        revision_count=revision_count,
        rejection_feedback=rejection_feedback,
        modification_request=modification_request,
    )

    messages = [
        SystemMessage(content=PLANNER_AGENT_SYSTEM_PROMPT),
        HumanMessage(content=human_prompt),
    ]

    # ── Tool-assisted planning phase ─────────────────────────────────────────
    from langchain_core.messages import ToolMessage

    tool_map = {t.name: t for t in _PLANNER_TOOLS}

    for step in range(6):
        ai_msg = await llm_with_tools.ainvoke(messages)
        messages.append(ai_msg)

        if not hasattr(ai_msg, "tool_calls") or not ai_msg.tool_calls:
            break

        for tc in ai_msg.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id = tc["id"]

            logger.info(f"Planner Agent calling tool: {tool_name}")

            if tool_name in tool_map:
                try:
                    result = tool_map[tool_name].invoke(tool_args)
                except Exception as exc:
                    result = f"Tool error: {exc}"
                    logger.warning(f"Planner tool {tool_name} error: {exc}")
            else:
                result = f"Unknown tool: {tool_name}"

            messages.append(ToolMessage(content=str(result), tool_call_id=tool_id))

    # ── Structured extraction ─────────────────────────────────────────────────
    messages.append(
        HumanMessage(
            content=(
                "Now produce the complete DraftItinerary JSON based on your planning above. "
                f"This is version {revision_count + 1}. "
                "Ensure all daily_plans are included, budget_allocation is accurate, "
                "and the JSON is valid."
            )
        )
    )

    last_error: str | None = None
    for attempt in range(max_retries + 1):
        if attempt > 0 and last_error:
            messages.append(
                HumanMessage(
                    content=f"JSON parse failed: {last_error}. "
                    "Fix the structure. Ensure all required fields are present and types are correct."
                )
            )

        result = await structured_llm.ainvoke(messages)
        parsed = result.get("parsed")
        parsing_error = result.get("parsing_error")

        if parsed is not None:
            # Stamp version number
            parsed.version = revision_count + 1
            logger.info(
                f"Planner structured output succeeded | "
                f"attempt={attempt + 1} | version={parsed.version} | days={len(parsed.daily_plans)}"
            )
            return parsed

        last_error = str(parsing_error) if parsing_error else "Unknown parse error"
        logger.warning(f"Planner structured output parse failed (attempt {attempt + 1}): {last_error}")

    logger.error(f"Planner agent failed structured output after {max_retries + 1} attempts")
    raise LLMOutputParseError("DraftItinerary", max_retries + 1)
