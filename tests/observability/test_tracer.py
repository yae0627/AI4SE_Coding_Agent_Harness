# tests/observability/test_tracer.py
import json
from ai4se_agent.observability.tracer import Tracer, NullTracer
from ai4se_agent.observability.events import StateEvent, ToolEvent, EventType

def test_tracer_records_and_saves(tmp_path):
    tracer = Tracer()
    tracer.record(StateEvent(iteration=1, old_state="IDLE", new_state="CONTEXT_ORG"))
    tracer.record(ToolEvent(iteration=1, tool="shell", success=True))
    path = tmp_path / "trace.json"
    tracer.save(str(path))
    data = json.loads(path.read_text())
    assert len(data) == 2
    assert data[0]["type"] == "state_changed"

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
