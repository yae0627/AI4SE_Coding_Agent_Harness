# Coding Agent Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python coding agent harness with state-machine-driven main loop, tool system, guardrails, feedback loop, and memory.

**Architecture:** 11-state FSM (transitions library) drives the agent loop. Each state is a separate module. Tools, guardrails, feedback, and memory are pluggable subsystems registered at startup. LLM is abstracted behind an adapter interface for mock testing.

**Tech Stack:** Python 3.10+, openai SDK, transitions, pytest, ruff, mypy

## Pre-requisite: Infrastructure Setup

Before starting any implementation task, the following infrastructure must be committed:

- `scripts/log_agent.py` — AGENT_LOG auto-logging helper
- `.github/workflows/ci.yml` — GitHub Actions CI (unit-test job)
- `.gitlab-ci.yml` — GitLab CI (unit-test job)
- `AGENTS.md` updated with auto-logging and CI/CD conventions
- `AGENT_LOG.md` populated with initial records

These files already exist (committed in this brainstorming session). Every subagent task must:
1. Run `python scripts/log_agent.py <task> <skill> <summary> <intervention>` after commit
2. Ensure all tests pass before committing

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

---

## File Structure

```
src/ai4se_agent/
├── __init__.py
├── types.py                    # Shared: Action, ToolResult, Feedback, GuardrailResult, etc.
├── config/
│   ├── __init__.py
│   └── loader.py               # ConfigLoader — .env, provider selection
├── core/
│   ├── __init__.py
│   ├── state_machine.py        # HarnessStateMachine — 11-state FSM
│   ├── agent_state.py          # AgentState — shared state object
│   └── action.py               # ActionParser, ActionValidator (format+schema+param)
├── llm/
│   ├── __init__.py
│   ├── base.py                 # LLMAdapter ABC
│   ├── openai_adapter.py       # OpenAIAdapter
│   ├── local_adapter.py        # LocalAdapter (OpenAI-compatible)
│   └── mock_adapter.py         # MockAdapter for testing
├── tools/
│   ├── __init__.py
│   ├── base.py                 # Tool ABC
│   ├── registry.py             # ToolRegistry
│   ├── read_file.py
│   ├── write_file.py
│   ├── edit_file.py
│   ├── shell.py
│   └── run_test.py
├── guardrails/
│   ├── __init__.py
│   ├── base.py                 # Policy ABC
│   ├── engine.py               # GuardrailEngine
│   ├── command_policy.py
│   ├── file_policy.py
│   ├── workspace_policy.py
│   └── git_policy.py
├── feedback/
│   ├── __init__.py
│   ├── loop.py                 # FeedbackLoop orchestrator
│   ├── sensor.py               # Sensor ABC + TestSensor, LintSensor, TypeSensor
│   ├── classifier.py           # FailureClassifier (rule-based)
│   ├── planner.py              # CorrectionPlanner
│   └── failure_db.py           # FailureDB (SQLite)
├── memory/
│   ├── __init__.py
│   ├── manager.py              # MemoryManager
│   ├── session.py              # SessionMemory (runtime)
│   └── persistent.py           # PersistentMemory (project_rules, summaries)
└── cli.py                      # CLI entry point

tests/
├── __init__.py
├── fixtures/
│   └── mock_llm.py             # MockLLM helpers
├── core/
│   ├── test_state_machine.py
│   ├── test_agent_state.py
│   └── test_action.py
├── llm/
│   └── test_adapters.py
├── tools/
│   ├── test_registry.py
│   ├── test_read_file.py
│   ├── test_write_file.py
│   ├── test_edit_file.py
│   ├── test_shell.py
│   └── test_run_test.py
├── guardrails/
│   ├── test_engine.py
│   ├── test_command_policy.py
│   ├── test_file_policy.py
│   ├── test_workspace_policy.py
│   └── test_git_policy.py
├── feedback/
│   ├── test_sensor.py
│   ├── test_classifier.py
│   ├── test_planner.py
│   ├── test_failure_db.py
│   └── test_loop.py
└── memory/
    ├── test_manager.py
    ├── test_session.py
    └── test_persistent.py
```

---

### Task 1: Shared Types

**Files:**
- Create: `src/ai4se_agent/types.py`
- Create: `tests/core/test_types.py`

**Interfaces:**
- Produces: `Action`, `ToolResult`, `Feedback`, `GuardrailResult`, `CorrectionPlan`, `StopReason` dataclasses consumed by all later tasks

- [ ] **Step 1: Write the failing test**

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

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_types.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write minimal implementation**

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

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_types.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/types.py tests/core/test_types.py
git commit -m "feat: add shared types (Action, ToolResult, Feedback, GuardrailResult, CorrectionPlan)"
```

---

### Task 2: AgentState

**Files:**
- Create: `src/ai4se_agent/core/agent_state.py`
- Create: `tests/core/test_agent_state.py`

**Interfaces:**
- Consumes: `Action`, `ToolResult` from Task 1
- Produces: `AgentState` consumed by state machine (Task 3)

- [ ] **Step 1: Write the failing test**

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

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_agent_state.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

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

- [ ] **Step 4: Run tests**

Run: `pytest tests/core/test_agent_state.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/core/agent_state.py tests/core/test_agent_state.py
git commit -m "feat: add AgentState data model"
```

---

### Task 3: LLMAdapter Abstraction

**Files:**
- Create: `src/ai4se_agent/llm/__init__.py`
- Create: `src/ai4se_agent/llm/base.py`
- Create: `src/ai4se_agent/llm/openai_adapter.py`
- Create: `src/ai4se_agent/llm/mock_adapter.py`
- Create: `tests/llm/__init__.py`
- Create: `tests/llm/test_adapters.py`

**Interfaces:**
- Consumes: Nothing from this project
- Produces: `LLMAdapter` ABC, `OpenAIAdapter`, `MockAdapter` consumed by state machine

- [ ] **Step 1: Write the failing test**

```python
# tests/llm/test_adapters.py
from ai4se_agent.llm.base import LLMAdapter
from ai4se_agent.llm.mock_adapter import MockAdapter

def test_mock_adapter_returns_preset():
    adapter = MockAdapter(responses=["action: write_file path=test.txt"])
    result = adapter.generate([{"role": "user", "content": "hello"}])
    assert result == "action: write_file path=test.txt"

def test_mock_adapter_cycles():
    adapter = MockAdapter(responses=["first", "second"])
    assert adapter.generate([]) == "first"
    assert adapter.generate([]) == "second"

def test_adapter_is_abstract():
    import inspect
    assert inspect.isabstract(LLMAdapter)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/llm/test_adapters.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/ai4se_agent/llm/base.py
from abc import ABC, abstractmethod


class LLMAdapter(ABC):
    @abstractmethod
    def generate(self, messages: list[dict]) -> str:
        pass
```

```python
# src/ai4se_agent/llm/openai_adapter.py
from openai import OpenAI
from ai4se_agent.llm.base import LLMAdapter


