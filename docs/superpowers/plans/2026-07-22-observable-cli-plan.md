# Lightweight Observable CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lightweight observable CLI layer with interactive session, Renderer abstraction, and JSON trace logging.

**Architecture:** Add `cli/` and `observability/` modules alongside existing `core/`. StateMachine gains optional Renderer/Tracer callbacks via constructor injection. SessionManager orchestrates the interactive loop. Renderer is an ABC with TerminalRenderer (colorama) and NullRenderer (test) implementations.

**Tech Stack:** colorama (~50KB), Python standard library (json, input, shutil)

## Global Constraints

- Python >=3.10
- No `rich`, `prompt_toolkit`, or other heavy terminal UI libraries
- colorama as only new dependency (cross-platform color output)
- Renderer must be an ABC with at least NullRenderer impl for testing
- StateMachine must not know display details — only calls abstract Renderer methods
- All existing 53 tests must continue to pass
- TDD: red-green-refactor for each new component

---

## File Structure

```
src/ai4se_agent/
├── cli/
│   ├── __init__.py
│   ├── main.py          ← CLI entry point (argparse, replaces old cli.py)
│   ├── session.py       ← SessionManager (interactive loop, lifecycle)
│   ├── renderer.py      ← Renderer ABC + TerminalRenderer + NullRenderer
│   └── commands.py      ← Interactive command handlers (/status, /memory, etc.)
├── observability/
│   ├── __init__.py
│   ├── events.py        ← Event dataclasses + EventType enum
│   └── tracer.py        ← Tracer: record, save, replay
├── core/
│   └── state_machine.py ← Modified: add renderer/tracer callbacks
└── (old) cli.py         ← DELETED after migration

tests/
├── cli/
│   ├── __init__.py
│   ├── test_renderer.py
│   └── test_session.py
├── observability/
│   ├── __init__.py
│   ├── test_events.py
│   └── test_tracer.py
└── test_cli.py          ← Modified: import from cli.main instead of cli
```

---

### Task 1: Observability Layer — Events + Tracer

**Files:**
- Create: `src/ai4se_agent/observability/__init__.py`
- Create: `src/ai4se_agent/observability/events.py`
- Create: `src/ai4se_agent/observability/tracer.py`
- Create: `tests/observability/__init__.py`
- Create: `tests/observability/test_events.py`
- Create: `tests/observability/test_tracer.py`

**Interfaces:**
- Produces: `EventType` enum, `Event` dataclass, `StateEvent`, `LLMEvent`, `ActionEvent`, `ToolEvent`, `FeedbackEvent` consumed by Tracer and Renderer
- Produces: `Tracer.record(event)`, `Tracer.save(path)`, `Tracer.replay(path)` consumed by SessionManager

- [ ] **Step 1: Write the failing test**

```python
# tests/observability/test_events.py
from ai4se_agent.observability.events import EventType, Event, StateEvent, LLMEvent, ActionEvent

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
```

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/observability/ -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write minimal implementation**

