# Task 1: Shared Types

**Files:**
- Create: `src/ai4se_agent/types.py`
- Create: `tests/core/test_types.py`

**Interfaces:**
- Produces: `Action`, `ToolResult`, `Feedback`, `GuardrailResult`, `CorrectionPlan`, `StopReason` dataclasses consumed by all later tasks

## Step 1: Write the failing test

```python
# tests/core/test_types.py
from ai4se_agent.types import Action, ToolResult, Feedback, GuardrailResult, CorrectionPlan, StopReason

def test_action_creation():
    action = Action(name="read_file", params={"path": "test.txt"})
    assert action.name == "read_file"
    assert action.params == {"path": "test.txt"}

def test_tool_result_defaults():
    result = ToolResult(success=True, output="file content", error=None)
    assert result.success is True
    assert result.metadata == {}

def test_feedback_with_source():
    fb = Feedback(success=False, category="test_failure", message="AssertionError",
                  details={"line": 42}, severity=3, source="pytest")
    assert fb.source == "pytest"
    assert fb.severity == 3

def test_guardrail_result_verdict():
    gr = GuardrailResult(verdict="DENY", reason="dangerous command", policy="CommandPolicy",
                         severity=5, metadata={"command": "rm -rf /"})
    assert gr.verdict == "DENY"

def test_correction_plan():
    plan = CorrectionPlan(scope="validate()", target_files=["order.py"], strategy="Add null check", retry_count=0)
    assert plan.retry_count == 0

def test_stop_reason_values():
    assert StopReason.SUCCESS.value == "success"
    assert StopReason.MAX_ITERATION.value == "max_iteration"
```

## Step 2: Run test to verify it fails

Run: `pytest tests/core/test_types.py -v`
Expected: FAIL with "ModuleNotFoundError"

## Step 3: Write minimal implementation

```python
# src/ai4se_agent/types.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional


class StopReason(Enum):
    SUCCESS = "success"
    MAX_ITERATION = "max_iteration"
    REPEATED_FAILURE = "repeated_failure"
    LLM_ERROR = "llm_error"
    USER_CANCEL = "user_cancel"
    APPROVAL_TIMEOUT = "approval_timeout"


@dataclass
class Action:
    name: str
    params: dict


@dataclass
class ToolResult:
    success: bool
    output: str
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Feedback:
    success: bool
    category: str
    message: str
    details: dict = field(default_factory=dict)
    severity: int = 0
    source: str = ""


@dataclass
class GuardrailResult:
    verdict: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"]
    reason: str
    policy: str
    severity: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class CorrectionPlan:
    scope: str
    target_files: list
    strategy: str
    retry_count: int = 0
```

## Step 4: Run test to verify it passes

Run: `pytest tests/core/test_types.py -v`
Expected: PASS

## Step 5: Commit

```bash
git add src/ai4se_agent/types.py tests/core/test_types.py
git commit -m "feat: add shared types (Action, ToolResult, Feedback, GuardrailResult, CorrectionPlan)"
```

## Global Constraints

- Python >=3.10
- openai >=1.0.0 (direct dependency, used via LLMAdapter)
- transitions (state machine, not an agent framework)
- pytest >=8.0 (dev)
- All API keys via .env file, never hardcoded
- All core mechanisms must be testable with mock LLM (no network, no real LLM)
- No use of agent orchestration frameworks (LangChain AgentExecutor, AutoGen, CrewAI, etc.)
- File paths relative to workspace root
- Tests in `tests/` mirroring `src/` structure