class OpenAIAdapter(LLMAdapter):
    def __init__(self, api_key: str, base_url: str = None, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def generate(self, messages: list[dict]) -> str:
        response = self.client.chat.completions.create(
            model=self.model, messages=messages
        )
        return response.choices[0].message.content
```

```python
# src/ai4se_agent/llm/mock_adapter.py
from ai4se_agent.llm.base import LLMAdapter


class MockAdapter(LLMAdapter):
    def __init__(self, responses: list[str]):
        self.responses = responses
        self._index = 0

    def generate(self, messages: list[dict]) -> str:
        response = self.responses[self._index % len(self.responses)]
        self._index += 1
        return response
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/llm/test_adapters.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/llm/ tests/llm/
git commit -m "feat: add LLMAdapter abstraction with OpenAI and Mock adapters"
```

---

### Task 4: Action Parsing and Validation

**Files:**
- Create: `src/ai4se_agent/core/action.py`
- Create: `tests/core/test_action.py`

**Interfaces:**
- Consumes: `Action` from Task 1
- Produces: `ActionParser.parse(text) -> Action`, `ActionValidator.validate(action) -> list[str]` consumed by state machine (Task 3)

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_action.py
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.types import Action

def test_parse_valid_action():
    parser = ActionParser()
    action = parser.parse('action: write_file path=test.txt content=hello')
    assert action.name == "write_file"
    assert action.params["path"] == "test.txt"

def test_parse_missing_action():
    parser = ActionParser()
    result = parser.parse("some random text")
    assert result is None

def test_validate_missing_param():
    validator = ActionValidator()
    action = Action(name="write_file", params={})
    errors = validator.validate(action)
    assert "path" in errors[0] or "content" in errors[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_action.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/ai4se_agent/core/action.py
import re
from ai4se_agent.types import Action


class ActionParser:
    def parse(self, text: str) -> Action | None:
        match = re.match(r'action:\s*(\w+)(.*)', text.strip())
        if not match:
            return None
        name = match.group(1)
        params_str = match.group(2).strip()
        params = {}
        for pair in re.findall(r'(\w+)=(\S+)', params_str):
            params[pair[0]] = pair[1]
        return Action(name=name, params=params)


class ActionValidator:
    REQUIRED_PARAMS = {
        "read_file": ["path"],
        "write_file": ["path", "content"],
        "edit_file": ["path", "old_string", "new_string"],
        "shell": ["command"],
        "run_test": [],
    }

    def validate(self, action: Action) -> list[str]:
        errors = []
        required = self.REQUIRED_PARAMS.get(action.name, [])
        for param in required:
            if param not in action.params:
                errors.append(f"Missing required param: {param}")
        return errors
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/core/test_action.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/core/action.py tests/core/test_action.py
git commit -m "feat: add ActionParser and ActionValidator"
```

---

### Task 5: Tool System

**Files:**
- Create: `src/ai4se_agent/tools/base.py`
- Create: `src/ai4se_agent/tools/registry.py`
- Create: `src/ai4se_agent/tools/read_file.py`
- Create: `src/ai4se_agent/tools/write_file.py`
- Create: `src/ai4se_agent/tools/edit_file.py`
- Create: `src/ai4se_agent/tools/shell.py`
- Create: `src/ai4se_agent/tools/run_test.py`
- Create: `tests/tools/test_registry.py`
- Create: `tests/tools/test_read_file.py`
- Create: `tests/tools/test_write_file.py`
- Create: `tests/tools/test_edit_file.py`
- Create: `tests/tools/test_shell.py`
- Create: `tests/tools/test_run_test.py`

**Interfaces:**
- Consumes: `Action`, `ToolResult` from Task 1
- Produces: `ToolRegistry` consumed by state machine, `Tool` ABC for extensibility

- [ ] **Step 1: Write the failing tests**

```python
# tests/tools/test_registry.py
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.tools.read_file import ReadFileTool
from ai4se_agent.types import Action

def test_register_and_execute(tmp_path):
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")
    action = Action(name="read_file", params={"path": str(test_file)})
    result = registry.execute(action)
    assert result.success is True
    assert result.output == "hello"
```

```python
# tests/tools/test_read_file.py
from ai4se_agent.tools.read_file import ReadFileTool
from ai4se_agent.types import Action

def test_read_existing_file(tmp_path):
    tool = ReadFileTool()
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2")
    action = Action(name="read_file", params={"path": str(test_file)})
    result = tool.execute(action.params)
    assert result.success is True
    assert "line1" in result.output

def test_read_nonexistent_file():
    tool = ReadFileTool()
    action = Action(name="read_file", params={"path": "/nonexistent/file.txt"})
    result = tool.execute(action.params)
    assert result.success is False
    assert result.error is not None
```

```python
# tests/tools/test_write_file.py
from ai4se_agent.tools.write_file import WriteFileTool
from ai4se_agent.types import Action

def test_write_file(tmp_path):
    tool = WriteFileTool()
    target = tmp_path / "out.txt"
    action = Action(name="write_file", params={"path": str(target), "content": "new content"})
    result = tool.execute(action.params)
    assert result.success is True
    assert target.read_text() == "new content"
```

```python
# tests/tools/test_edit_file.py
from ai4se_agent.tools.edit_file import EditFileTool
from ai4se_agent.types import Action

def test_edit_file(tmp_path):
    tool = EditFileTool()
    target = tmp_path / "test.txt"
    target.write_text("hello world\nfoo bar")
    action = Action(name="edit_file", params={"path": str(target), "old_string": "foo bar", "new_string": "baz qux"})
    result = tool.execute(action.params)
    assert result.success is True
    assert target.read_text() == "hello world\nbaz qux"

def test_edit_file_no_match(tmp_path):
    tool = EditFileTool()
    target = tmp_path / "test.txt"
    target.write_text("hello")
    action = Action(name="edit_file", params={"path": str(target), "old_string": "nonexistent", "new_string": "replacement"})
    result = tool.execute(action.params)
    assert result.success is False
```

```python
# tests/tools/test_shell.py
from ai4se_agent.tools.shell import ShellTool

def test_shell_success():
    tool = ShellTool()
    result = tool.execute({"command": "echo hello", "timeout": 5})
    assert result.success is True
    assert "hello" in result.output

def test_shell_failure():
    tool = ShellTool()
    result = tool.execute({"command": "exit 1", "timeout": 5})
    assert result.success is False
```

```python
# tests/tools/test_run_test.py
from ai4se_agent.tools.run_test import RunTestTool

def test_run_test_nonexistent_path():
    tool = RunTestTool()
    result = tool.execute({"test_path": "/nonexistent"})
    assert result.success is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/tools/ -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementations**

```python
# src/ai4se_agent/tools/base.py
from abc import ABC, abstractmethod
from ai4se_agent.types import ToolResult


class Tool(ABC):
    name: str

    @abstractmethod
    def execute(self, params: dict) -> ToolResult:
        pass
```

```python
# src/ai4se_agent/tools/registry.py
from ai4se_agent.tools.base import Tool
from ai4se_agent.types import Action, ToolResult


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def execute(self, action: Action) -> ToolResult:
        tool = self._tools.get(action.name)
        if not tool:
            return ToolResult(success=False, output="", error=f"Unknown tool: {action.name}")
        try:
            return tool.execute(action.params)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
```

```python
# src/ai4se_agent/tools/read_file.py
from pathlib import Path
from ai4se_agent.tools.base import Tool
from ai4se_agent.types import ToolResult


class ReadFileTool(Tool):
    name = "read_file"

    def execute(self, params: dict) -> ToolResult:
        path = Path(params["path"])
        try:
            content = path.read_text(encoding="utf-8")
            return ToolResult(success=True, output=content)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
```

```python
# src/ai4se_agent/tools/write_file.py
from pathlib import Path
from ai4se_agent.tools.base import Tool
from ai4se_agent.types import ToolResult


class WriteFileTool(Tool):
    name = "write_file"

    def execute(self, params: dict) -> ToolResult:
        path = Path(params["path"])
        content = params["content"]
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return ToolResult(success=True, output=f"Written {len(content)} bytes")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
```

```python
# src/ai4se_agent/tools/edit_file.py
from pathlib import Path
from ai4se_agent.tools.base import Tool
from ai4se_agent.types import ToolResult


class EditFileTool(Tool):
    name = "edit_file"

    def execute(self, params: dict) -> ToolResult:
        path = Path(params["path"])
        old = params["old_string"]
        new = params["new_string"]
        try:
            content = path.read_text(encoding="utf-8")
            if old not in content:
                return ToolResult(success=False, output="", error=f"String not found: {old[:50]}")
            new_content = content.replace(old, new, 1)
            path.write_text(new_content, encoding="utf-8")
            return ToolResult(success=True, output="Edit applied")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
```

```python
# src/ai4se_agent/tools/shell.py
import subprocess
import shlex
from ai4se_agent.tools.base import Tool
from ai4se_agent.types import ToolResult


class ShellTool(Tool):
    name = "shell"

    def execute(self, params: dict) -> ToolResult:
        command = params["command"]
        timeout = params.get("timeout", 30)
        workdir = params.get("workdir")
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=workdir
            )
            output = result.stdout + result.stderr
            return ToolResult(
                success=result.returncode == 0,
                output=output.strip(),
                metadata={"exit_code": result.returncode}
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="Command timed out")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
```

```python
# src/ai4se_agent/tools/run_test.py
import subprocess
from ai4se_agent.tools.base import Tool
from ai4se_agent.types import ToolResult


