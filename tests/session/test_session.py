from ai4se_agent.session.session import Session, AgentRuntime
from ai4se_agent.session.history import ConversationMemory
from ai4se_agent.core.event_bus import EventBus
from ai4se_agent.config.loader import ConfigLoader


def test_session_send_returns_result():
    bus = EventBus()
    mem = ConversationMemory()
    config = ConfigLoader()
    config.set("provider", "name", "mock")
    session = Session(config=config, event_bus=bus, memory=mem)
    result = session.send("echo hello")
    assert result["status"] in ("success", "failed")
    assert "iterations" in result


def test_session_history_accumulates_detailed():
    """After send(), ConversationMemory contains detailed turn history, not just summary."""
    bus = EventBus()
    mem = ConversationMemory()
    config = ConfigLoader()
    config.set("provider", "name", "mock")
    session = Session(config=config, event_bus=bus, memory=mem)
    session.send("first task")
    messages = mem.get_all()
    assert len(messages) >= 2
    user_messages = [m for m in messages if m["role"] == "user"]
    assert any("first task" in m["content"] for m in user_messages)


def test_session_emits_session_events():
    bus = EventBus()
    events: list[str] = []
    bus.subscribe("SESSION_START", lambda e: events.append(e.type))
    bus.subscribe("SESSION_END", lambda e: events.append(e.type))
    mem = ConversationMemory()
    config = ConfigLoader()
    config.set("provider", "name", "mock")
    session = Session(config=config, event_bus=bus, memory=mem)
    session.send("task")
    assert "SESSION_START" in events


def test_agent_runtime_emits_agent_events():
    bus = EventBus()
    events: list[str] = []
    bus.subscribe("AGENT_START", lambda e: events.append("start"))
    bus.subscribe("AGENT_STOP", lambda e: events.append("stop"))
    mem = ConversationMemory()
    config = ConfigLoader()
    config.set("provider", "name", "mock")
    runtime = AgentRuntime(
        goal="test",
        memory=mem,
        config=config,
        event_bus=bus,
    )
    runtime.run()
    assert events == ["start", "stop"]


def test_agent_runtime_history_injected():
    """After run(), state.history is populated from ConversationMemory at start."""
    bus = EventBus()
    mem = ConversationMemory()
    mem.append("user", "previous task")
    mem.append("assistant", "previous response")
    config = ConfigLoader()
    config.set("provider", "name", "mock")
    runtime = AgentRuntime(
        goal="new task",
        memory=mem,
        config=config,
        event_bus=bus,
    )
    runtime.run()
    assert len(runtime._state.history) >= 2