```python
# src/ai4se_agent/observability/events.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(Enum):
    STATE_CHANGED = "state_changed"
    LLM_CALLED = "llm_called"
    ACTION_PARSED = "action_parsed"
    GUARDRAIL_CHECKED = "guardrail_checked"
    TOOL_EXECUTED = "tool_executed"
    FEEDBACK_RECEIVED = "feedback_received"


@dataclass
class Event:
    type: EventType
    iteration: int
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"type": self.type.value, "iteration": self.iteration, **self.data}


@dataclass
class StateEvent(Event):
    old_state: str = ""
    new_state: str = ""

    def __init__(self, iteration: int, old_state: str, new_state: str):
        super().__init__(type=EventType.STATE_CHANGED, iteration=iteration,
                         data={"old_state": old_state, "new_state": new_state})
        self.old_state = old_state
        self.new_state = new_state


@dataclass
class LLMEvent(Event):
    model: str = ""
    messages: list = field(default_factory=list)
    response: str = ""

    def __init__(self, iteration: int, model: str, messages: list, response: str):
        super().__init__(type=EventType.LLM_CALLED, iteration=iteration,
                         data={"model": model, "response": response})
        self.model = model
        self.messages = messages
        self.response = response


@dataclass
class ActionEvent(Event):
    action_name: str = ""
    action_params: dict = field(default_factory=dict)

    def __init__(self, iteration: int, action_name: str, action_params: dict):
        super().__init__(type=EventType.ACTION_PARSED, iteration=iteration,
                         data={"action_name": action_name, "action_params": action_params})
        self.action_name = action_name
        self.action_params = action_params


@dataclass
class ToolEvent(Event):
    tool: str = ""
    success: bool = True
    output: str = ""

    def __init__(self, iteration: int, tool: str, success: bool, output: str = ""):
        super().__init__(type=EventType.TOOL_EXECUTED, iteration=iteration,
                         data={"tool": tool, "success": success, "output": output[:200]})
        self.tool = tool
        self.success = success
        self.output = output


@dataclass
class FeedbackEvent(Event):
    plan_scope: str = ""
    has_plan: bool = False

    def __init__(self, iteration: int, plan_scope: str = "", has_plan: bool = False):
        super().__init__(type=EventType.FEEDBACK_RECEIVED, iteration=iteration,
                         data={"plan_scope": plan_scope, "has_plan": has_plan})
        self.plan_scope = plan_scope
        self.has_plan = has_plan


@dataclass
class GuardrailEvent(Event):
    verdict: str = ""
    policy: str = ""
    reason: str = ""

    def __init__(self, iteration: int, verdict: str, policy: str, reason: str):
        super().__init__(type=EventType.GUARDRAIL_CHECKED, iteration=iteration,
                         data={"verdict": verdict, "policy": policy, "reason": reason})
        self.verdict = verdict
        self.policy = policy
        self.reason = reason
```

```python
# src/ai4se_agent/observability/tracer.py
import json
from pathlib import Path
from ai4se_agent.observability.events import Event


class Tracer:
    def __init__(self):
        self._events: list[Event] = []

    def record(self, event: Event) -> None:
        self._events.append(event)

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = [e.to_dict() for e in self._events]
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def replay(path: str) -> list[dict]:
        p = Path(path)
        if not p.exists():
            return []
        return json.loads(p.read_text(encoding="utf-8"))


class NullTracer(Tracer):
    def record(self, event: Event) -> None:
        pass

    def save(self, path: str) -> None:
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/observability/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/observability/ tests/observability/
git commit -m "feat: add observability layer — Event types and Tracer (subagent: observability-01)"
```

---

### Task 2: Renderer — ABC + TerminalRenderer + NullRenderer

**Files:**
- Create: `src/ai4se_agent/cli/__init__.py`
- Create: `src/ai4se_agent/cli/renderer.py`
- Create: `tests/cli/__init__.py`
- Create: `tests/cli/test_renderer.py`

**Interfaces:**
- Consumes: `Event` types from Task 1 (for trace logging)
- Produces: `Renderer` ABC with `on_state_change`, `on_llm_call`, `on_action`, `on_tool_exec`, `on_feedback`, `on_stop` consumed by StateMachine (Task 4)
- Produces: `NullRenderer` for testing
- Produces: `TerminalRenderer` for interactive use

- [ ] **Step 1: Write the failing test**