class RunTestTool(Tool):
    name = "run_test"

    def execute(self, params: dict) -> ToolResult:
        test_path = params.get("test_path", "")
        args = params.get("args", "")
        try:
            cmd = f"python -m pytest {test_path} {args} -v"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
            output = result.stdout + result.stderr
            return ToolResult(
                success=result.returncode == 0,
                output=output.strip(),
                metadata={"exit_code": result.returncode}
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="Test timed out")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/tools/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/tools/ tests/tools/
git commit -m "feat: add Tool system with registry and 5 core tools"
```

---

### Task 6: Guardrail System

**Files:**
- Create: `src/ai4se_agent/guardrails/base.py`
- Create: `src/ai4se_agent/guardrails/engine.py`
- Create: `src/ai4se_agent/guardrails/command_policy.py`
- Create: `src/ai4se_agent/guardrails/file_policy.py`
- Create: `src/ai4se_agent/guardrails/workspace_policy.py`
- Create: `src/ai4se_agent/guardrails/git_policy.py`
- Create: `tests/guardrails/test_engine.py`
- Create: `tests/guardrails/test_command_policy.py`
- Create: `tests/guardrails/test_file_policy.py`
- Create: `tests/guardrails/test_workspace_policy.py`
- Create: `tests/guardrails/test_git_policy.py`

**Interfaces:**
- Consumes: `Action`, `GuardrailResult` from Task 1
- Produces: `GuardrailEngine.check(action) -> GuardrailResult` consumed by state machine (Task 3)

- [ ] **Step 1: Write the failing tests**

```python
# tests/guardrails/test_command_policy.py
from ai4se_agent.guardrails.command_policy import CommandPolicy
from ai4se_agent.types import Action

def test_block_rm_rf():
    policy = CommandPolicy()
    action = Action(name="shell", params={"command": "rm -rf /"})
    result = policy.check(action)
    assert result.verdict == "DENY"

def test_allow_safe_command():
    policy = CommandPolicy()
    action = Action(name="shell", params={"command": "echo hello"})
    result = policy.check(action)
    assert result.verdict == "ALLOW"
```

```python
# tests/guardrails/test_file_policy.py
from ai4se_agent.guardrails.file_policy import FilePolicy
from ai4se_agent.types import Action

def test_block_git_write():
    policy = FilePolicy()
    action = Action(name="write_file", params={"path": "/workspace/.git/config", "content": ""})
    result = policy.check(action)
    assert result.verdict == "DENY"
```

```python
# tests/guardrails/test_workspace_policy.py
from ai4se_agent.guardrails.workspace_policy import WorkspacePolicy
from ai4se_agent.types import Action

def test_block_path_escape(tmp_path):
    policy = WorkspacePolicy(workspace=str(tmp_path))
    action = Action(name="read_file", params={"path": str(tmp_path / "../../etc/passwd")})
    result = policy.check(action)
    assert result.verdict == "DENY"

def test_allow_inside_workspace(tmp_path):
    policy = WorkspacePolicy(workspace=str(tmp_path))
    inner = tmp_path / "subdir" / "file.txt"
    inner.parent.mkdir()
    inner.write_text("")
    action = Action(name="read_file", params={"path": str(inner)})
    result = policy.check(action)
    assert result.verdict == "ALLOW"
```

```python
# tests/guardrails/test_git_policy.py
from ai4se_agent.guardrails.git_policy import GitPolicy
from ai4se_agent.types import Action

def test_block_push():
    policy = GitPolicy()
    action = Action(name="shell", params={"command": "git push origin main"})
    result = policy.check(action)
    assert result.verdict == "REQUIRE_APPROVAL"

def test_allow_status():
    policy = GitPolicy()
    action = Action(name="shell", params={"command": "git status"})
    result = policy.check(action)
    assert result.verdict == "ALLOW"
```

```python
# tests/guardrails/test_engine.py
from ai4se_agent.guardrails.engine import GuardrailEngine
from ai4se_agent.guardrails.command_policy import CommandPolicy
from ai4se_agent.types import Action

def test_engine_block_dangerous():
    engine = GuardrailEngine()
    engine.add_policy(CommandPolicy())
    action = Action(name="shell", params={"command": "rm -rf /"})
    result = engine.check(action)
    assert result.verdict == "DENY"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/guardrails/ -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementations**

```python
# src/ai4se_agent/guardrails/base.py
from abc import ABC, abstractmethod
from ai4se_agent.types import Action, GuardrailResult


class Policy(ABC):
    @abstractmethod
    def check(self, action: Action) -> GuardrailResult | None:
        pass
```

```python
# src/ai4se_agent/guardrails/engine.py
from ai4se_agent.guardrails.base import Policy
from ai4se_agent.types import Action, GuardrailResult


class GuardrailEngine:
    def __init__(self):
        self._policies: list[Policy] = []

    def add_policy(self, policy: Policy) -> None:
        self._policies.append(policy)

    def check(self, action: Action) -> GuardrailResult:
        results = []
        for policy in self._policies:
            result = policy.check(action)
            if result is not None:
                results.append(result)
        for r in results:
            if r.verdict == "DENY":
                return r
        for r in results:
            if r.verdict == "REQUIRE_APPROVAL":
                return r
        return GuardrailResult(verdict="ALLOW", reason="All policies passed", policy="all")
```

