from ai4se_agent.observability.events import EventType, StateEvent, LLMEvent


def test_event_type_values():
    assert EventType.STATE_CHANGED.value == "state_changed"
    assert EventType.LLM_CALLED.value == "llm_called"


def test_state_event():
    event = StateEvent(iteration=1, old_state="IDLE", new_state="CONTEXT_ORG")
    assert event.type == EventType.STATE_CHANGED
    assert event.old_state == "IDLE"
    assert event.iteration == 1


def test_llm_event():
    event = LLMEvent(iteration=1, model="mock", messages=[], response="action: shell command=echo")
    assert event.type == EventType.LLM_CALLED
    assert event.model == "mock"


def test_event_to_dict_includes_timestamp():
    event = StateEvent(iteration=1, old_state="IDLE", new_state="CONTEXT_ORG")
    event.timestamp = "2026-07-23T12:00:00"
    event.elapsed_ms = 150.0
    d = event.to_dict()
    assert d["timestamp"] == "2026-07-23T12:00:00"
    assert d["elapsed_ms"] == 150.0


def test_event_default_timestamp_empty():
    event = StateEvent(iteration=1, old_state="IDLE", new_state="CONTEXT_ORG")
    d = event.to_dict()
    assert d["timestamp"] == ""
    assert d["elapsed_ms"] == 0.0
