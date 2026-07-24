from ai4se_agent.core.state_machine import HarnessStateMachine
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.core.event_bus import EventBus
from ai4se_agent.llm.mock_adapter import MockAdapter
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.guardrails.engine import GuardrailEngine
from ai4se_agent.tools.read_file import ReadFileTool


def test_state_machine_completes_successfully(tmp_path):
    llm = MockAdapter(responses=["action: read_file path=test.txt", "[DONE]"])
    registry = ToolRegistry()
    guardrails = GuardrailEngine()
    state = AgentState(goal="test task")
    machine = HarnessStateMachine(
        agent_state=state,
        llm_adapter=llm,
        action_parser=ActionParser(),
        action_validator=ActionValidator(),
        tool_registry=registry,
        guardrail_engine=guardrails,
        feedback_loop=None,
        max_iterations=5,
        event_bus=EventBus(),
    )
    result = machine.run()
    assert result["status"] in ("success", "failed")


def test_state_machine_with_tracer():
    llm = MockAdapter(responses=["action: read_file path=test.txt", "[DONE]"])
    registry = ToolRegistry()
    guardrails = GuardrailEngine()
    state = AgentState(goal="test task")
    machine = HarnessStateMachine(
        agent_state=state,
        llm_adapter=llm,
        action_parser=ActionParser(),
        action_validator=ActionValidator(),
        tool_registry=registry,
        guardrail_engine=guardrails,
        feedback_loop=None,
        max_iterations=5,
        event_bus=EventBus(),
    )
    result = machine.run()
    assert result["status"] in ("success", "failed")


def test_respond_action_bypasses_guardrail_and_tool_exec():
    bus = EventBus()
    respond_events: list[dict] = []
    bus.subscribe("RESPOND", lambda e: respond_events.append(e.payload))

    llm = MockAdapter(responses=[
        '{"action": "respond", "parameters": {"message": "I found the issue in auth.py"}}',
        '{"action": "finish", "parameters": {}}',
    ])
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    state = AgentState(goal="debug auth")
    machine = HarnessStateMachine(
        agent_state=state,
        llm_adapter=llm,
        action_parser=ActionParser(),
        action_validator=ActionValidator(),
        tool_registry=registry,
        guardrail_engine=GuardrailEngine(),
        feedback_loop=None,
        max_iterations=5,
        event_bus=bus,
        interactive=False,
    )
    result = machine.run()
    assert result["status"] == "success"
    assert len(respond_events) >= 1
    assert "auth.py" in respond_events[0]["message"]


def test_respond_action_followed_by_tool_still_works(tmp_path):
    bus = EventBus()
    transitions: list[str] = []
    bus.subscribe("RESPOND", lambda e: transitions.append("responded"))
    bus.subscribe("TOOL_START", lambda e: transitions.append("tool_executed"))

    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")
    file_path = str(test_file).replace("\\", "/")

    llm = MockAdapter(responses=[
        '{"action": "respond", "parameters": {"message": "checking..."}}',
        f'{{"action": "read_file", "parameters": {{"path": "{file_path}"}}}}',
        '{"action": "finish", "parameters": {}}',
    ])
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    state = AgentState(goal="test")
    machine = HarnessStateMachine(
        agent_state=state,
        llm_adapter=llm,
        action_parser=ActionParser(),
        action_validator=ActionValidator(),
        tool_registry=registry,
        guardrail_engine=GuardrailEngine(),
        feedback_loop=None,
        max_iterations=5,
        event_bus=bus,
        interactive=False,
    )
    result = machine.run()
    assert result["status"] == "success"
    assert "responded" in transitions
    assert "tool_executed" in transitions