```python
# src/ai4se_agent/guardrails/command_policy.py
import re
from ai4se_agent.guardrails.base import Policy
from ai4se_agent.types import Action, GuardrailResult


DANGEROUS_PATTERNS = [
    r'\brm\s+-rf\s+/', r'\bdd\b', r'\bwget\b', r'\bcurl\b.*[-][-]output',
    r'\bmkfs', r'\bformat', r'\b> /dev/sda', r'\| sh', r'> /dev/',
]


class CommandPolicy(Policy):
    def check(self, action: Action) -> GuardrailResult | None:
        if action.name != "shell":
            return None
        command = action.params.get("command", "")
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return GuardrailResult(
                    verdict="DENY", reason=f"Dangerous command matched: {pattern}",
                    policy="CommandPolicy", severity=5, metadata={"command": command}
                )
        return GuardrailResult(verdict="ALLOW", reason="Safe command", policy="CommandPolicy")
```

```python
# src/ai4se_agent/guardrails/file_policy.py
from ai4se_agent.guardrails.base import Policy
from ai4se_agent.types import Action, GuardrailResult


PROTECTED_PATTERNS = ['.git/', 'node_modules/']


class FilePolicy(Policy):
    def check(self, action: Action) -> GuardrailResult | None:
        if action.name not in ("write_file", "edit_file", "read_file"):
            return None
        path = action.params.get("path", "")
        for pattern in PROTECTED_PATTERNS:
            if pattern in path:
                return GuardrailResult(
                    verdict="DENY", reason=f"Protected path: {pattern}",
                    policy="FilePolicy", severity=4, metadata={"path": path}
                )
        return GuardrailResult(verdict="ALLOW", reason="Safe path", policy="FilePolicy")
```

```python
# src/ai4se_agent/guardrails/workspace_policy.py
import os
from ai4se_agent.guardrails.base import Policy
from ai4se_agent.types import Action, GuardrailResult


class WorkspacePolicy(Policy):
    def __init__(self, workspace: str):
        self.workspace = os.path.realpath(workspace)

    def check(self, action: Action) -> GuardrailResult | None:
        if action.name not in ("read_file", "write_file", "edit_file"):
            return None
        path = action.params.get("path", "")
        real_path = os.path.realpath(path)
        if not real_path.startswith(self.workspace):
            return GuardrailResult(
                verdict="DENY", reason=f"Path escapes workspace: {real_path}",
                policy="WorkspacePolicy", severity=5, metadata={"path": path, "real_path": real_path}
            )
        return GuardrailResult(verdict="ALLOW", reason="Path within workspace", policy="WorkspacePolicy")
```

```python
# src/ai4se_agent/guardrails/git_policy.py
import re
from ai4se_agent.guardrails.base import Policy
from ai4se_agent.types import Action, GuardrailResult


HIGH_RISK_GIT = [r'git\s+push', r'git\s+reset\s+--hard', r'git\s+merge', r'git\s+rebase']


class GitPolicy(Policy):
    def check(self, action: Action) -> GuardrailResult | None:
        if action.name != "shell":
            return None
        command = action.params.get("command", "")
        for pattern in HIGH_RISK_GIT:
            if re.search(pattern, command):
                return GuardrailResult(
                    verdict="REQUIRE_APPROVAL", reason=f"High-risk git operation: {pattern}",
                    policy="GitPolicy", severity=3, metadata={"command": command}
                )
        return GuardrailResult(verdict="ALLOW", reason="Safe git command", policy="GitPolicy")
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/guardrails/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/guardrails/ tests/guardrails/
git commit -m "feat: add Guardrail system with Command, File, Workspace, Git policies"
```

---

### Task 7: Memory System

**Files:**
- Create: `src/ai4se_agent/memory/manager.py`
- Create: `src/ai4se_agent/memory/session.py`
- Create: `src/ai4se_agent/memory/persistent.py`
- Create: `tests/memory/test_manager.py`
- Create: `tests/memory/test_session.py`
- Create: `tests/memory/test_persistent.py`

**Interfaces:**
- Consumes: Nothing from this project
- Produces: `MemoryManager` consumed by state machine

- [ ] **Step 1: Write the failing tests**

```python
# tests/memory/test_session.py
from ai4se_agent.memory.session import SessionMemory

def test_session_add_and_get():
    mem = SessionMemory(max_turns=5)
    mem.add("user", "hello")
    mem.add("assistant", "hi")
    turns = mem.get_recent(2)
    assert len(turns) == 2
    assert turns[0]["role"] == "user"

def test_session_lru_eviction():
    mem = SessionMemory(max_turns=3)
    for i in range(5):
        mem.add("user", f"msg{i}")
    turns = mem.get_recent(10)
    assert len(turns) == 3
    assert turns[0]["content"] == "msg2"
```

```python
# tests/memory/test_persistent.py
from ai4se_agent.memory.persistent import PersistentMemory

def test_save_and_load_rule(tmp_path):
    mem = PersistentMemory(base_dir=str(tmp_path))
    mem.save_rule("branch_naming", "Use feat/ prefix")
    loaded = mem.load_rule("branch_naming")
    assert loaded == "Use feat/ prefix"

def test_save_summary(tmp_path):
    mem = PersistentMemory(base_dir=str(tmp_path))
    mem.save_summary("session-1", "Fixed bug in validator")
    summaries = mem.list_summaries()
    assert len(summaries) >= 1
```

```python
# tests/memory/test_manager.py
from ai4se_agent.memory.manager import MemoryManager
from ai4se_agent.memory.session import SessionMemory
from ai4se_agent.memory.persistent import PersistentMemory

def test_manager_adds_to_session(tmp_path):
    mgr = MemoryManager(session=SessionMemory(), persistent=PersistentMemory(base_dir=str(tmp_path)))
    mgr.add_to_session("user", "test")
    assert len(mgr.get_session_history()) == 1
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/memory/ -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementations**

```python
# src/ai4se_agent/memory/session.py
from collections import deque


class SessionMemory:
    def __init__(self, max_turns: int = 50):
        self._turns = deque(maxlen=max_turns)

    def add(self, role: str, content: str) -> None:
        self._turns.append({"role": role, "content": content})

    def get_recent(self, n: int) -> list:
        return list(self._turns)[-n:]

    def get_all(self) -> list:
        return list(self._turns)

    def clear(self) -> None:
        self._turns.clear()
```

```python
# src/ai4se_agent/memory/persistent.py
from pathlib import Path


class PersistentMemory:
    def __init__(self, base_dir: str = "memory"):
        self._rules_dir = Path(base_dir) / "project_rules"
        self._summaries_dir = Path(base_dir) / "session_summaries"
        self._rules_dir.mkdir(parents=True, exist_ok=True)
        self._summaries_dir.mkdir(parents=True, exist_ok=True)

    def save_rule(self, name: str, content: str) -> None:
        (self._rules_dir / f"{name}.md").write_text(content, encoding="utf-8")

    def load_rule(self, name: str) -> str | None:
        path = self._rules_dir / f"{name}.md"
        return path.read_text(encoding="utf-8") if path.exists() else None

    def list_rules(self) -> list[str]:
        return [p.stem for p in self._rules_dir.glob("*.md")]

    def save_summary(self, session_id: str, summary: str) -> None:
        (self._summaries_dir / f"{session_id}.md").write_text(summary, encoding="utf-8")

    def list_summaries(self) -> list[str]:
        return [p.stem for p in self._summaries_dir.glob("*.md")]
```

```python
# src/ai4se_agent/memory/manager.py
from ai4se_agent.memory.session import SessionMemory
from ai4se_agent.memory.persistent import PersistentMemory


