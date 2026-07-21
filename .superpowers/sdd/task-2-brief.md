# Task 2: AgentState

**Files:**
- Create: `src/ai4se_agent/core/agent_state.py`
- Create: `tests/core/test_agent_state.py`

**Interfaces:**
- Consumes: `Action`, `ToolResult` from Task 1
- Produces: `AgentState` consumed by state machine (Task 10)

## Step 1: Write the failing test

```python
# tests/core/test_agent_state.py
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
```

## Step 2: Run test to verify it fails

Run: `pytest tests/core/test_agent_state.py -v`
Expected: FAIL

## Step 3: Write minimal implementation

```python
# src/ai4se_agent/core/agent_state.py
from dataclasses import dataclass, field
from typing import Optional

from ai4se_agent.types import Action


@dataclass
class AgentState:
    goal: str
    current_state: str = "IDLE"
    iteration: int = 0
    context: list = field(default_factory=list)
    history: list = field(default_factory=list)
    last_action: Optional[Action] = None
    last_observation: Optional[str] = None
    error_count: int = 0
    retry_count: int = 0

    def record_turn(self, action: Action, observation: str) -> None:
        self.history.append({"action": action, "observation": observation})
        self.last_action = action
        self.last_observation = observation

    def increment_iteration(self) -> None:
        self.iteration += 1
```

## Step 4: Run tests

Run: `pytest tests/core/test_agent_state.py -v`
Expected: PASS

## Step 5: Commit

```bash
git add src/ai4se_agent/core/agent_state.py tests/core/test_agent_state.py
git commit -m "feat: add AgentState data model"
```

## Global Constraints

- Python >=3.10
- All core mechanisms must be testable with mock LLM (no network, no real LLM)
- No use of agent orchestration frameworks
- Tests in `tests/` mirroring `src/` structure
- No comments in code unless specified
