"""
Unit tests for the Itinerary Planner Agent.
"""
from __future__ import annotations

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from app.core.exceptions import LLMOutputParseError
from app.models.domain import BudgetAllocation, Itinerary, ResearchOutput, TravelRequest


@pytest.fixture
def mock_travel_req():
    return TravelRequest(
        destination="Tokyo",
        start_date=date(2025, 5, 1),
        end_date=date(2025, 5, 3),
        budget_min=1000,
        budget_max=2000,
        interests=["food"],
        num_travelers=2,
    )


@pytest.fixture
def mock_research_out():
    return ResearchOutput(
        general_destination_info="Great place for food.",
        weather_summary={"conditions": "Sunny"}
    )


@pytest.fixture
def mock_itinerary():
    from app.models.domain import DailyPlan
    return Itinerary(
        destination="Tokyo",
        dates="May 1-3, 2025",
        budget_summary=BudgetAllocation(grand_total=1500),
        day_by_day_plans=[
            DailyPlan(day_number=1, date=date(2025, 5, 1)),
            DailyPlan(day_number=2, date=date(2025, 5, 2)),
            DailyPlan(day_number=3, date=date(2025, 5, 3)),
        ],
        total_estimated_cost=1500,
    )


@pytest.mark.asyncio
@patch("app.agents.itinerary_agent._build_planner_llm")
async def test_itinerary_agent_success(mock_build_llm, mock_travel_req, mock_research_out, mock_itinerary, test_settings):
    """Test standard initial generation with tool usage."""
    mock_llm = MagicMock()
    mock_build_llm.return_value = mock_llm

    # ReAct loop side effects
    mock_llm_with_tools = AsyncMock()
    mock_llm_with_tools.ainvoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[{"name": "budget_allocator_tool", "args": {"total_budget": 2000, "travelers": 2}, "id": "call_1"}],
        ),
        AIMessage(
            content="",
            tool_calls=[{"name": "schedule_optimizer_tool", "args": {"activities": []}, "id": "call_2"}],
        ),
        AIMessage(content="I have gathered the info."),
    ]
    mock_llm.bind_tools.return_value = mock_llm_with_tools

    # Structured LLM success
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = {"parsed": mock_itinerary, "parsing_error": None}
    mock_llm.with_structured_output.return_value = mock_structured_llm

    from app.agents.itinerary_agent import invoke_itinerary_agent

    mock_budget_tool = MagicMock()
    mock_budget_tool.name = "budget_allocator_tool"
    mock_budget_tool.invoke.return_value = {"food_total": 500}

    mock_schedule_tool = MagicMock()
    mock_schedule_tool.name = "schedule_optimizer_tool"
    mock_schedule_tool.invoke.return_value = []

    with patch("app.agents.itinerary_agent._PLANNER_TOOLS", [mock_budget_tool, mock_schedule_tool]):
        result = await invoke_itinerary_agent(
            travel_request=mock_travel_req,
            research_output=mock_research_out,
        )

    assert result.destination == "Tokyo"
    assert mock_llm_with_tools.ainvoke.call_count == 3
    assert mock_structured_llm.ainvoke.call_count == 1
    mock_budget_tool.invoke.assert_called_once()
    mock_schedule_tool.invoke.assert_called_once()


@pytest.mark.asyncio
@patch("app.agents.itinerary_agent._build_planner_llm")
async def test_itinerary_agent_parse_error_raises_after_retries(mock_build_llm, mock_travel_req, mock_research_out, test_settings):
    """Test that LLMOutputParseError is raised when max_retries is exceeded."""
    mock_llm = MagicMock()
    mock_build_llm.return_value = mock_llm

    mock_llm_with_tools = AsyncMock()
    mock_llm_with_tools.ainvoke.return_value = AIMessage(content="Ready")
    mock_llm.bind_tools.return_value = mock_llm_with_tools

    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = {"parsed": None, "parsing_error": "Invalid date format"}
    mock_llm.with_structured_output.return_value = mock_structured_llm

    from app.agents.itinerary_agent import invoke_itinerary_agent

    with patch("app.agents.itinerary_agent._PLANNER_TOOLS", []):
        with pytest.raises(LLMOutputParseError):
            await invoke_itinerary_agent(
                travel_request=mock_travel_req,
                research_output=mock_research_out,
                max_retries=1
            )
    
    assert mock_structured_llm.ainvoke.call_count == 2  # 1 initial + 1 retry


@pytest.mark.asyncio
@patch("app.agents.itinerary_agent._build_planner_llm")
async def test_itinerary_agent_feedback_included(mock_build_llm, mock_travel_req, mock_research_out, mock_itinerary, test_settings):
    """Test that rejection feedback and modification request are passed to prompt builder."""
    mock_llm = MagicMock()
    mock_build_llm.return_value = mock_llm

    mock_llm_with_tools = AsyncMock()
    mock_llm_with_tools.ainvoke.return_value = AIMessage(content="Ready")
    mock_llm.bind_tools.return_value = mock_llm_with_tools

    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = {"parsed": mock_itinerary, "parsing_error": None}
    mock_llm.with_structured_output.return_value = mock_structured_llm

    from app.agents.itinerary_agent import invoke_itinerary_agent
    from app.prompts.itinerary_agent import build_itinerary_prompt

    with patch("app.agents.itinerary_agent._PLANNER_TOOLS", []):
        with patch("app.agents.itinerary_agent.build_itinerary_prompt", wraps=build_itinerary_prompt) as spy:
            await invoke_itinerary_agent(
                travel_request=mock_travel_req,
                research_output=mock_research_out,
                rejection_feedback="Too expensive",
                modification_request="Add a hike",
                existing_itinerary=mock_itinerary,
            )
            
            call_kwargs = spy.call_args.kwargs
            assert call_kwargs["rejection_feedback"] == "Too expensive"
            assert call_kwargs["modification_request"] == "Add a hike"
            assert "May 1-3, 2025" in call_kwargs["existing_itinerary"]