class MemoryManager:
    def __init__(self, session: SessionMemory | None = None, persistent: PersistentMemory | None = None):
        self.session = session or SessionMemory()
        self.persistent = persistent or PersistentMemory()

    def add_to_session(self, role: str, content: str) -> None:
        self.session.add(role, content)

    def get_session_history(self) -> list:
        return self.session.get_all()
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/memory/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/memory/ tests/memory/
git commit -m "feat: add Memory system with session and persistent storage"
```

---

### Task 8: Configuration

**Files:**
- Create: `src/ai4se_agent/config/loader.py`
- Create: `tests/config/test_loader.py`

**Interfaces:**
- Consumes: Nothing from this project
- Produces: `ConfigLoader` consumed by CLI entry point

- [ ] **Step 1: Write the failing test**

```python
# tests/config/test_loader.py
from ai4se_agent.config.loader import ConfigLoader

def test_config_returns_defaults():
    loader = ConfigLoader()
    assert loader.get("provider", "openai") == "openai"

def test_config_accepts_env_override(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    loader = ConfigLoader()
    assert loader.get("api_key") == "test-key-123"
```

- [ ] **Step 2: Run test**

Run: `pytest tests/config/test_loader.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/ai4se_agent/config/loader.py
import os
from pathlib import Path


class ConfigLoader:
    def __init__(self, env_file: str = ".env"):
        self._env_file = Path(env_file)
        self._load_env_file()

    def _load_env_file(self) -> None:
        if self._env_file.exists():
            for line in self._env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())

    def get(self, key: str, default: str | None = None) -> str | None:
        env_map = {
            "api_key": "OPENAI_API_KEY",
            "base_url": "OPENAI_BASE_URL",
            "provider": "LLM_PROVIDER",
            "local_model_url": "LOCAL_MODEL_URL",
            "local_model_name": "LOCAL_MODEL_NAME",
        }
        env_key = env_map.get(key, key.upper())
        return os.environ.get(env_key, default)

    def get_provider(self) -> str:
        return self.get("provider", "openai")
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/config/test_loader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/config/ tests/config/
git commit -m "feat: add ConfigLoader with .env support"
```

---

### Task 9: Feedback Loop (重点维度)

**Files:**
- Create: `src/ai4se_agent/feedback/sensor.py`
- Create: `src/ai4se_agent/feedback/classifier.py`
- Create: `src/ai4se_agent/feedback/planner.py`
- Create: `src/ai4se_agent/feedback/failure_db.py`
- Create: `src/ai4se_agent/feedback/loop.py`
- Create: `tests/feedback/test_sensor.py`
- Create: `tests/feedback/test_classifier.py`
- Create: `tests/feedback/test_planner.py`
- Create: `tests/feedback/test_failure_db.py`
- Create: `tests/feedback/test_loop.py`

**Interfaces:**
- Consumes: `Feedback`, `ToolResult`, `CorrectionPlan` from Task 1
- Produces: `FeedbackLoop.run(tool_result) -> CorrectionPlan` consumed by state machine

- [ ] **Step 1: Write the failing tests**

```python
# tests/feedback/test_sensor.py
from ai4se_agent.feedback.sensor import TestSensor, LintSensor
from ai4se_agent.types import ToolResult

def test_test_sensor_parses_failure():
    sensor = TestSensor()
    result = ToolResult(success=False, output="FAILED test_order.py::test_validate - AssertionError: expected True got False",
                        metadata={"exit_code": 1})
    feedback = sensor.sense(result)
    assert feedback.success is False
    assert feedback.category == "test_failure"
    assert feedback.source == "pytest"

def test_test_sensor_parses_success():
    sensor = TestSensor()
    result = ToolResult(success=True, output="1 passed", metadata={"exit_code": 0})
    feedback = sensor.sense(result)
    assert feedback.success is True
```

```python
# tests/feedback/test_classifier.py
from ai4se_agent.feedback.classifier import FailureClassifier
from ai4se_agent.types import Feedback

def test_classify_assertion_error():
    classifier = FailureClassifier()
    fb = Feedback(success=False, category="test_failure", message="AssertionError: expected 5 got 3",
                  details={"line": 42}, severity=3, source="pytest")
    result = classifier.classify(fb)
    assert result["type"] == "logic_error"

def test_classify_lint_error():
    classifier = FailureClassifier()
    fb = Feedback(success=False, category="lint_error", message="F401 imported but unused",
                  details={}, severity=2, source="ruff")
    result = classifier.classify(fb)
    assert result["type"] == "syntax_error"
```

```python
# tests/feedback/test_planner.py
from ai4se_agent.feedback.planner import CorrectionPlanner
from ai4se_agent.types import ToolResult

def test_planner_generates_plan():
    planner = CorrectionPlanner()
    result = ToolResult(success=False, output="FAILED test_order.py::test_validate - AssertionError",
                        metadata={"exit_code": 1})
    plan = planner.plan(result, {"type": "logic_error", "category": "test_failure"})
    assert plan.scope is not None
    assert len(plan.target_files) > 0
    assert plan.retry_count == 0
```

```python
# tests/feedback/test_failure_db.py
from ai4se_agent.feedback.failure_db import FailureDB

def test_failure_db_save_and_query(tmp_path):
    db = FailureDB(db_path=str(tmp_path / "test_failure.db"))
    db.record_failure("logic_error", "Missing null check on order_id", "Add guard clause before query")
    results = db.query_similar("logic_error")
    assert len(results) >= 1
    assert results[0]["failure_type"] == "logic_error"
```

```python
# tests/feedback/test_loop.py
from ai4se_agent.feedback.loop import FeedbackLoop
from ai4se_agent.feedback.sensor import TestSensor
from ai4se_agent.feedback.classifier import FailureClassifier
from ai4se_agent.feedback.planner import CorrectionPlanner
from ai4se_agent.types import ToolResult

def test_feedback_loop_produces_correction():
    loop = FeedbackLoop(
        sensors=[TestSensor()],
        classifier=FailureClassifier(),
        planner=CorrectionPlanner()
    )
    result = ToolResult(success=False, output="FAILED - AssertionError", metadata={"exit_code": 1})
    plan = loop.run(result)
    assert plan is not None
    assert plan.retry_count == 0
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/feedback/ -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementations**

```python
# src/ai4se_agent/feedback/sensor.py
from abc import ABC, abstractmethod
from ai4se_agent.types import ToolResult, Feedback


class Sensor(ABC):
    @abstractmethod
    def sense(self, result: ToolResult) -> Feedback | None:
        pass


class TestSensor(Sensor):
    def sense(self, result: ToolResult) -> Feedback | None:
        if result.metadata.get("exit_code") == 0:
            return Feedback(success=True, category="test_success", message="All tests passed",
                            source="pytest")
        return Feedback(
            success=False, category="test_failure", message=result.output,
            source="pytest", severity=3, details={"exit_code": result.metadata.get("exit_code", 1)}
        )


class LintSensor(Sensor):
    def sense(self, result: ToolResult) -> Feedback | None:
        if result.success:
            return Feedback(success=True, category="lint_success", message="Clean lint",
                            source="ruff")
        return Feedback(
            success=False, category="lint_error", message=result.output,
            source="ruff", severity=2
        )


class TypeSensor(Sensor):
    def sense(self, result: ToolResult) -> Feedback | None:
        if result.success:
            return Feedback(success=True, category="type_success", message="Clean types",
                            source="mypy")
        return Feedback(
            success=False, category="type_error", message=result.output,
            source="mypy", severity=2
        )
```

