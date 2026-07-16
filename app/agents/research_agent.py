"""
Research Agent — ReAct pattern with web search and weather tools.
Uses structured output with retry wrapper (Risk 5 bypass).
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.exceptions import LLMOutputParseError
from app.models.domain import ResearchOutput
from app.prompts.research_agent import RESEARCH_AGENT_SYSTEM_PROMPT, build_research_prompt
from app.tools.web_search import web_search_tool
from app.tools.weather import weather_tool

logger = logging.getLogger("app.agents.research_agent")

_RESEARCH_TOOLS = [web_search_tool, weather_tool]


def _build_research_llm() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        timeout=settings.LLM_TIMEOUT_SECONDS,
        api_key=settings.OPENAI_API_KEY.get_secret_value(),
    )


async def invoke_research_agent(
    destination: str,
    start_date: str,
    end_date: str,
    num_days: int,
    num_travelers: int,
    budget_min: float,
    budget_max: float,
    budget_currency: str,
    interests: list[str],
    rejection_feedback: str | None = None,
    max_retries: int = 2,
) -> ResearchOutput:
    """
    Runs the Research Agent using a ReAct-style loop.
    
    Risk 5 bypass: Uses include_raw=True + retry loop with error-correction prompt.
    Falls back to a minimal ResearchOutput on complete failure rather than crashing.
    """
    settings = get_settings()
    llm = _build_research_llm()

    # Bind tools for ReAct loop
    llm_with_tools = llm.bind_tools(_RESEARCH_TOOLS)

    # Build structured output LLM (separate chain for final extraction)
    structured_llm = llm.with_structured_output(ResearchOutput, include_raw=True)

    human_prompt = build_research_prompt(
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        num_days=num_days,
        num_travelers=num_travelers,
        budget_min=budget_min,
        budget_max=budget_max,
        budget_currency=budget_currency,
        interests=interests,
        rejection_feedback=rejection_feedback,
    )

    messages = [
        SystemMessage(content=RESEARCH_AGENT_SYSTEM_PROMPT),
        HumanMessage(content=human_prompt),
    ]

    # ── ReAct loop: let LLM use tools iteratively ─────────────────────────────
    from langchain_core.messages import AIMessage, ToolMessage
    import json

    tool_map = {t.name: t for t in _RESEARCH_TOOLS}
    collected_research: list[str] = []

    for step in range(8):  # Max 8 ReAct steps
        ai_msg = await llm_with_tools.ainvoke(messages)
        messages.append(ai_msg)

        if not hasattr(ai_msg, "tool_calls") or not ai_msg.tool_calls:
            break  # No more tool calls — agent is done with research

        for tc in ai_msg.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id = tc["id"]

            logger.info(f"Research Agent calling tool: {tool_name} | args={list(tool_args.keys())}")

            if tool_name in tool_map:
                try:
                    result = tool_map[tool_name].invoke(tool_args)
                    collected_research.append(f"[{tool_name}]: {result}")
                except Exception as exc:
                    result = f"Tool error: {exc}"
                    logger.warning(f"Tool {tool_name} error: {exc}")
            else:
                result = f"Unknown tool: {tool_name}"

            messages.append(
                ToolMessage(content=str(result), tool_call_id=tool_id)
            )

    # ── Structured extraction: convert research into ResearchOutput ───────────
    extraction_prompt = (
        "Based on all the research you've conducted above, "
        "synthesize the information into a comprehensive ResearchOutput JSON object. "
        "Include all attractions, local tips, safety considerations, weather data, "
        "seasonal notes, and general destination information you found. "
        "Be specific and thorough."
    )
    messages.append(HumanMessage(content=extraction_prompt))

    last_error: str | None = None
    for attempt in range(max_retries + 1):
        if attempt > 0 and last_error:
            messages.append(
                HumanMessage(
                    content=f"Your previous response could not be parsed: {last_error}. "
                    "Please fix the JSON structure and try again."
                )
            )

        result = await structured_llm.ainvoke(messages)
        parsed = result.get("parsed")
        parsing_error = result.get("parsing_error")

        if parsed is not None:
            logger.info(
                f"Research agent structured output succeeded | "
                f"attempt={attempt + 1} | attractions={len(parsed.attractions)}"
            )
            return parsed

        last_error = str(parsing_error) if parsing_error else "Unknown parse error"
        logger.warning(f"Research structured output parse failed (attempt {attempt + 1}): {last_error}")

    logger.error(f"Research agent failed structured output after {max_retries + 1} attempts")
    raise LLMOutputParseError("ResearchOutput", max_retries + 1)
