from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.types import Action

def test_agent_state_initialization():
    state = AgentState(goal="fix the bug")
    assert state.goal == "fix the bug"
    assert state.current_state == "IDLE"
    assert state.iteration == 0
    assert state.retry_count == 0

def test_agent_state_record_turn():
    state = AgentState(goal="test")
    action = Action(name="shell", params={"command": "pytest"})
    state.record_turn(action, "test output")
    assert len(state.history) == 1
    assert state.history[0]["action"].name == "shell"

def test_agent_state_increment():
    state = AgentState(goal="test")
    state.increment_iteration()
    assert state.iteration == 1