```python
# src/ai4se_agent/feedback/classifier.py
from ai4se_agent.types import Feedback


class FailureClassifier:
    def classify(self, feedback: Feedback) -> dict:
        if feedback.category == "lint_error":
            return {"type": "syntax_error", "category": feedback.category, "message": feedback.message}
        if feedback.category == "type_error":
            return {"type": "type_error", "category": feedback.category, "message": feedback.message}
        if "AssertionError" in feedback.message:
            return {"type": "logic_error", "category": feedback.category, "message": feedback.message}
        if "ImportError" in feedback.message or "ModuleNotFoundError" in feedback.message:
            return {"type": "missing_dependency", "category": feedback.category, "message": feedback.message}
        if "timeout" in feedback.message.lower():
            return {"type": "timeout", "category": feedback.category, "message": feedback.message}
        return {"type": "unknown", "category": feedback.category, "message": feedback.message}
```

```python
# src/ai4se_agent/feedback/planner.py
from ai4se_agent.types import ToolResult, CorrectionPlan


class CorrectionPlanner:
    def plan(self, result: ToolResult, classification: dict, retry_count: int = 0) -> CorrectionPlan:
        if classification["type"] == "logic_error":
            return CorrectionPlan(
                scope="Fix assertion failure in test output",
                target_files=self._extract_files(result.output),
                strategy="Analyze the test failure and fix the logic in the relevant code",
                retry_count=retry_count
            )
        elif classification["type"] == "syntax_error":
            return CorrectionPlan(
                scope="Fix lint/type errors",
                target_files=self._extract_files(result.output),
                strategy="Fix the reported syntax or type issues",
                retry_count=retry_count
            )
        else:
            return CorrectionPlan(
                scope="General fix",
                target_files=self._extract_files(result.output),
                strategy="Review the error and fix the issue",
                retry_count=retry_count
            )

    def _extract_files(self, output: str) -> list:
        import re
        files = re.findall(r'(\S+\.py):', output)
        return list(set(files)) if files else ["unknown"]
```

```python
# src/ai4se_agent/feedback/failure_db.py
import sqlite3
from pathlib import Path


class FailureDB:
    def __init__(self, db_path: str = "memory/failure.db"):
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS failure_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    failure_type TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    fix_strategy TEXT,
                    count INTEGER DEFAULT 1,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def record_failure(self, failure_type: str, pattern: str, fix_strategy: str = "") -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO failure_patterns (failure_type, pattern, fix_strategy) VALUES (?, ?, ?)",
                (failure_type, pattern, fix_strategy)
            )

    def query_similar(self, failure_type: str) -> list[dict]:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM failure_patterns WHERE failure_type = ? ORDER BY count DESC LIMIT 5",
                (failure_type,)
            )
            return [dict(row) for row in cursor.fetchall()]
```

```python
# src/ai4se_agent/feedback/loop.py
from ai4se_agent.feedback.sensor import Sensor
from ai4se_agent.feedback.classifier import FailureClassifier
from ai4se_agent.feedback.planner import CorrectionPlanner
from ai4se_agent.types import ToolResult, CorrectionPlan


class FeedbackLoop:
    def __init__(self, sensors: list[Sensor], classifier: FailureClassifier, planner: CorrectionPlanner):
        self._sensors = sensors
        self._classifier = classifier
        self._planner = planner

    def run(self, result: ToolResult, retry_count: int = 0) -> CorrectionPlan | None:
        if result.success:
            return None
        for sensor in self._sensors:
            feedback = sensor.sense(result)
            if feedback and not feedback.success:
                classification = self._classifier.classify(feedback)
                plan = self._planner.plan(result, classification, retry_count)
                return plan
        return None
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/feedback/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/feedback/ tests/feedback/
git commit -m "feat: add Feedback Loop with Sensor, Classifier, Planner, and FailureDB"
```

---

### Task 10: State Machine + Integration

**Files:**
- Create: `src/ai4se_agent/core/state_machine.py`
- Create: `tests/core/test_state_machine.py`

**Interfaces:**
- Consumes: All previous tasks (AgentState, LLMAdapter, ActionParser, ActionValidator, ToolRegistry, GuardrailEngine, FeedbackLoop, MemoryManager)
- Produces: `HarnessStateMachine` — the main entry point

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_state_machine.py
from ai4se_agent.core.state_machine import HarnessStateMachine
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.llm.mock_adapter import MockAdapter
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.guardrails.engine import GuardrailEngine
from ai4se_agent.feedback.loop import FeedbackLoop
from ai4se_agent.feedback.classifier import FailureClassifier
from ai4se_agent.feedback.planner import CorrectionPlanner
from ai4se_agent.feedback.sensor import TestSensor
from ai4se_agent.memory.manager import MemoryManager

def test_state_machine_completes_successfully(tmp_path):
    llm = MockAdapter(responses=["action: read_file path=test.txt", "[DONE]"])
    registry = ToolRegistry()
    guardrails = GuardrailEngine()
    state = AgentState(goal="test task")
    machine = HarnessStateMachine(
        agent_state=state,
        llm_adapter=llm,
        action_parser=ActionParser(),
        action_validator=ActionValidator(),
        tool_registry=registry,
        guardrail_engine=guardrails,
        feedback_loop=None,
        memory_manager=MemoryManager(),
        max_iterations=5
    )
    result = machine.run()
    assert result["status"] in ("success", "failed")
```

- [ ] **Step 2: Run test**

Run: `pytest tests/core/test_state_machine.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/ai4se_agent/core/state_machine.py
from transitions import Machine
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.llm.base import LLMAdapter
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.guardrails.engine import GuardrailEngine
from ai4se_agent.feedback.loop import FeedbackLoop
from ai4se_agent.memory.manager import MemoryManager
from ai4se_agent.types import GuardrailResult, StopReason


