from ai4se_agent.core.state_machine import HarnessStateMachine
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.core.event_bus import EventBus
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.tools.write_file import WriteFileTool
from ai4se_agent.guardrails.engine import GuardrailEngine
from ai4se_agent.llm.mock_adapter import MockAdapter


def test_plan_create_and_update():
    """LLM creates a plan, then marks steps done one by one."""
    bus = EventBus()
    plan_events = []
    bus.subscribe("PLAN_UPDATED", lambda e: plan_events.append(e.payload))

    llm = MockAdapter(responses=[
        # Round 1: create plan
        '{"message": "Breaking into steps", "action": {"name": "plan_create", "parameters": {"steps": ["Step A", "Step B"]}}}',
        # Round 2: update step 0 to in_progress
        '{"action": {"name": "plan_update", "parameters": {"step_index": 0, "status": "in_progress"}}}',
        # Round 3: do work + mark step 0 done
        '{"message": "Step A done", "action": {"name": "plan_update", "parameters": {"step_index": 0, "status": "done"}}}',
        # Round 4: start and complete step 1
        '{"message": "Step B done", "action": {"name": "plan_update", "parameters": {"step_index": 1, "status": "done"}}}',
        # Round 5: finish
        '{"action": {"name": "finish", "parameters": {}}}',
    ])

    state = AgentState(goal="test plan")
    sm = HarnessStateMachine(
        agent_state=state, llm_adapter=llm,
        action_parser=ActionParser(), action_validator=ActionValidator(),
        tool_registry=ToolRegistry(), guardrail_engine=GuardrailEngine(),
        feedback_loop=None, max_iterations=10, max_step_iterations=5,
        event_bus=bus, interactive=False,
    )
    result = sm.run()
    assert result["status"] == "success"
    assert state.plan is not None
    assert state.plan.completed()
    assert state.plan.steps[0].status == "done"
    assert state.plan.steps[1].status == "done"
    assert len(plan_events) >= 4


def test_plan_step_iteration_limit():
    """When a step exceeds max_step_iterations, it's marked failed."""
    bus = EventBus()
    plan_events = []
    bus.subscribe("PLAN_UPDATED", lambda e: plan_events.append(e.payload))

    # LLM creates a plan but never marks the first step done —
    # it just keeps doing write_file over and over
    responses = [
        '{"message": "Creating plan", "action": {"name": "plan_create", "parameters": {"steps": ["Write file"]}}}',
    ]
    # Keep writing the same file — step should eventually be marked failed
    for _ in range(8):
        responses.append(
            '{"message": "Writing file...", "action": {"name": "write_file", "parameters": {"path": "test.txt", "content": "data"}}}'
        )
    responses.append('{"action": {"name": "finish", "parameters": {}}}')

    llm = MockAdapter(responses=responses)
    registry = ToolRegistry()
    registry.register(WriteFileTool())

    state = AgentState(goal="test step limit")
    sm = HarnessStateMachine(
        agent_state=state, llm_adapter=llm,
        action_parser=ActionParser(), action_validator=ActionValidator(),
        tool_registry=registry, guardrail_engine=GuardrailEngine(),
        feedback_loop=None, max_iterations=20, max_step_iterations=3,
        event_bus=bus, interactive=False,
    )
    sm.run()
    # The step should have been auto-marked as failed after exceeding 3 iterations
    assert state.plan is not None
    # The plan should still exist (not stopped globally)
    # After step failure, LLM can recover instead of dying with max_iteration
    assert state.plan.steps[0].status == "failed"


def test_no_plan_works_normally():
    """Without a plan, the agent behaves exactly as before."""
    bus = EventBus()
    llm = MockAdapter(responses=[
        '{"message": "doing work", "action": {"name": "finish", "parameters": {}}}',
    ])
    state = AgentState(goal="simple task")
    sm = HarnessStateMachine(
        agent_state=state, llm_adapter=llm,
        action_parser=ActionParser(), action_validator=ActionValidator(),
        tool_registry=ToolRegistry(), guardrail_engine=GuardrailEngine(),
        feedback_loop=None, event_bus=bus, interactive=False,
    )
    result = sm.run()
    assert result["status"] == "success"
    assert state.plan is None
    assert result["iterations"] == 1
