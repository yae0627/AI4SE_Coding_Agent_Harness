from ai4se_agent.core.events import AgentEvent
from ai4se_agent.core.event_bus import EventBus


def test_subscribe_and_publish():
    bus = EventBus()
    received: list[AgentEvent] = []

    def handler(event: AgentEvent) -> None:
        received.append(event)

    bus.subscribe("TOOL_START", handler)
    event = AgentEvent(type="TOOL_START", iteration=1, state="TOOL_EXEC", payload={})
    bus.publish(event)
    assert len(received) == 1
    assert received[0] is event


def test_multiple_subscribers():
    bus = EventBus()
    results: list[str] = []

    bus.subscribe("LLM_END", lambda e: results.append("a"))
    bus.subscribe("LLM_END", lambda e: results.append("b"))
    bus.publish(AgentEvent(type="LLM_END", iteration=1, state="LLM_CALL", payload={}))
    assert results == ["a", "b"]


def test_unrelated_subscriber_not_called():
    bus = EventBus()
    results: list[str] = []

    bus.subscribe("LLM_START", lambda e: results.append("called"))
    bus.publish(AgentEvent(type="TOOL_START", iteration=1, state="TOOL_EXEC", payload={}))
    assert results == []


def test_publish_no_subscribers_does_not_crash():
    bus = EventBus()
    bus.publish(AgentEvent(type="TOOL_END", iteration=1, state="TOOL_EXEC", payload={}))


def test_subscribe_same_handler_multiple_types():
    bus = EventBus()
    results: list[str] = []

    def handler(event: AgentEvent) -> None:
        results.append(event.type)

    bus.subscribe("TOOL_START", handler)
    bus.subscribe("TOOL_END", handler)
    bus.publish(AgentEvent(type="TOOL_START", iteration=1, state="TOOL_EXEC", payload={}))
    bus.publish(AgentEvent(type="TOOL_END", iteration=1, state="TOOL_EXEC", payload={}))
    assert results == ["TOOL_START", "TOOL_END"]


def test_crashing_handler_does_not_block_others():
    bus = EventBus()
    results: list[str] = []

    def bad_handler(event: AgentEvent) -> None:
        raise RuntimeError("boom")

    def good_handler(event: AgentEvent) -> None:
        results.append("good")

    bus.subscribe("TOOL_START", bad_handler)
    bus.subscribe("TOOL_START", good_handler)
    bus.publish(AgentEvent(type="TOOL_START", iteration=1, state="TOOL_EXEC", payload={}))
    assert results == ["good"]


from ai4se_agent.core.state_machine import HarnessStateMachine
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.llm.mock_adapter import MockAdapter
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.guardrails.engine import GuardrailEngine
from ai4se_agent.memory.manager import MemoryManager


def test_state_machine_emits_events():
    bus = EventBus()
    events: list[str] = []

    bus.subscribe("LLM_START", lambda e: events.append("llm_start"))
    bus.subscribe("LLM_END", lambda e: events.append("llm_end"))
    bus.subscribe("ACTION_CREATED", lambda e: events.append("action_created"))
    bus.subscribe("GUARDRAIL_PASS", lambda e: events.append("guardrail_pass"))
    bus.subscribe("TOOL_START", lambda e: events.append("tool_start"))
    bus.subscribe("TOOL_END", lambda e: events.append("tool_end"))
    bus.subscribe("FEEDBACK_COMPLETED", lambda e: events.append("feedback_completed"))
    bus.subscribe("MEMORY_WRITE", lambda e: events.append("memory_write"))
    bus.subscribe("AGENT_STOP", lambda e: events.append("agent_stop"))

    llm = MockAdapter(responses=[
        '{"action": "read_file", "parameters": {"path": "test.txt"}}',
        '{"action": "finish", "parameters": {}}',
    ])
    state = AgentState(goal="test")
    machine = HarnessStateMachine(
        agent_state=state,
        llm_adapter=llm,
        action_parser=ActionParser(),
        action_validator=ActionValidator(),
        tool_registry=ToolRegistry(),
        guardrail_engine=GuardrailEngine(),
        feedback_loop=None,
        memory_manager=MemoryManager(),
        max_iterations=3,
        event_bus=bus,
    )
    machine.run()

    assert "llm_start" in events
    assert "llm_end" in events
    assert "action_created" in events
    assert "tool_start" in events
    assert "agent_stop" in events


def test_state_machine_no_event_bus_does_not_crash():
    """Backward compat: StateMachine works without EventBus."""
    llm = MockAdapter(responses=['{"action": "finish", "parameters": {}}'])
    state = AgentState(goal="test")
    machine = HarnessStateMachine(
        agent_state=state,
        llm_adapter=llm,
        action_parser=ActionParser(),
        action_validator=ActionValidator(),
        tool_registry=ToolRegistry(),
        guardrail_engine=GuardrailEngine(),
        feedback_loop=None,
        memory_manager=MemoryManager(),
        max_iterations=3,
    )
    result = machine.run()
    assert result["status"] in ("success", "failed")