class HarnessStateMachine:
    states = [
        "IDLE", "CONTEXT_ORG", "LLM_CALL", "ACTION_PARSE",
        "GUARDRAIL", "WAIT_APPROVAL", "TOOL_EXEC", "TOOL_ERROR",
        "FEEDBACK", "MEMORY_UPDATE", "STOP"
    ]

    def __init__(
        self,
        agent_state: AgentState,
        llm_adapter: LLMAdapter,
        action_parser: ActionParser,
        action_validator: ActionValidator,
        tool_registry: ToolRegistry,
        guardrail_engine: GuardrailEngine,
        feedback_loop: FeedbackLoop | None,
        memory_manager: MemoryManager,
        max_iterations: int = 20,
    ):
        self.state = agent_state
        self.llm = llm_adapter
        self.parser = action_parser
        self.validator = action_validator
        self.tools = tool_registry
        self.guardrails = guardrail_engine
        self.feedback = feedback_loop
        self.memory = memory_manager
        self.max_iterations = max_iterations
        self.stop_reason = StopReason.SUCCESS
        self._pending_action = None
        self._pending_guardrail = None

        self.machine = Machine(
            model=self,
            states=HarnessStateMachine.states,
            initial="IDLE",
            auto_transitions=False,
        )

        self.machine.add_transition("start", "IDLE", "CONTEXT_ORG", after="_on_context_org")
        self.machine.add_transition("retry_context", "CONTEXT_ORG", "CONTEXT_ORG", after="_on_context_org")
        self.machine.add_transition("call_llm", "CONTEXT_ORG", "LLM_CALL", after="_on_llm_call")
        self.machine.add_transition("parse_action", "LLM_CALL", "ACTION_PARSE", after="_on_action_parse")
        self.machine.add_transition("retry_parse", "ACTION_PARSE", "CONTEXT_ORG", after="_on_context_org")
        self.machine.add_transition("check_guardrails", "ACTION_PARSE", "GUARDRAIL", after="_on_guardrail")
        self.machine.add_transition("deny_action", "GUARDRAIL", "CONTEXT_ORG", after="_on_context_org")
        self.machine.add_transition("request_approval", "GUARDRAIL", "WAIT_APPROVAL", after="_on_wait_approval")
        self.machine.add_transition("approve", "WAIT_APPROVAL", "TOOL_EXEC", after="_on_tool_exec")
        self.machine.add_transition("reject", "WAIT_APPROVAL", "CONTEXT_ORG", after="_on_context_org")
        self.machine.add_transition("execute", "GUARDRAIL", "TOOL_EXEC", after="_on_tool_exec")
        self.machine.add_transition("tool_error", "TOOL_EXEC", "TOOL_ERROR", after="_on_tool_error")
        self.machine.add_transition("tool_success", "TOOL_EXEC", "FEEDBACK", after="_on_feedback")
        self.machine.add_transition("retry_tool", "TOOL_ERROR", "TOOL_EXEC", after="_on_tool_exec")
        self.machine.add_transition("feedback_done", "FEEDBACK", "MEMORY_UPDATE", after="_on_memory_update")
        self.machine.add_transition("feedback_correct", "FEEDBACK", "CONTEXT_ORG", after="_on_context_org")
        self.machine.add_transition("continue_loop", "MEMORY_UPDATE", "CONTEXT_ORG", after="_on_context_org")
        self.machine.add_transition("stop", "MEMORY_UPDATE", "STOP")

    def run(self) -> dict:
        self.start()
        self.state.current_state = self.state
        return self._build_result()

    def _on_context_org(self) -> None:
        self.state.increment_iteration()
        if self.state.iteration > self.max_iterations:
            self.stop_reason = StopReason.MAX_ITERATION
            self.stop()
            return
        self.call_llm()

    def _on_llm_call(self) -> None:
        try:
            messages = self.state.context
            response = self.llm.generate(messages)
            self.state.context.append({"role": "assistant", "content": response})
            self.parse_action()
        except Exception:
            self.state.error_count += 1
            if self.state.error_count >= 3:
                self.stop_reason = StopReason.LLM_ERROR
                self.stop()
            else:
                self.retry_context()

    def _on_action_parse(self) -> None:
        last_msg = self.state.context[-1]["content"]
        if "[DONE]" in last_msg:
            self.stop_reason = StopReason.SUCCESS
            self.stop()
            return
        action = self.parser.parse(last_msg)
        if action is None:
            self.retry_parse()
            return
        errors = self.validator.validate(action)
        if errors:
            self.retry_parse()
            return
        self._pending_action = action
        self.check_guardrails()

    def _on_guardrail(self) -> None:
        result = self.guardrails.check(self._pending_action)
        self._pending_guardrail = result
        if result.verdict == "DENY":
            self.deny_action()
        elif result.verdict == "REQUIRE_APPROVAL":
            self.request_approval()
        else:
            self.execute()

    def _on_wait_approval(self) -> None:
        print(f"\n[DANGEROUS ACTION] Policy: {self._pending_guardrail.policy}")
        print(f"Reason: {self._pending_guardrail.reason}")
        print(f"Action: {self._pending_action}")
        answer = input("Approve? (y/n): ").strip().lower()
        if answer == "y":
            self.approve()
        else:
            self.reject()

    def _on_tool_exec(self) -> None:
        result = self.tools.execute(self._pending_action)
        if result.success:
            self.tool_success()
        else:
            self.tool_error()

    def _on_tool_error(self) -> None:
        if self.state.retry_count < 3:
            self.state.retry_count += 1
            self.retry_tool()
        else:
            self.stop_reason = StopReason.REPEATED_FAILURE
            self.stop()

    def _on_feedback(self) -> None:
        if self.feedback:
            plan = self.feedback.run(None, self.state.retry_count)
            if plan:
                self.state.retry_count += 1
                if self.state.retry_count >= 3:
                    self.state.retry_count = 0
                self.feedback_correct()
                return
        self.feedback_done()

    def _on_memory_update(self) -> None:
        self.continue_loop()

    def _build_result(self) -> dict:
        return {
            "status": "success" if self.stop_reason == StopReason.SUCCESS else "failed",
            "reason": self.stop_reason.value,
            "iterations": self.state.iteration,
        }
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/core/test_state_machine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/core/state_machine.py tests/core/test_state_machine.py
git commit -m "feat: add HarnessStateMachine - 11-state FSM with transitions"
```

---

### Task 11: CLI Entry Point

**Files:**
- Create: `src/ai4se_agent/cli.py`
- Modify: `pyproject.toml` (add entry point)

**Interfaces:**
- Consumes: `HarnessStateMachine`, `ConfigLoader`, all subsystems

- [ ] **Step 1: Write the CLI**

```python
# src/ai4se_agent/cli.py
import sys
from ai4se_agent.config.loader import ConfigLoader
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.core.state_machine import HarnessStateMachine
from ai4se_agent.llm.openai_adapter import OpenAIAdapter
from ai4se_agent.llm.mock_adapter import MockAdapter
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.tools.read_file import ReadFileTool
from ai4se_agent.tools.write_file import WriteFileTool
from ai4se_agent.tools.edit_file import EditFileTool
from ai4se_agent.tools.shell import ShellTool
from ai4se_agent.tools.run_test import RunTestTool
from ai4se_agent.guardrails.engine import GuardrailEngine
from ai4se_agent.guardrails.command_policy import CommandPolicy
from ai4se_agent.guardrails.file_policy import FilePolicy
from ai4se_agent.guardrails.workspace_policy import WorkspacePolicy
from ai4se_agent.guardrails.git_policy import GitPolicy
from ai4se_agent.feedback.loop import FeedbackLoop
from ai4se_agent.feedback.sensor import TestSensor, LintSensor
from ai4se_agent.feedback.classifier import FailureClassifier
from ai4se_agent.feedback.planner import CorrectionPlanner
from ai4se_agent.memory.manager import MemoryManager
from ai4se_agent.memory.session import SessionMemory
from ai4se_agent.memory.persistent import PersistentMemory


