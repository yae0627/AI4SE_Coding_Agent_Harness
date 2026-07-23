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
