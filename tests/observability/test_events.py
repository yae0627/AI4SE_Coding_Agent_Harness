# tests/observability/test_events.py
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
