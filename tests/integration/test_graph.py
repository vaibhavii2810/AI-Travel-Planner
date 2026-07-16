"""
Integration tests for the LangGraph state machine.
Verifies HITL genuineness and the complete workflow.
"""
from __future__ import annotations

import pytest
from langgraph.types import Command

from app.graph.state import (
    STATUS_AWAITING_REVIEW,
    STATUS_FINALIZED,
    STATUS_REVISING,
    initial_state,
)


@pytest.mark.asyncio
async def test_hitl_genuinely_pauses(compiled_graph, sample_travel_request):
    """
    CRITICAL TEST: Verifies that the graph genuinely pauses at hitl_review_node
    and waits for external input via Command(resume=...).
    """
    plan_id = "test-plan-genuinely-pauses"
    config = {"configurable": {"thread_id": plan_id}}
    state = initial_state(plan_id, sample_travel_request)

    # 1. Start the graph. We don't await the full result, we just let it run until interrupt
    # We must patch the agents to return dummy data so they don't hit the real LLM
    from unittest.mock import patch
    with patch("app.graph.nodes.research_node.invoke_research_agent") as mock_research, \
         patch("app.graph.nodes.planner_node.invoke_planner_agent") as mock_planner:
        
        # Setup mocks
        mock_research.return_value = {"dummy": "research"}
        mock_planner.return_value = {"dummy": "itinerary", "version": 1}

        # Run until interrupt
        result = await compiled_graph.ainvoke(state, config=config)

    # 2. VERIFY HITL PAUSE (Risk 1 bypass verification)
    # The return value of ainvoke() when interrupted is the argument passed to interrupt()
    assert result.get("status") == STATUS_AWAITING_REVIEW
    
    # Verify the graph is actually paused by inspecting the checkpoint
    snapshot = await compiled_graph.aget_state(config)
    # next contains the nodes waiting to execute. If it's paused at hitl_review_node, 
    # the node itself is suspended midway. Actually, langgraph lists the node it paused in.
    assert snapshot.next == ("hitl_review_node",)

    # 3. RESUME the graph with an 'approve' action
    review_decision = {"action": "approve", "feedback": None, "modifications": None}
    
    # We resume by passing Command to ainvoke
    final_result = await compiled_graph.ainvoke(Command(resume=review_decision), config=config)

    # 4. VERIFY FINALIZATION
    assert final_result.get("status") == STATUS_FINALIZED
    
    # Verify graph is finished
    final_snapshot = await compiled_graph.aget_state(config)
    assert final_snapshot.next == () # empty tuple means execution completed


@pytest.mark.asyncio
async def test_reject_routing_loop(compiled_graph, sample_travel_request):
    """Tests that a rejection routes back correctly."""
    plan_id = "test-plan-reject-loop"
    config = {"configurable": {"thread_id": plan_id}}
    state = initial_state(plan_id, sample_travel_request)

    from unittest.mock import patch
    with patch("app.graph.nodes.research_node.invoke_research_agent") as mock_research, \
         patch("app.graph.nodes.planner_node.invoke_planner_agent") as mock_planner:
        
        mock_research.return_value = {"dummy": "research"}
        mock_planner.return_value = {"dummy": "itinerary", "version": 1}

        # Run to first pause
        await compiled_graph.ainvoke(state, config=config)
        
        # Reject with planner feedback
        reject_decision = {
            "action": "reject", 
            "feedback": "make it cheaper", # Doesn't trigger re-research
            "modifications": None
        }
        
        # Resume
        resumed_result = await compiled_graph.ainvoke(Command(resume=reject_decision), config=config)
        
        # Because we mocked planner to just return immediately, it should loop right back to review
        assert resumed_result.get("status") == STATUS_AWAITING_REVIEW
        assert resumed_result.get("revision_count") == 2
        
        # Check mock calls to ensure we hit planner again, but NOT research
        assert mock_planner.call_count == 2
        assert mock_research.call_count == 1
