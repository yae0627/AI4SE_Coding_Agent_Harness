# tests/test_cli.py
from ai4se_agent.cli import build_harness

def test_build_harness_creates_machine(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    harness = build_harness("test task", workspace="/tmp")
    assert harness is not None
    assert harness.state.goal == "test task"