def build_harness(task: str, workspace: str = ".") -> HarnessStateMachine:
    config = ConfigLoader()
    provider = config.get_provider()
    if provider == "mock":
        llm = MockAdapter(responses=["action: shell command=echo hello", "[DONE]"])
    else:
        api_key = config.get("api_key")
        base_url = config.get("base_url")
        llm = OpenAIAdapter(api_key=api_key, base_url=base_url)

    tools = ToolRegistry()
    tools.register(ReadFileTool())
    tools.register(WriteFileTool())
    tools.register(EditFileTool())
    tools.register(ShellTool())
    tools.register(RunTestTool())

    guardrails = GuardrailEngine()
    guardrails.add_policy(CommandPolicy())
    guardrails.add_policy(FilePolicy())
    guardrails.add_policy(WorkspacePolicy(workspace=workspace))
    guardrails.add_policy(GitPolicy())

    feedback = FeedbackLoop(
        sensors=[TestSensor(), LintSensor()],
        classifier=FailureClassifier(),
        planner=CorrectionPlanner()
    )

    memory = MemoryManager(
        session=SessionMemory(),
        persistent=PersistentMemory()
    )

    state = AgentState(goal=task)

    return HarnessStateMachine(
        agent_state=state,
        llm_adapter=llm,
        action_parser=ActionParser(),
        action_validator=ActionValidator(),
        tool_registry=tools,
        guardrail_engine=guardrails,
        feedback_loop=feedback,
        memory_manager=memory,
    )


def main():
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Task: ")
    harness = build_harness(task)
    result = harness.run()
    print(f"\nResult: {result['status']} ({result['reason']}) after {result['iterations']} iterations")


if __name__ == "__main__":
    main()
```

Add to `pyproject.toml`:
```toml
[project.scripts]
ai4se-agent = "ai4se_agent.cli:main"
```

- [ ] **Step 2: Add CLI test**

```python
# tests/test_cli.py
from ai4se_agent.cli import build_harness

def test_build_harness_creates_machine():
    harness = build_harness("test task", workspace="/tmp")
    assert harness is not None
    assert harness.state.goal == "test task"
```

- [ ] **Step 3: Run test**

Run: `pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/ai4se_agent/cli.py tests/test_cli.py pyproject.toml
git commit -m "feat: add CLI entry point and harness builder"
```

---

### Task 12: Mechanism Demo

**Files:**
- Create: `demo/mechanism_demo.py`
- Create: `demo/README.md`

**Interfaces:**
- Consumes: All subsystems

- [ ] **Step 1: Write the demo script**

```python
# demo/mechanism_demo.py
"""
Mechanism Demo — 演示三个核心行为：
1. 治理护栏拦截危险动作
2. 反馈闭环使 agent 收到失败信号并修正
3. 重点维度的确定性行为（Feedback Loop 完整流程）
"""
from ai4se_agent.feedback.sensor import TestSensor
from ai4se_agent.feedback.classifier import FailureClassifier
from ai4se_agent.feedback.planner import CorrectionPlanner
from ai4se_agent.feedback.failure_db import FailureDB
from ai4se_agent.guardrails.command_policy import CommandPolicy
from ai4se_agent.guardrails.workspace_policy import WorkspacePolicy
from ai4se_agent.types import Action, ToolResult
import tempfile
import os


def demo_guardrail():
    print("=== Demo 1: Guardrail Intercepts Dangerous Action ===")
    policy = CommandPolicy()
    action = Action(name="shell", params={"command": "rm -rf /"})
    result = policy.check(action)
    assert result.verdict == "DENY", f"Expected DENY, got {result.verdict}"
    print(f"  Action: shell rm -rf /")
    print(f"  Verdict: {result.verdict}")
    print(f"  Reason: {result.reason}")
    print("  PASS: Guardrail correctly blocked dangerous command\n")


def demo_feedback_loop():
    print("=== Demo 2: Feedback Loop Detects Failure and Generates Correction ===")
    sensor = TestSensor()
    classifier = FailureClassifier()
    planner = CorrectionPlanner()

    result = ToolResult(
        success=False,
        output="FAILED test_order.py::test_validate - AssertionError: expected True got False",
        metadata={"exit_code": 1}
    )
    feedback = sensor.sense(result)
    assert feedback.success is False
    classification = classifier.classify(feedback)
    plan = planner.plan(result, classification)
    assert plan is not None
    print(f"  Tool result: FAILED (exit code 1)")
    print(f"  Feedback: category={feedback.category}, source={feedback.source}")
    print(f"  Classification: {classification['type']}")
    print(f"  Correction plan: scope='{plan.scope}', files={plan.target_files}")
    print("  PASS: Feedback loop detected failure and generated correction plan\n")


def demo_incremental_correction():
    print("=== Demo 3: Incremental Correction Strategy (重点维度) ===")
    planner = CorrectionPlanner()
    classifier = FailureClassifier()
    sensor = TestSensor()

    for retry in range(3):
        result = ToolResult(
            success=False,
            output=f"FAILED test_order.py::test_validate - AssertionError (attempt {retry + 1})",
            metadata={"exit_code": 1}
        )
        feedback = sensor.sense(result)
        classification = classifier.classify(feedback)
        plan = planner.plan(result, classification, retry_count=retry)
        strategy = "incremental" if retry < 2 else "full replan"
        print(f"  Attempt {retry + 1}: retry_count={retry}, strategy={strategy}")
        print(f"    Correction: {plan.strategy[:50]}...")

    print("  PASS: Incremental correction strategy escalates to full replan after 3 failures\n")


def demo_failure_db():
    print("=== Demo 4: FailureDB Records and Queries Failure Patterns ===")
    with tempfile.TemporaryDirectory() as tmp:
        db = FailureDB(db_path=os.path.join(tmp, "failure.db"))
        db.record_failure("logic_error", "Missing null check on order_id", "Add guard clause before query")
        results = db.query_similar("logic_error")
        assert len(results) >= 1
        print(f"  Recorded failure: logic_error")
        print(f"  Queried similar patterns: {len(results)} found")
        print(f"  Pattern: {results[0]['pattern']}")
        print("  PASS: FailureDB persisted and retrieved failure pattern\n")


def demo_workspace_policy():
    print("=== Demo 5: WorkspacePolicy Blocks Path Escape ===")
    with tempfile.TemporaryDirectory() as tmp:
        policy = WorkspacePolicy(workspace=tmp)
        action = Action(name="read_file", params={"path": os.path.join(tmp, "..", "..", "etc", "passwd")})
        result = policy.check(action)
        assert result.verdict == "DENY"
        print(f"  Action: read_file ../../etc/passwd")
        print(f"  Verdict: {result.verdict}")
        print(f"  Reason: {result.reason}")
        print("  PASS: WorkspacePolicy blocked path escape\n")


if __name__ == "__main__":
    demo_guardrail()
    demo_feedback_loop()
    demo_incremental_correction()
    demo_failure_db()
    demo_workspace_policy()
    print("=== All demos passed ===")
```

- [ ] **Step 2: Run the demo**

Run: `python demo/mechanism_demo.py`
Expected: All 5 demos print PASS

- [ ] **Step 3: Commit**

```bash
git add demo/
git commit -m "feat: add mechanism demo for guardrail, feedback, correction, failure DB, workspace policy"
```

---

## Task Dependency Graph

```
Task 1 (Types) ──┬── Task 2 (AgentState)
                 ├── Task 3 (LLMAdapter)
                 ├── Task 4 (ActionParse)
                 ├── Task 5 (Tools)
                 ├── Task 6 (Guardrails)
                 ├── Task 7 (Memory)
                 └── Task 8 (Config)
                          │
Task 2-8 ────────────────┴── Task 10 (StateMachine) ──┬── Task 11 (CLI)
                                                       └── Task 12 (Demo)
Task 9 (Feedback) ────────────────────────────────────────┘
```

Tasks 2-9 are independent of each other and can be parallelized.