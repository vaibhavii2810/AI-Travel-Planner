"""
Unit tests for Research Agent.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from app.core.exceptions import ToolExecutionError
from app.models.domain import Attraction, ResearchOutput, WeatherSummary


@pytest.fixture
def mock_research_output():
    return ResearchOutput(
        general_destination_info="A great city.",
        attractions=[Attraction(name="Tower", description="Big tower")],
        weather_summary=WeatherSummary(conditions="Sunny"),
        safety_considerations=["Keep an eye on belongings."],
        local_tips=["Use the metro."],
        seasonal_notes="Summer is hot.",
        research_sources=["https://example.com"],
        researched_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
@patch("app.agents.research_agent._build_research_llm")
async def test_research_agent_success(mock_build_llm, mock_research_output, test_settings):
    mock_llm = MagicMock()
    mock_build_llm.return_value = mock_llm

    # Setup bind_tools mock
    mock_llm_with_tools = AsyncMock()
    # First ainvoke returns a tool call for web search
    mock_llm_with_tools.ainvoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[{"name": "web_search_tool", "args": {"query": "test"}, "id": "call_1"}],
        ),
        AIMessage(content="Done researching"), # Second call finishes loop
    ]
    mock_llm.bind_tools.return_value = mock_llm_with_tools

    # Setup structured output mock
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = {"parsed": mock_research_output, "parsing_error": None}
    mock_llm.with_structured_output.return_value = mock_structured_llm

    from app.agents.research_agent import invoke_research_agent

    mock_web_search = MagicMock()
    mock_web_search.name = "web_search_tool"
    mock_web_search.invoke.return_value = "Search result"

    with patch("app.agents.research_agent._RESEARCH_TOOLS", [mock_web_search]):
        result = await invoke_research_agent(
            destination="Paris",
            start_date="2025-05-01",
            end_date="2025-05-07",
            num_days=6,
            num_travelers=2,
            budget_min=1000,
            budget_max=2000,
            budget_currency="USD",
            interests=["food"],
        )

        assert result == mock_research_output
        mock_web_search.invoke.assert_called_once()
        mock_structured_llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
@patch("app.agents.research_agent._build_research_llm")
async def test_research_agent_web_search_failure(mock_build_llm, test_settings):
    # Test requirement: "If mandatory web research completely fails, surface a meaningful workflow error rather than silently hallucinating research."
    mock_llm = MagicMock()
    mock_build_llm.return_value = mock_llm

    mock_llm_with_tools = AsyncMock()
    # Agent tries to call web search, but we will make it fail
    mock_llm_with_tools.ainvoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[{"name": "web_search_tool", "args": {"query": "test"}, "id": "call_1"}],
        ),
        AIMessage(content="Done researching"),
    ]
    mock_llm.bind_tools.return_value = mock_llm_with_tools

    from app.agents.research_agent import invoke_research_agent

    mock_web_search = MagicMock()
    mock_web_search.name = "web_search_tool"
    mock_web_search.invoke.side_effect = Exception("API down")

    with patch("app.agents.research_agent._RESEARCH_TOOLS", [mock_web_search]):
        with pytest.raises(ToolExecutionError, match="Mandatory web research completely failed"):
            await invoke_research_agent(
                destination="Paris",
                start_date="2025-05-01",
                end_date="2025-05-07",
                num_days=6,
                num_travelers=2,
                budget_min=1000,
                budget_max=2000,
                budget_currency="USD",
                interests=["food"],
            )


@pytest.mark.asyncio
@patch("app.agents.research_agent._build_research_llm")
async def test_research_agent_parse_error_raises_after_retries(mock_build_llm, test_settings):
    """Req 9: LLMOutputParseError must surface when structured output exhausts all retries."""
    mock_llm = MagicMock()
    mock_build_llm.return_value = mock_llm

    mock_llm_with_tools = AsyncMock()
    mock_llm_with_tools.ainvoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[{"name": "web_search_tool", "args": {"query": "test"}, "id": "call_1"}],
        ),
        AIMessage(content="Done"),
    ]
    mock_llm.bind_tools.return_value = mock_llm_with_tools

    # Structured LLM always fails to parse
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = {"parsed": None, "parsing_error": "Bad JSON"}
    mock_llm.with_structured_output.return_value = mock_structured_llm

    from app.core.exceptions import LLMOutputParseError
    from app.agents.research_agent import invoke_research_agent

    mock_web_search = MagicMock()
    mock_web_search.name = "web_search_tool"
    mock_web_search.invoke.return_value = "Search result"

    with patch("app.agents.research_agent._RESEARCH_TOOLS", [mock_web_search]):
        with pytest.raises(LLMOutputParseError):
            await invoke_research_agent(
                destination="Paris",
                start_date="2025-05-01",
                end_date="2025-05-07",
                num_days=6,
                num_travelers=2,
                budget_min=1000,
                budget_max=2000,
                budget_currency="USD",
                interests=["food"],
                max_retries=1,
            )
    # Verify retry loop ran: 1 initial + 1 retry = 2 calls
    assert mock_structured_llm.ainvoke.call_count == 2


@pytest.mark.asyncio
@patch("app.agents.research_agent._build_research_llm")
async def test_research_agent_rejection_feedback_included(mock_build_llm, mock_research_output, test_settings):
    """Req: rejection_feedback must be forwarded to build_research_prompt."""
    mock_llm = MagicMock()
    mock_build_llm.return_value = mock_llm

    mock_llm_with_tools = AsyncMock()
    mock_llm_with_tools.ainvoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[{"name": "web_search_tool", "args": {"query": "safety"}, "id": "call_2"}],
        ),
        AIMessage(content="Done"),
    ]
    mock_llm.bind_tools.return_value = mock_llm_with_tools

    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = {"parsed": mock_research_output, "parsing_error": None}
    mock_llm.with_structured_output.return_value = mock_structured_llm

    from app.agents.research_agent import invoke_research_agent
    from app.prompts.research_agent import build_research_prompt

    mock_web_search = MagicMock()
    mock_web_search.name = "web_search_tool"
    mock_web_search.invoke.return_value = "Updated safety data"

    with patch("app.agents.research_agent._RESEARCH_TOOLS", [mock_web_search]):
        with patch("app.agents.research_agent.build_research_prompt", wraps=build_research_prompt) as spy:
            await invoke_research_agent(
                destination="Tokyo",
                start_date="2025-06-01",
                end_date="2025-06-08",
                num_days=7,
                num_travelers=1,
                budget_min=500,
                budget_max=1500,
                budget_currency="USD",
                interests=["culture"],
                rejection_feedback="Safety information was outdated.",
            )
            call_kwargs = spy.call_args
            assert call_kwargs.kwargs["rejection_feedback"] == "Safety information was outdated."

