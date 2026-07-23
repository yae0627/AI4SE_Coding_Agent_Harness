import json
from ai4se_agent.observability.tracer import Tracer, NullTracer
from ai4se_agent.observability.events import StateEvent, ToolEvent


def test_tracer_records_and_saves(tmp_path):
    tracer = Tracer()
    tracer.record(StateEvent(iteration=1, old_state="IDLE", new_state="CONTEXT_ORG"))
    tracer.record(ToolEvent(iteration=1, tool="shell", success=True))
    path = tmp_path / "trace.json"
    tracer.save(str(path))
    data = json.loads(path.read_text())
    assert len(data) == 2
    assert data[0]["type"] == "state_changed"
    assert "timestamp" in data[0]
    assert "elapsed_ms" in data[0]


def test_tracer_replay(tmp_path):
    tracer = Tracer()
    tracer.record(StateEvent(iteration=1, old_state="IDLE", new_state="CONTEXT_ORG"))
    path = tmp_path / "trace.json"
    tracer.save(str(path))
    events = Tracer.replay(str(path))
    assert len(events) == 1
    assert events[0]["old_state"] == "IDLE"


def test_null_tracer():
    tracer = NullTracer()
    tracer.record(StateEvent(iteration=1, old_state="IDLE", new_state="CONTEXT_ORG"))
    tracer.save("ignored.json")
    events = Tracer.replay("ignored.json")
    assert events == []


def test_tracer_record_token():
    tracer = Tracer()
    tracer.record_token(100, 50)
    assert tracer.total_tokens == 150


def test_tracer_replay_filtered_by_type(tmp_path):
    tracer = Tracer()
    tracer.record(StateEvent(iteration=1, old_state="IDLE", new_state="CONTEXT_ORG"))
    tracer.record(ToolEvent(iteration=1, tool="shell", success=True))
    path = tmp_path / "trace.json"
    tracer.save(str(path))
    state_events = tracer.replay_filtered(str(path), event_type="state_changed")
    assert len(state_events) == 1
    assert state_events[0]["type"] == "state_changed"


def test_tracer_replay_filtered_by_iteration(tmp_path):
    tracer = Tracer()
    tracer.record(StateEvent(iteration=1, old_state="IDLE", new_state="CONTEXT_ORG"))
    tracer.record(StateEvent(iteration=5, old_state="CONTEXT_ORG", new_state="LLM_CALL"))
    tracer.record(StateEvent(iteration=10, old_state="LLM_CALL", new_state="STOP"))
    path = tmp_path / "trace.json"
    tracer.save(str(path))
    filtered = tracer.replay_filtered(str(path), min_iteration=5)
    assert len(filtered) == 2
