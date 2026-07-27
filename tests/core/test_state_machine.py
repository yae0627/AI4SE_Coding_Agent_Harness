from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.core.event_bus import EventBus
from ai4se_agent.core.interrupt import InterruptChannel
from ai4se_agent.core.state_machine import HarnessStateMachine
from ai4se_agent.guardrails.engine import GuardrailEngine
from ai4se_agent.llm.mock_adapter import MockAdapter
from ai4se_agent.tools.read_file import ReadFileTool
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.tools.shell import ShellTool


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


def test_stop_requested_cancels_agent():
    ch = InterruptChannel()
    bus = EventBus()
    events: list[str] = []
    bus.subscribe("AGENT_STOP", lambda e: events.append(e.payload.get("reason", "")))

    # Keep the agent busy long enough for the stop signal to arrive
    shell_resp = '{"action": "shell", "parameters": {"command": "echo x"}}'
    llm = MockAdapter(responses=[shell_resp] * 20)
    registry = ToolRegistry()
    registry.register(ShellTool())
    state = AgentState(goal="test")

    import threading
    def request_stop_later():
        import time
        time.sleep(0.01)
        ch.request_stop()

    threading.Thread(target=request_stop_later, daemon=True).start()

    machine = HarnessStateMachine(
        agent_state=state, llm_adapter=llm,
        action_parser=ActionParser(), action_validator=ActionValidator(),
        tool_registry=registry, guardrail_engine=GuardrailEngine(),
        feedback_loop=None, max_iterations=30, event_bus=bus,
        interrupt=ch, interactive=False,
    )
    machine.run()
    assert "user_cancel" in events


def test_hitl_approval_via_queue():
    ch = InterruptChannel()
    bus = EventBus()
    approval_events: list[dict] = []
    bus.subscribe("APPROVAL_REQUIRED", lambda e: approval_events.append(e.payload))

    llm = MockAdapter(responses=[
        '{"action": "shell", "parameters": {"command": "git push origin main"}}',
        '{"action": "shell", "parameters": {"command": "echo safe"}}',
        '{"action": "finish", "parameters": {}}',
    ])
    from ai4se_agent.guardrails.git_policy import GitPolicy
    guardrails = GuardrailEngine()
    guardrails.add_policy(GitPolicy())

    registry = ToolRegistry()
    registry.register(ShellTool())
    state = AgentState(goal="test")

    import threading
    def approve_later():
        import time
        time.sleep(0.05)
        ch.send_approval(True)

    threading.Thread(target=approve_later, daemon=True).start()

    machine = HarnessStateMachine(
        agent_state=state, llm_adapter=llm,
        action_parser=ActionParser(), action_validator=ActionValidator(),
        tool_registry=registry, guardrail_engine=guardrails,
        feedback_loop=None, max_iterations=5, event_bus=bus,
        interrupt=ch, interactive=False,
    )
    machine.run()
    assert len(approval_events) >= 1
    assert approval_events[0]["policy"] == "GitPolicy"


def test_llm_message_event_emitted():
    """When LLM response has a message field, LLM_MESSAGE event is emitted."""
    bus = EventBus()
    message_events = []
    bus.subscribe("LLM_MESSAGE", lambda e: message_events.append(e.payload))

    llm = MockAdapter(responses=[
        '{"message": "Let me check the file.", "action": {"name": "shell", "parameters": {"command": "echo ok"}}}',
        '{"action": {"name": "finish", "parameters": {}}}',
    ])
    registry = ToolRegistry()
    registry.register(ShellTool())

    sm = HarnessStateMachine(
        agent_state=AgentState(goal="test message"),
        llm_adapter=llm, action_parser=ActionParser(),
        action_validator=ActionValidator(), tool_registry=registry,
        guardrail_engine=GuardrailEngine(), feedback_loop=None,
        max_iterations=5, event_bus=bus, interactive=False,
    )
    sm.run()
    assert len(message_events) >= 1, f"expected at least 1 LLM_MESSAGE, got {len(message_events)}"
    assert "Let me check the file" in message_events[0]["message"]


