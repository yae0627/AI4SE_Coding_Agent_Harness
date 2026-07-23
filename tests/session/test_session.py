from ai4se_agent.session.session import Session, AgentRuntime
from ai4se_agent.session.history import MessageHistory
from ai4se_agent.core.event_bus import EventBus
from ai4se_agent.config.loader import ConfigLoader


def test_session_send_returns_result():
    bus = EventBus()
    history = MessageHistory()
    config = ConfigLoader()
    config.set("provider", "name", "mock")
    session = Session(config=config, event_bus=bus, history=history)
    result = session.send("echo hello")
    assert result["status"] in ("success", "failed")
    assert "iterations" in result


def test_session_history_accumulates():
    bus = EventBus()
    history = MessageHistory()
    config = ConfigLoader()
    config.set("provider", "name", "mock")
    session = Session(config=config, event_bus=bus, history=history)
    session.send("first task")
    session.send("second task")
    messages = history.get_recent()
    assert len(messages) >= 2


def test_session_emits_session_events():
    bus = EventBus()
    events: list[str] = []
    bus.subscribe("SESSION_START", lambda e: events.append(e.type))
    bus.subscribe("SESSION_END", lambda e: events.append(e.type))
    history = MessageHistory()
    config = ConfigLoader()
    config.set("provider", "name", "mock")
    session = Session(config=config, event_bus=bus, history=history)
    session.send("task")
    assert "SESSION_START" in events


def test_agent_runtime_emits_agent_events():
    bus = EventBus()
    events: list[str] = []
    bus.subscribe("AGENT_START", lambda e: events.append("start"))
    bus.subscribe("AGENT_STOP", lambda e: events.append("stop"))
    history = MessageHistory()
    config = ConfigLoader()
    config.set("provider", "name", "mock")
    runtime = AgentRuntime(
        goal="test",
        history=history.get_recent(),
        config=config,
        event_bus=bus,
    )
    runtime.run()
    assert events == ["start", "stop"]


def test_agent_runtime_history_injected():
    bus = EventBus()
    history = MessageHistory()
    history.add_user("previous task")
    history.add_assistant("previous response")
    config = ConfigLoader()
    config.set("provider", "name", "mock")
    runtime = AgentRuntime(
        goal="new task",
        history=history.get_recent(),
        config=config,
        event_bus=bus,
    )
    runtime.run()
    assert len(runtime._state.history) >= 2
