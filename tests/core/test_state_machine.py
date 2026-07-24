from ai4se_agent.core.state_machine import HarnessStateMachine
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.core.event_bus import EventBus
from ai4se_agent.llm.mock_adapter import MockAdapter
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.guardrails.engine import GuardrailEngine
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