```python
# tests/cli/test_renderer.py
from ai4se_agent.cli.renderer import Renderer, NullRenderer, TerminalRenderer
from ai4se_agent.types import StopReason

def test_null_renderer_does_nothing():
    r = NullRenderer()
    r.on_state_change("IDLE", "CONTEXT_ORG", 1)
    r.on_stop(StopReason.SUCCESS, 3)

def test_renderer_is_abstract():
    import inspect
    assert inspect.isabstract(Renderer)

def test_terminal_renderer_creates(capsys):
    r = TerminalRenderer()
    r.on_state_change("IDLE", "CONTEXT_ORG", 1)
    captured = capsys.readouterr()
    assert "[CONTEXT_ORG]" in captured.out
    assert "Iteration 1" in captured.out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/cli/test_renderer.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/ai4se_agent/cli/renderer.py
from abc import ABC, abstractmethod
from ai4se_agent.types import Action, GuardrailResult, ToolResult, StopReason


class Renderer(ABC):
    @abstractmethod
    def on_state_change(self, old_state: str, new_state: str, iteration: int) -> None:
        pass

    @abstractmethod
    def on_llm_call(self, iteration: int, model: str, response: str) -> None:
        pass

    @abstractmethod
    def on_action(self, iteration: int, action: Action, guardrail_result: GuardrailResult | None) -> None:
        pass

    @abstractmethod
    def on_tool_exec(self, iteration: int, tool: str, result: ToolResult) -> None:
        pass

    @abstractmethod
    def on_feedback(self, iteration: int, has_plan: bool, plan_scope: str) -> None:
        pass

    @abstractmethod
    def on_stop(self, reason: StopReason, iteration: int) -> None:
        pass


class NullRenderer(Renderer):
    def on_state_change(self, old_state: str, new_state: str, iteration: int) -> None:
        pass
    def on_llm_call(self, iteration: int, model: str, response: str) -> None:
        pass
    def on_action(self, iteration: int, action: Action, guardrail_result: GuardrailResult | None) -> None:
        pass
    def on_tool_exec(self, iteration: int, tool: str, result: ToolResult) -> None:
        pass
    def on_feedback(self, iteration: int, has_plan: bool, plan_scope: str) -> None:
        pass
    def on_stop(self, reason: StopReason, iteration: int) -> None:
        pass


class TerminalRenderer(Renderer):
    def __init__(self, verbose: bool = False):
        self._verbose = verbose

    def _print(self, line: str) -> None:
        import shutil
        width = shutil.get_terminal_size().columns
        print(line[:width])

    def on_state_change(self, old_state: str, new_state: str, iteration: int) -> None:
        if new_state == "STOP":
            return
        self._print(f"[{new_state}]")

    def on_llm_call(self, iteration: int, model: str, response: str) -> None:
        if self._verbose:
            self._print(f"  model: {model}")
            self._print(f"  response: {response[:200]}")

    def on_action(self, iteration: int, action: Action, guardrail_result: GuardrailResult | None) -> None:
        self._print(f"  action: {action.name}({action.params})")
        if guardrail_result:
            self._print(f"  guardrail: {guardrail_result.policy} → {guardrail_result.verdict}")

    def on_tool_exec(self, iteration: int, tool: str, result: ToolResult) -> None:
        status = "OK" if result.success else "FAILED"
        self._print(f"  result: {status}")
        if self._verbose or not result.success:
            self._print(f"  output: {result.output[:300]}")

    def on_feedback(self, iteration: int, has_plan: bool, plan_scope: str) -> None:
        if has_plan:
            self._print(f"  feedback: correction planned — {plan_scope[:100]}")
        else:
            self._print(f"  feedback: success")

    def on_stop(self, reason: StopReason, iteration: int) -> None:
        self._print(f"STOP: {reason.value} after {iteration} iterations")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/cli/test_renderer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/cli/__init__.py src/ai4se_agent/cli/renderer.py tests/cli/
git commit -m "feat: add Renderer ABC with NullRenderer and TerminalRenderer (subagent: renderer-02)"
```

---

### Task 3: CLI Layer — SessionManager + Commands + Entry Point

**Files:**
- Create: `src/ai4se_agent/cli/session.py`
- Create: `src/ai4se_agent/cli/commands.py`
- Create: `src/ai4se_agent/cli/main.py`
- Delete: `src/ai4se_agent/cli.py` (old flat module)
- Modify: `tests/test_cli.py` — update import path
- Create: `tests/cli/test_session.py`

**Interfaces:**
- Consumes: `Renderer` from Task 2, `Tracer` from Task 1, `HarnessStateMachine` from core
- Produces: `SessionManager` with `start()`, `submit(task)`, `interactive()`, `exit()` — CLI entry point

- [ ] **Step 1: Write the failing test**

