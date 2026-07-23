from ai4se_agent.core.events import AgentEvent


def test_agent_event_creation():
    event = AgentEvent(
        type="TOOL_START",
        iteration=1,
        state="TOOL_EXEC",
        payload={"tool": "shell", "command": "echo hello"},
    )
    assert event.type == "TOOL_START"
    assert event.iteration == 1
    assert event.state == "TOOL_EXEC"
    assert event.payload["tool"] == "shell"
    assert event.timestamp > 0


def test_agent_event_default_timestamp():
    event = AgentEvent(type="LLM_START", iteration=1, state="LLM_CALL", payload={})
    assert isinstance(event.timestamp, float)


def test_agent_event_to_dict():
    event = AgentEvent(
        type="TOOL_END",
        iteration=2,
        state="TOOL_EXEC",
        payload={"tool": "shell", "success": True, "duration": 1.5},
    )
    d = event.to_dict()
    assert d["type"] == "TOOL_END"
    assert d["iteration"] == 2
    assert d["state"] == "TOOL_EXEC"
    assert d["payload"]["tool"] == "shell"


def test_agent_event_from_dict():
    data = {
        "type": "LLM_END",
        "timestamp": 1000.0,
        "iteration": 3,
        "state": "LLM_CALL",
        "payload": {"model": "gpt-4", "tokens": 500},
    }
    event = AgentEvent.from_dict(data)
    assert event.type == "LLM_END"
    assert event.iteration == 3
    assert event.payload["tokens"] == 500


def test_agent_event_round_trip():
    original = AgentEvent(
        type="TOOL_END",
        iteration=5,
        state="TOOL_EXEC",
        payload={"tool": "shell", "success": True},
    )
    restored = AgentEvent.from_dict(original.to_dict())
    assert restored.type == original.type
    assert restored.iteration == original.iteration
    assert restored.state == original.state
    assert restored.payload == original.payload