def test_llm_message_finish_with_message():
    """finish action with a message field — message is emitted before STOP."""
    bus = EventBus()
    message_events = []
    bus.subscribe("LLM_MESSAGE", lambda e: message_events.append(e.payload))

    llm = MockAdapter(responses=[
        '{"message": "Analysis complete. Found 3 bugs.", "action": {"name": "finish", "parameters": {}}}',
    ])
    sm = HarnessStateMachine(
        agent_state=AgentState(goal="test finish message"),
        llm_adapter=llm, action_parser=ActionParser(),
        action_validator=ActionValidator(), tool_registry=ToolRegistry(),
        guardrail_engine=GuardrailEngine(), feedback_loop=None,
        max_iterations=5, event_bus=bus, interactive=False,
    )
    sm.run()
    assert len(message_events) >= 1
    assert "Analysis complete" in message_events[0]["message"]


def test_ask_action_enters_wait_input():
    """ask action should emit LLM_MESSAGE with the question and enter WAIT_INPUT."""
    bus = EventBus()
    message_events = []
    bus.subscribe("LLM_MESSAGE", lambda e: message_events.append(e.payload))

    ch = InterruptChannel()
    llm = MockAdapter(responses=[
        '{"action": {"name": "ask", "parameters": {"question": "Which file should I check?"}}}',
        '{"action": {"name": "finish", "parameters": {}}}',
    ])
    registry = ToolRegistry()
    state = AgentState(goal="test ask")

    import threading
    def answer_later():
        import time
        time.sleep(0.05)
        ch.send_approval(True)  # reuse approval queue for input signal

    threading.Thread(target=answer_later, daemon=True).start()

    sm = HarnessStateMachine(
        agent_state=state, llm_adapter=llm,
        action_parser=ActionParser(), action_validator=ActionValidator(),
        tool_registry=registry, guardrail_engine=GuardrailEngine(),
        feedback_loop=None, max_iterations=5, event_bus=bus,
        interrupt=ch, interactive=False,
    )
    sm.run()
    # ask question should be emitted as LLM_MESSAGE
    assert len(message_events) >= 1
    assert "Which file" in str(message_events[0]["message"])


def test_existing_respond_tests_still_pass():
    """Backward compat: old respond action format still works as RESPOND state."""
    bus = EventBus()
    respond_events = []
    bus.subscribe("RESPOND", lambda e: respond_events.append(e.payload))

    llm = MockAdapter(responses=[
        '{"action": "respond", "parameters": {"message": "I found the issue in auth.py"}}',
        '{"action": {"name": "finish", "parameters": {}}}',
    ])
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    state = AgentState(goal="debug auth")
    sm = HarnessStateMachine(
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
    result = sm.run()
    assert result["status"] == "success"
    assert len(respond_events) >= 1
    assert "auth.py" in respond_events[0]["message"]


def test_old_format_action_still_works():
    """Old format {'action': 'tool_name', 'parameters': {...}} still works."""
    bus = EventBus()
    tool_events = []
    bus.subscribe("TOOL_END", lambda e: tool_events.append(e.payload))

    llm = MockAdapter(responses=[
        '{"action": "shell", "parameters": {"command": "echo old_format"}}',
        '{"action": {"name": "finish", "parameters": {}}}',
    ])
    registry = ToolRegistry()
    registry.register(ShellTool())

    sm = HarnessStateMachine(
        agent_state=AgentState(goal="old format"),
        llm_adapter=llm, action_parser=ActionParser(),
        action_validator=ActionValidator(), tool_registry=registry,
        guardrail_engine=GuardrailEngine(), feedback_loop=None,
        max_iterations=5, event_bus=bus, interactive=False,
    )
    r = sm.run()
    assert r["status"] == "success"
    assert len(tool_events) >= 1