```python
# tests/cli/test_session.py
from ai4se_agent.cli.session import SessionManager
from ai4se_agent.cli.renderer import NullRenderer
from ai4se_agent.observability.tracer import NullTracer

def test_session_submit_with_null_renderer():
    session = SessionManager(renderer=NullRenderer(), tracer=NullTracer())
    result = session.start()
    assert result is None

def test_session_submit_task():
    session = SessionManager(renderer=NullRenderer(), tracer=NullTracer())
    result = session.submit("echo hello")
    assert result is not None
    assert "status" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/cli/test_session.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/ai4se_agent/cli/commands.py
def handle_command(line: str, session) -> bool:
    cmd = line.strip().lower()
    if cmd == "/status":
        print(f"State: {session.state.current_state}")
        print(f"Iteration: {session.state.iteration}")
        return True
    if cmd == "/reset":
        session.state = None
        print("Session reset")
        return True
    if cmd == "/verbose":
        if hasattr(session, '_renderer') and hasattr(session._renderer, '_verbose'):
            session._renderer._verbose = not session._renderer._verbose
            print(f"Verbose mode: {'on' if session._renderer._verbose else 'off'}")
        return True
    if cmd in ("exit", "quit"):
        return False
    return False
```

```python
# src/ai4se_agent/cli/session.py
from ai4se_agent.cli.renderer import Renderer, NullRenderer
from ai4se_agent.cli.commands import handle_command
from ai4se_agent.observability.tracer import Tracer, NullTracer
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
from typing import Any


class SessionManager:
    def __init__(self, renderer: Renderer | None = None, tracer: Tracer | None = None):
        self._renderer = renderer or NullRenderer()
        self._tracer = tracer or NullTracer()
        self._harness: HarnessStateMachine | None = None
        self.state: AgentState | None = None

    def _build_harness(self, task: str) -> HarnessStateMachine:
        config = ConfigLoader()
        provider = config.get_provider()
        if provider == "mock":
            llm: Any = MockAdapter(responses=["action: shell command=echo hello", "[DONE]"])
        else:
            api_key = config.get("api_key") or ""
            base_url = config.get("base_url")
            model = config.get("model") or ""
            llm = OpenAIAdapter(api_key=api_key, base_url=base_url, model=model)

        tools = ToolRegistry()
        tools.register(ReadFileTool())
        tools.register(WriteFileTool())
        tools.register(EditFileTool())
        tools.register(ShellTool())
        tools.register(RunTestTool())

        guardrails = GuardrailEngine()
        guardrails.add_policy(CommandPolicy())
        guardrails.add_policy(FilePolicy())
        guardrails.add_policy(WorkspacePolicy(workspace="."))
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
        self.state = state

        return HarnessStateMachine(
            agent_state=state,
            llm_adapter=llm,
            action_parser=ActionParser(),
            action_validator=ActionValidator(),
            tool_registry=tools,
            guardrail_engine=guardrails,
            feedback_loop=feedback,
            memory_manager=memory,
            renderer=self._renderer,
            tracer=self._tracer,
        )

    def start(self) -> None:
        config = ConfigLoader()
        provider = config.get_provider()
        model = config.get("model") or "unknown"
        self._renderer.on_state_change("", "IDLE", 0)
        print(f"Workspace: {'.'}")
        print(f"Model: {model}")
        print(f"Provider: {provider}")
        print()

    def submit(self, task: str) -> dict:
        self._harness = self._build_harness(task)
        result = self._harness.run()
        self._renderer.on_stop(self._harness.stop_reason, self._harness.state.iteration)
        return result

    def interactive(self) -> None:
        self.start()
        while True:
            try:
                line = input("> ").strip()
                if not line:
                    continue
                if line.startswith("/") or line in ("exit", "quit"):
                    if not handle_command(line, self):
                        break
                    continue
                result = self.submit(line)
                print(f"Result: {result['status']} ({result['reason']})")
            except (EOFError, KeyboardInterrupt):
                print()
                break

    def exit(self) -> None:
        print("Session ended")
```

```python
# src/ai4se_agent/cli/main.py
import sys
import argparse
from ai4se_agent.cli.renderer import TerminalRenderer, NullRenderer
from ai4se_agent.cli.session import SessionManager
from ai4se_agent.observability.tracer import Tracer, NullTracer


def main():
    parser = argparse.ArgumentParser(description="AI4SE Coding Agent Harness")
    parser.add_argument("task", nargs="*", help="Task description")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--trace", action="store_true", help="Save JSON trace to sessions/")
    args = parser.parse_args()

    renderer = TerminalRenderer(verbose=args.verbose)
    tracer = Tracer() if args.trace else NullTracer()
    session = SessionManager(renderer=renderer, tracer=tracer)

    if args.task:
        session.start()
        task = " ".join(args.task)
        result = session.submit(task)
        if args.trace:
            import datetime
            path = f"sessions/session_{datetime.datetime.now():%Y%m%d_%H%M%S}.json"
            tracer.save(path)
            print(f"Trace saved: {path}")
    else:
        session.interactive()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Update test_cli.py**

```python
# tests/test_cli.py
from ai4se_agent.cli.main import build_harness

