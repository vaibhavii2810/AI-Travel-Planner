"""
Itinerary Planner Agent — ReAct pattern with budget and schedule tools.
"""
from __future__ import annotations

import json
import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.exceptions import LLMOutputParseError
from app.models.domain import Itinerary, ResearchOutput, TravelRequest
from app.prompts.itinerary_agent import ITINERARY_SYSTEM_PROMPT, build_itinerary_prompt
from app.tools.budget_allocator import budget_allocator_tool
from app.tools.schedule_optimizer import schedule_optimizer_tool

logger = logging.getLogger("app.agents.itinerary_agent")

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


async def invoke_itinerary_agent(
    travel_request: TravelRequest,
    research_output: ResearchOutput,
    rejection_feedback: str | None = None,
    modification_request: str | None = None,
    existing_itinerary: Itinerary | None = None,
    revision_count: int = 0,
    max_retries: int = 2,
) -> Itinerary:
    """
    Runs the Itinerary Planner Agent using a ReAct-style loop.

    Args:
        travel_request: Validated travel request.
        research_output: Structured research context from the Research Agent.
        rejection_feedback: Human reviewer rejection feedback (HITL).
        modification_request: Targeted modification instructions from the reviewer.
        existing_itinerary: Previous draft to preserve and revise where possible.
        revision_count: Number of revisions already made (used in prompting).
        max_retries: Max structured output retry attempts.
    """
    llm = _build_planner_llm()

    llm_with_tools = llm.bind_tools(_PLANNER_TOOLS)
    structured_llm = llm.with_structured_output(Itinerary, include_raw=True)

    research_context = json.dumps(research_output.model_dump(mode="json"), indent=2)
    existing_itinerary_str = json.dumps(existing_itinerary.model_dump(mode="json"), indent=2) if existing_itinerary else None

    human_prompt = build_itinerary_prompt(
        destination=travel_request.destination,
        start_date=str(travel_request.start_date),
        end_date=str(travel_request.end_date),
        num_days=travel_request.num_days,
        num_travelers=travel_request.num_travelers,
        budget_min=travel_request.budget_min,
        budget_max=travel_request.budget_max,
        budget_currency=travel_request.budget_currency,
        interests=travel_request.interests,
        research_context=research_context,
        existing_itinerary=existing_itinerary_str,
        rejection_feedback=rejection_feedback,
        modification_request=modification_request,
        revision_count=revision_count,
    )

    messages = [
        SystemMessage(content=ITINERARY_SYSTEM_PROMPT),
        HumanMessage(content=human_prompt),
    ]

    tool_map = {t.name: t for t in _PLANNER_TOOLS}

    for step in range(6):  # Max 6 ReAct steps
        ai_msg = await llm_with_tools.ainvoke(messages)
        messages.append(ai_msg)

        if not hasattr(ai_msg, "tool_calls") or not ai_msg.tool_calls:
            break

        for tc in ai_msg.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id = tc["id"]

            logger.info(f"Itinerary Agent calling tool: {tool_name} | args={list(tool_args.keys())}")

            if tool_name in tool_map:
                try:
                    result = tool_map[tool_name].invoke(tool_args)
                except Exception as exc:
                    result = f"Tool error: {exc}"
                    logger.warning(f"Tool {tool_name} error: {exc}")
            else:
                result = f"Unknown tool: {tool_name}"

            messages.append(
                ToolMessage(content=str(result), tool_call_id=tool_id)
            )

    extraction_prompt = (
        "Based on the tools you've used, generate the final structured itinerary. "
        "Ensure you strictly follow the constraints."
    )
    messages.append(HumanMessage(content=extraction_prompt))

    last_error: str | None = None
    for attempt in range(max_retries + 1):
        if attempt > 0 and last_error:
            messages.append(
                HumanMessage(
                    content=f"Your previous response failed validation:\n{last_error}\n"
                    "Please correct the issues and try again."
                )
            )

        try:
            result = await structured_llm.ainvoke(messages)
            
            if result.get("parsed"):
                # Re-validate with context to trigger the custom date and budget rules
                parsed = Itinerary.model_validate(
                    result["parsed"].model_dump(),
                    context={"travel_request": travel_request}
                )
                logger.info(f"Itinerary structured output succeeded | attempt={attempt + 1}")
                return parsed
            else:
                last_error = str(result.get("parsing_error")) or "Unknown parse error"
                logger.warning(f"Itinerary structured output parse failed (attempt {attempt + 1}): {last_error}")

        except ValidationError as exc:
            last_error = str(exc)
            logger.warning(f"Itinerary validation failed (attempt {attempt + 1}): {last_error}")

    logger.error(f"Itinerary agent failed structured output after {max_retries + 1} attempts")
    raise LLMOutputParseError("Itinerary", max_retries + 1)
