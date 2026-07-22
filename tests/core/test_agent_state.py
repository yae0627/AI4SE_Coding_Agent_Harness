from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.types import Action

def test_agent_state_initialization():
    state = AgentState(goal="fix the bug")
    assert state.goal == "fix the bug"
    assert state.current_state == "IDLE"
    assert state.iteration == 0
    assert state.retry_count == 0
    assert state.history == []
    assert state.feedback == []

def test_agent_state_record_turn():
    state = AgentState(goal="test")
    action = Action(name="shell", params={"command": "pytest"})
    state.record_turn(action, "test output")
    assert len(state.history) == 2
    assert state.history[0]["role"] == "assistant"
    assert state.history[1]["role"] == "tool"
    assert state.history[1]["content"] == "test output"
    assert state.last_action is not None
    assert state.last_action.name == "shell"

def test_agent_state_record_feedback():
    state = AgentState(goal="test")
    state.record_feedback("pytest failed: AssertionError")
    assert len(state.feedback) == 1
    assert state.feedback[0]["role"] == "user"
    assert "AssertionError" in state.feedback[0]["content"]

def test_agent_state_increment():
    state = AgentState(goal="test")
    state.increment_iteration()
    assert state.iteration == 1