def test_build_harness_creates_machine(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    harness = build_harness("test task", workspace="/tmp")
    assert harness is not None
    assert harness.state.goal == "test task"
```

Actually, `build_harness` is now inside `session.py` as `SessionManager._build_harness`. The old `build_harness` function was moved. Let me reconsider the test.

The test_cli.py test is about the harness being created correctly. In the new architecture, this functionality is in `SessionManager._build_harness`. The test should be updated to test through `SessionManager.submit()` instead.

```python
# tests/test_cli.py
from ai4se_agent.cli.session import SessionManager
from ai4se_agent.cli.renderer import NullRenderer
from ai4se_agent.observability.tracer import NullTracer

def test_session_submit_with_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    session = SessionManager(renderer=NullRenderer(), tracer=NullTracer())
    result = session.submit("test task")
    assert result is not None
    assert "status" in result
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/cli/ tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 6: Delete old cli.py and commit**

```bash
git rm src/ai4se_agent/cli.py
git add src/ai4se_agent/cli/ tests/cli/ tests/test_cli.py
git commit -m "feat: add CLI layer — SessionManager, interactive mode, commands (subagent: cli-03)"
```

---

### Task 4: StateMachine Integration — Renderer/Tracer Callbacks

**Files:**
- Modify: `src/ai4se_agent/core/state_machine.py`

**Interfaces:**
- Consumes: `Renderer` from Task 2, `Tracer` from Task 1
- Produces: `HarnessStateMachine` with constructor params `renderer`, `tracer` and callbacks at key transition points

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_state_machine.py — add to existing test
from ai4se_agent.cli.renderer import NullRenderer
from ai4se_agent.observability.tracer import NullTracer

def test_state_machine_with_renderer():
    from ai4se_agent.core.agent_state import AgentState
    from ai4se_agent.llm.mock_adapter import MockAdapter
    from ai4se_agent.core.action import ActionParser, ActionValidator
    from ai4se_agent.tools.registry import ToolRegistry
    from ai4se_agent.guardrails.engine import GuardrailEngine
    from ai4se_agent.memory.manager import MemoryManager

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
        max_iterations=5,
        renderer=NullRenderer(),
        tracer=NullTracer(),
    )
    result = machine.run()
    assert result["status"] in ("success", "failed")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_state_machine.py -v`
Expected: FAIL (TypeError: unexpected keyword arguments)

- [ ] **Step 3: Modify StateMachine to accept renderer/tracer and emit callbacks**

Add to `__init__` signature:
```python
renderer: Renderer = NullRenderer(),
tracer: Tracer = NullTracer(),
```

Add to `__init__` body:
```python
self._renderer = renderer
self._tracer = tracer
```

Add callbacks at key points:

```python
def _on_context_org(self) -> None:
    self.state.increment_iteration()
    if self.state.iteration > self.max_iterations:
        self.stop_reason = StopReason.MAX_ITERATION
        self._renderer.on_state_change("CONTEXT_ORG", "STOP", self.state.iteration)
        self.stop()
        return
    self._renderer.on_state_change("", "CONTEXT_ORG", self.state.iteration)
    self.call_llm()

def _on_llm_call(self) -> None:
    try:
        messages = self._context_builder.build(self.state)
        response = self.llm.generate(messages)
        self._renderer.on_llm_call(self.state.iteration, self.llm.model if hasattr(self.llm, 'model') else "", response)
        self._tracer.record(LLMEvent(self.state.iteration, getattr(self.llm, 'model', ''), messages, response))
        self.state.history.append({"role": "assistant", "content": response})
        self.parse_action()
    except Exception:
        self.state.error_count += 1
        if self.state.error_count >= 3:
            self.stop_reason = StopReason.LLM_ERROR
            self.stop()
        else:
            self.llm_error()

