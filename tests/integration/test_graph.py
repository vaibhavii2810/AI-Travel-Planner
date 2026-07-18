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
async def test_reject_terminates_graph(compiled_graph, sample_travel_request):
    """Tests that reject routes to rejected_node and terminates cleanly."""
    from app.graph.state import STATUS_REJECTED

    plan_id = "test-plan-reject-terminal"
    config = {"configurable": {"thread_id": plan_id}}
    state = initial_state(plan_id, sample_travel_request)

    from unittest.mock import patch
    with patch("app.graph.nodes.research_node.invoke_research_agent") as mock_research, \
         patch("app.graph.nodes.planner_node.invoke_planner_agent") as mock_planner:
        
        mock_research.return_value = {"dummy": "research"}
        mock_planner.return_value = {"dummy": "itinerary", "version": 1}

        # Run to first pause
        await compiled_graph.ainvoke(state, config=config)
        
        reject_decision = {
            "action": "reject", 
            "feedback": "I don't want this plan at all.",
            "modifications": None
        }
        
        # Resume — should go to rejected_node and terminate
        resumed_result = await compiled_graph.ainvoke(Command(resume=reject_decision), config=config)
        
        # Status must be rejected (terminal)
        assert resumed_result.get("status") == STATUS_REJECTED
        
        # Graph must have finished cleanly
        snapshot = await compiled_graph.aget_state(config)
        assert snapshot.next == ()
        
        # Planner was called only once (initial plan) — reject does NOT re-plan
        assert mock_planner.call_count == 1

@pytest.mark.asyncio
async def test_modify_routing_loop(compiled_graph, sample_travel_request):
    """TEST 4: Tests that a modify request routes correctly back to the planner."""
    plan_id = "test-plan-modify-loop"
    config = {"configurable": {"thread_id": plan_id}}
    state = initial_state(plan_id, sample_travel_request)

    from unittest.mock import patch
    with patch("app.graph.nodes.research_node.invoke_research_agent") as mock_research, \
         patch("app.graph.nodes.planner_node.invoke_planner_agent") as mock_planner:
        
        mock_research.return_value = {"dummy": "research"}
        mock_planner.return_value = {"dummy": "itinerary", "version": 1}

        # Run to first pause
        await compiled_graph.ainvoke(state, config=config)
        
        # Modify
        modify_decision = {
            "action": "modify", 
            "feedback": None,
            "modifications": {"add_hike": True}
        }
        
        # Resume
        resumed_result = await compiled_graph.ainvoke(Command(resume=modify_decision), config=config)
        
        assert resumed_result.get("status") == STATUS_AWAITING_REVIEW
        assert resumed_result.get("revision_count") == 2
        
        assert mock_planner.call_count == 2
        assert mock_research.call_count == 1

@pytest.mark.asyncio
async def test_persistence_recovery(sample_travel_request):
    """TEST 5: Persist an interrupted workflow -> recreate app dependencies -> retrieve/resume -> prove state not lost."""
    plan_id = "test-plan-persistence-recovery"
    config = {"configurable": {"thread_id": plan_id}}
    state = initial_state(plan_id, sample_travel_request)

    from langgraph.checkpoint.memory import MemorySaver
    from app.graph.graph import build_graph
    from unittest.mock import patch

    # Create first checkpointer instance
    checkpointer = MemorySaver()
    graph_v1 = build_graph(checkpointer)

    with patch("app.graph.nodes.research_node.invoke_research_agent") as mock_research, \
         patch("app.graph.nodes.planner_node.invoke_planner_agent") as mock_planner:
        
        mock_research.return_value = {"dummy": "research"}
        mock_planner.return_value = {"dummy": "itinerary", "version": 1}

        # Run to first pause
        await graph_v1.ainvoke(state, config=config)
        
    # Recreate app dependencies using the same checkpointer backend (MemorySaver persists in dict)
    graph_v2 = build_graph(checkpointer)
    
    # Retrieve state
    snapshot = await graph_v2.aget_state(config)
    assert snapshot.next == ("hitl_review_node",)
    assert snapshot.values.get("status") == STATUS_AWAITING_REVIEW

    # Resume with approve on the new graph instance
    with patch("app.graph.nodes.finalize_node.finalize_node") as mock_finalize:
        mock_finalize.return_value = {"status": STATUS_FINALIZED}
        
        review_decision = {"action": "approve", "feedback": None, "modifications": None}
        final_result = await graph_v2.ainvoke(Command(resume=review_decision), config=config)
        
        assert final_result.get("status") == STATUS_FINALIZED
        
        final_snapshot = await graph_v2.aget_state(config)
        assert final_snapshot.next == ()

@pytest.mark.asyncio
async def test_invalid_review_action_rejected(compiled_graph, sample_travel_request):
    """TEST 6: Invalid review action is rejected."""
    plan_id = "test-plan-invalid-action"
    config = {"configurable": {"thread_id": plan_id}}
    state = initial_state(plan_id, sample_travel_request)

    from unittest.mock import patch
    with patch("app.graph.nodes.research_node.invoke_research_agent") as mock_research, \
         patch("app.graph.nodes.planner_node.invoke_planner_agent") as mock_planner:
        
        mock_research.return_value = {"dummy": "research"}
        mock_planner.return_value = {"dummy": "itinerary", "version": 1}
        
        await compiled_graph.ainvoke(state, config=config)
        
        invalid_decision = {"action": "invalid_action"}
        
        # In our implementation, invalid actions hit the fallback in route_after_review
        # which logs an error and routes back to planner_node (defensive routing)
        resumed_result = await compiled_graph.ainvoke(Command(resume=invalid_decision), config=config)
        assert resumed_result.get("status") == "awaiting_review"

@pytest.mark.asyncio
async def test_maximum_revision_behavior(compiled_graph, sample_travel_request):
    """TEST 7: Maximum revision behavior works."""
    from app.graph.state import STATUS_MAX_REVISIONS
    
    plan_id = "test-plan-max-revisions"
    config = {"configurable": {"thread_id": plan_id}}
    state = initial_state(plan_id, sample_travel_request)
    # Set revision count to 1 less than MAX (MAX is 5 by default)
    state["revision_count"] = 4

    from unittest.mock import patch
    with patch("app.graph.nodes.research_node.invoke_research_agent") as mock_research, \
         patch("app.graph.nodes.planner_node.invoke_planner_agent") as mock_planner:
        
        mock_research.return_value = {"dummy": "research"}
        mock_planner.return_value = {"dummy": "itinerary", "version": 1}

        # Run to first pause
        await compiled_graph.ainvoke(state, config=config)
        
        reject_decision = {
            "action": "reject", 
            "feedback": "make it cheaper", 
            "modifications": None
        }
        
        # Resume. Since revision_count was 3, the router should see it increment to 4
        # and trigger max_revisions_node -> END.
        resumed_result = await compiled_graph.ainvoke(Command(resume=reject_decision), config=config)
        
        assert resumed_result.get("status") == STATUS_MAX_REVISIONS
        
        final_snapshot = await compiled_graph.aget_state(config)
        assert final_snapshot.next == () # Execution completed cleanly without crashing