def _on_action_parse(self) -> None:
    last_msg = self.state.history[-1]["content"]
    if "[DONE]" in last_msg:
        self._renderer.on_state_change("ACTION_PARSE", "STOP", self.state.iteration)
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
    self._renderer.on_action(self.state.iteration, action, None)
    self._tracer.record(ActionEvent(self.state.iteration, action.name, action.params))
    self.check_guardrails()

def _on_guardrail(self) -> None:
    assert self._pending_action is not None
    result = self.guardrails.check(self._pending_action)
    self._pending_guardrail = result
    self._renderer.on_action(self.state.iteration, self._pending_action, result)
    self._tracer.record(GuardrailEvent(self.state.iteration, result.verdict, result.policy, result.reason))
    if result.verdict == "DENY":
        self.deny_action()
    elif result.verdict == "REQUIRE_APPROVAL":
        self.request_approval()
    else:
        self.execute()

def _on_tool_exec(self) -> None:
    assert self._pending_action is not None
    result = self.tools.execute(self._pending_action)
    self._last_tool_result = result
    self.state.record_turn(self._pending_action, result.output)
    self._renderer.on_tool_exec(self.state.iteration, self._pending_action.name, result)
    self._tracer.record(ToolEvent(self.state.iteration, self._pending_action.name, result.success, result.output))
    if result.success:
        self.tool_success()
    else:
        self.tool_error()

def _on_feedback(self) -> None:
    assert self._last_tool_result is not None
    if self.feedback:
        plan = self.feedback.run(self._last_tool_result, self.state.retry_count)
        if plan:
            feedback_msg = (
                f"Feedback: {plan.strategy}\n"
                f"Scope: {plan.scope}\n"
                f"Target files: {plan.target_files}\n"
                f"Retry count: {plan.retry_count}"
            )
            self.state.record_feedback(feedback_msg)
            self.state.retry_count += 1
            if self.state.retry_count >= 3:
                self.state.retry_count = 0
            self._renderer.on_feedback(self.state.iteration, True, plan.scope)
            self._tracer.record(FeedbackEvent(self.state.iteration, plan.scope, True))
            self.feedback_correct()
            return
    self._renderer.on_feedback(self.state.iteration, False, "")
    self._tracer.record(FeedbackEvent(self.state.iteration, "", False))
    self.feedback_done()
```

Need to add imports for event types:
```python
from ai4se_agent.cli.renderer import Renderer, NullRenderer
from ai4se_agent.observability.tracer import Tracer, NullTracer
from ai4se_agent.observability.events import StateEvent, LLMEvent, ActionEvent, ToolEvent, FeedbackEvent, GuardrailEvent
```

Wait, I need to add a `GuardrailEvent` to events.py too. Let me add that.

- [ ] **Step 4: Run tests**

Run: `pytest -q`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/core/state_machine.py src/ai4se_agent/observability/events.py
git commit -m "feat: integrate Renderer and Tracer into StateMachine callbacks (subagent: integration-04)"
```

---

### Task 5: Build Config + Cleanup

**Files:**
- Modify: `pyproject.toml` — update entry point, add colorama dependency
- Verify: old `src/ai4se_agent/cli.py` is deleted

- [ ] **Step 1: Update pyproject.toml**

```toml
[project]
dependencies = [
    "openai>=1.0.0",
    "transitions>=0.9.0",
    "colorama>=0.4.6",
]

[project.scripts]
ai4se-agent = "ai4se_agent.cli.main:main"
```

- [ ] **Step 2: Verify old cli.py is gone**

Run: `test -f src/ai4se_agent/cli.py && echo "EXISTS" || echo "DELETED"`
Expected: DELETED

- [ ] **Step 3: Run full test suite**

Run: `pytest -q && mypy src/ && ruff check src/`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: update pyproject.toml — entry point to cli.main, add colorama (subagent: build-05)"
```

---

## Dependency Graph

```
Task 1 (Events + Tracer)
    │
    ▼
Task 2 (Renderer ABC + impls)
    │
    ▼
Task 3 (SessionManager + CLI entry)
    │
    ▼
Task 4 (StateMachine integration) ── depends on Task 1 + Task 2 interfaces
    │
    ▼
Task 5 (Build config + cleanup)
```

Tasks 1-3 can be parallelized if the interfaces are agreed upon. Task 4 depends on 1 and 2. Task 5 is last.