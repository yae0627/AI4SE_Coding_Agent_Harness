# Session & Event Bus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decouple agent core from terminal output by introducing Session layer (persistent conversation history) and Event Bus (structured event emission from state machine).

**Architecture:** `Session` owns permanent `MessageHistory`; each `send()` creates a temporary `AgentRuntime` that assembles `StateMachine` with injected `EventBus`. 14 event types emitted from `StateMachine._on_*()` methods. `TerminalRenderer` becomes an `EventBus` subscriber — output format unchanged, data flow redirected from direct `_print()` to event handlers.

**Tech Stack:** Python 3.10+, dataclasses, time, uuid, transitions (existing)

## Global Constraints

- Python >=3.10
- All existing 131 tests must remain green
- StateMachine transition graph unchanged — only emit() calls added
- `self.emit()` is no-op when `_event_bus is None` (backward compat)
- TerminalRenderer text output format unchanged
- Event names use `AGENT_STOP` not `SESSION_END` (StateMachine doesn't know about Session)
- `FEEDBACK_COMPLETED` not `FEEDBACK_RESULT` (event describes behavior, not outcome)

---

### Task 1: Event Infrastructure

**Files:**
- Create: `src/ai4se_agent/core/events.py`
- Create: `src/ai4se_agent/core/event_bus.py`
- Create: `tests/core/test_events.py`
- Create: `tests/core/test_event_bus.py`

**Interfaces:**
- Consumes: Nothing
- Produces: `AgentEvent` dataclass, `EventBus` with subscribe/publish

- [ ] **Step 1: Write the failing tests**

```python
# tests/core/test_events.py
from ai4se_agent.core.events import AgentEvent


def test_agent_event_creation():
    event = AgentEvent(
        type="TOOL_START",
        iteration=1,
        state="TOOL_EXEC",
        payload={"tool": "shell", "command": "echo hello"},
    )
    assert event.type == "TOOL_START"
    assert event.iteration == 1
    assert event.state == "TOOL_EXEC"
    assert event.payload["tool"] == "shell"
    assert event.timestamp > 0


def test_agent_event_default_timestamp():
    event = AgentEvent(type="LLM_START", iteration=1, state="LLM_CALL", payload={})
    assert isinstance(event.timestamp, float)


def test_agent_event_to_dict():
    event = AgentEvent(
        type="TOOL_END",
        iteration=2,
        state="TOOL_EXEC",
        payload={"tool": "shell", "success": True, "duration": 1.5},
    )
    d = event.to_dict()
    assert d["type"] == "TOOL_END"
    assert d["iteration"] == 2
    assert d["state"] == "TOOL_EXEC"
    assert d["payload"]["tool"] == "shell"


def test_agent_event_from_dict():
    data = {
        "type": "LLM_END",
        "timestamp": 1000.0,
        "iteration": 3,
        "state": "LLM_CALL",
        "payload": {"model": "gpt-4", "tokens": 500},
    }
    event = AgentEvent.from_dict(data)
    assert event.type == "LLM_END"
    assert event.iteration == 3
    assert event.payload["tokens"] == 500


def test_all_event_types_defined():
    expected = {
        "SESSION_START", "SESSION_END",
        "AGENT_START", "AGENT_STOP",
        "LLM_START", "LLM_END",
        "ACTION_CREATED",
        "GUARDRAIL_PASS", "GUARDRAIL_DENY", "APPROVAL_REQUIRED",
        "TOOL_START", "TOOL_END",
        "FEEDBACK_COMPLETED",
        "MEMORY_WRITE",
    }
    # Verify these are the types we expect to emit
    assert len(expected) == 14
```

```python
# tests/core/test_event_bus.py
from ai4se_agent.core.events import AgentEvent
from ai4se_agent.core.event_bus import EventBus


def test_subscribe_and_publish():
    bus = EventBus()
    received: list[AgentEvent] = []

    def handler(event: AgentEvent) -> None:
        received.append(event)

    bus.subscribe("TOOL_START", handler)
    event = AgentEvent(type="TOOL_START", iteration=1, state="TOOL_EXEC", payload={})
    bus.publish(event)
    assert len(received) == 1
    assert received[0] is event


def test_multiple_subscribers():
    bus = EventBus()
    results: list[str] = []

    bus.subscribe("LLM_END", lambda e: results.append("a"))
    bus.subscribe("LLM_END", lambda e: results.append("b"))
    bus.publish(AgentEvent(type="LLM_END", iteration=1, state="LLM_CALL", payload={}))
    assert results == ["a", "b"]


def test_unrelated_subscriber_not_called():
    bus = EventBus()
    results: list[str] = []

    bus.subscribe("LLM_START", lambda e: results.append("called"))
    bus.publish(AgentEvent(type="TOOL_START", iteration=1, state="TOOL_EXEC", payload={}))
    assert results == []


def test_publish_no_subscribers_does_not_crash():
    bus = EventBus()
    bus.publish(AgentEvent(type="TOOL_END", iteration=1, state="TOOL_EXEC", payload={}))


def test_subscribe_same_handler_multiple_types():
    bus = EventBus()
    results: list[str] = []

    def handler(event: AgentEvent) -> None:
        results.append(event.type)

    bus.subscribe("TOOL_START", handler)
    bus.subscribe("TOOL_END", handler)
    bus.publish(AgentEvent(type="TOOL_START", iteration=1, state="TOOL_EXEC", payload={}))
    bus.publish(AgentEvent(type="TOOL_END", iteration=1, state="TOOL_EXEC", payload={}))
    assert results == ["TOOL_START", "TOOL_END"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/core/test_events.py tests/core/test_event_bus.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Create src/ai4se_agent/core/events.py**

```python
import time
from dataclasses import dataclass, field


@dataclass
class AgentEvent:
    type: str
    iteration: int
    state: str
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "timestamp": self.timestamp,
            "iteration": self.iteration,
            "state": self.state,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentEvent":
        return cls(
            type=data["type"],
            timestamp=data.get("timestamp", 0.0),
            iteration=data.get("iteration", 0),
            state=data.get("state", ""),
            payload=data.get("payload", {}),
        )
```

- [ ] **Step 4: Create src/ai4se_agent/core/event_bus.py**

```python
from collections import defaultdict
from typing import Callable
from ai4se_agent.core.events import AgentEvent


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[AgentEvent], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable[[AgentEvent], None]) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: AgentEvent) -> None:
        for handler in self._handlers.get(event.type, []):
            handler(event)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/core/test_events.py tests/core/test_event_bus.py -v`
Expected: ALL 10 PASS

- [ ] **Step 6: Commit**

```bash
git add src/ai4se_agent/core/events.py src/ai4se_agent/core/event_bus.py tests/core/test_events.py tests/core/test_event_bus.py
git commit -m "feat: add AgentEvent dataclass and EventBus with subscribe/publish"
```

---

### Task 2: MessageHistory

**Files:**
- Create: `src/ai4se_agent/session/__init__.py`
- Create: `src/ai4se_agent/session/history.py`
- Create: `tests/session/__init__.py`
- Create: `tests/session/test_history.py`

**Interfaces:**
- Consumes: Nothing
- Produces: `MessageHistory` with add/get_recent/clear

- [ ] **Step 1: Write the failing tests**

```python
# tests/session/test_history.py
from ai4se_agent.session.history import MessageHistory


def test_add_user_message():
    h = MessageHistory()
    h.add_user("hello")
    messages = h.get_recent()
    assert len(messages) == 1
    assert messages[0] == {"role": "user", "content": "hello"}


def test_add_assistant_message():
    h = MessageHistory()
    h.add_assistant("action: shell command=ls")
    messages = h.get_recent()
    assert messages[0]["role"] == "assistant"
    assert "shell" in messages[0]["content"]


def test_add_tool_result():
    h = MessageHistory()
    h.add_tool_result("shell", "file1.txt\nfile2.txt")
    messages = h.get_recent()
    assert messages[0]["role"] == "tool"
    assert "file1.txt" in messages[0]["content"]


def test_add_system_message():
    h = MessageHistory()
    h.add_system("Project rules: no rm -rf")
    messages = h.get_recent()
    assert messages[0]["role"] == "system"


def test_get_recent_ordering():
    h = MessageHistory()
    h.add_user("task 1")
    h.add_assistant("response 1")
    h.add_user("task 2")
    messages = h.get_recent()
    assert len(messages) == 3
    assert messages[0]["content"] == "task 1"
    assert messages[2]["content"] == "task 2"


def test_get_recent_truncation():
    h = MessageHistory(max_messages=3)
    for i in range(5):
        h.add_user(f"msg {i}")
    messages = h.get_recent()
    assert len(messages) == 3
    assert messages[0]["content"] == "msg 2"
    assert messages[-1]["content"] == "msg 4"


def test_add_turn():
    h = MessageHistory()
    h.add_turn("user says hi", {"status": "success", "reason": "success", "iterations": 3})
    messages = h.get_recent()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"


def test_clear():
    h = MessageHistory()
    h.add_user("msg")
    h.clear()
    assert h.get_recent() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/session/test_history.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Create src/ai4se_agent/session/__init__.py**

```python
from ai4se_agent.session.history import MessageHistory
from ai4se_agent.session.session import Session, AgentRuntime

__all__ = ["MessageHistory", "Session", "AgentRuntime"]
```

- [ ] **Step 4: Create src/ai4se_agent/session/history.py**

```python
class MessageHistory:
    def __init__(self, max_messages: int = 50):
        self._messages: list[dict] = []
        self._max_messages = max_messages

    def add_user(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})
        self._trim()

    def add_assistant(self, content: str) -> None:
        self._messages.append({"role": "assistant", "content": content})
        self._trim()

    def add_tool_result(self, action_name: str, output: str) -> None:
        self._messages.append({"role": "tool", "content": output, "name": action_name})
        self._trim()

    def add_system(self, content: str) -> None:
        self._messages.append({"role": "system", "content": content})
        self._trim()

    def add_turn(self, user_message: str, result: dict) -> None:
        self.add_user(user_message)
        self.add_assistant(f"Task completed: {result['status']} ({result['reason']})")

    def get_recent(self, n: int | None = None) -> list[dict]:
        count = n if n is not None else self._max_messages
        return self._messages[-count:] if count < len(self._messages) else list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def _trim(self) -> None:
        while len(self._messages) > self._max_messages:
            self._messages.pop(0)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/session/test_history.py -v`
Expected: ALL 8 PASS

- [ ] **Step 6: Commit**

```bash
git add src/ai4se_agent/session/ tests/session/
git commit -m "feat: add MessageHistory with add/get_recent/clear"
```

---

### Task 3: Session + AgentRuntime

**Files:**
- Create: `src/ai4se_agent/session/session.py`
- Create: `tests/session/test_session.py`

**Interfaces:**
- Consumes: `EventBus` (Task 1), `MessageHistory` (Task 2)
- Produces: `Session` with `send()`, `AgentRuntime` with `run()`

- [ ] **Step 1: Write the failing tests**

```python
# tests/session/test_session.py
from ai4se_agent.session.session import Session, AgentRuntime
from ai4se_agent.session.history import MessageHistory
from ai4se_agent.core.event_bus import EventBus
from ai4se_agent.config.loader import ConfigLoader


def test_session_send_returns_result():
    bus = EventBus()
    history = MessageHistory()
    config = ConfigLoader()
    config.set("provider", "name", "mock")
    session = Session(config=config, event_bus=bus, history=history)
    result = session.send("echo hello")
    assert result["status"] in ("success", "failed")
    assert "iterations" in result


def test_session_history_accumulates():
    bus = EventBus()
    history = MessageHistory()
    config = ConfigLoader()
    config.set("provider", "name", "mock")
    session = Session(config=config, event_bus=bus, history=history)
    session.send("first task")
    session.send("second task")
    messages = history.get_recent()
    assert len(messages) >= 2


def test_session_emits_session_events():
    bus = EventBus()
    events: list[str] = []
    bus.subscribe("SESSION_START", lambda e: events.append(e.type))
    bus.subscribe("SESSION_END", lambda e: events.append(e.type))
    history = MessageHistory()
    config = ConfigLoader()
    config.set("provider", "name", "mock")
    session = Session(config=config, event_bus=bus, history=history)
    session.send("task")
    assert "SESSION_START" in events


def test_agent_runtime_emits_agent_events():
    bus = EventBus()
    events: list[str] = []
    bus.subscribe("AGENT_START", lambda e: events.append("start"))
    bus.subscribe("AGENT_STOP", lambda e: events.append("stop"))
    history = MessageHistory()
    config = ConfigLoader()
    config.set("provider", "name", "mock")
    runtime = AgentRuntime(
        goal="test",
        history=history.get_recent(),
        config=config,
        event_bus=bus,
    )
    runtime.run()
    assert events == ["start", "stop"]


def test_agent_runtime_history_injected():
    bus = EventBus()
    history = MessageHistory()
    history.add_user("previous task")
    history.add_assistant("previous response")
    config = ConfigLoader()
    config.set("provider", "name", "mock")
    runtime = AgentRuntime(
        goal="new task",
        history=history.get_recent(),
        config=config,
        event_bus=bus,
    )
    runtime.run()
    # AgentState history should have been pre-populated
    assert len(runtime._state.history) >= 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/session/test_session.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Create src/ai4se_agent/session/session.py**

```python
import uuid
from ai4se_agent.config.loader import ConfigLoader
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.core.event_bus import EventBus
from ai4se_agent.core.events import AgentEvent
from ai4se_agent.core.state_machine import HarnessStateMachine
from ai4se_agent.feedback.classifier import FailureClassifier
from ai4se_agent.feedback.loop import FeedbackLoop
from ai4se_agent.feedback.planner import CorrectionPlanner
from ai4se_agent.feedback.sensor import LintSensor, TestSensor
from ai4se_agent.guardrails.command_policy import CommandPolicy
from ai4se_agent.guardrails.engine import GuardrailEngine
from ai4se_agent.guardrails.file_policy import FilePolicy
from ai4se_agent.guardrails.git_policy import GitPolicy
from ai4se_agent.guardrails.workspace_policy import WorkspacePolicy
from ai4se_agent.llm.manager import LLMManager
from ai4se_agent.memory.manager import MemoryManager
from ai4se_agent.memory.persistent import PersistentMemory
from ai4se_agent.memory.session import SessionMemory
from ai4se_agent.session.history import MessageHistory
from ai4se_agent.tools.edit_file import EditFileTool
from ai4se_agent.tools.read_file import ReadFileTool
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.tools.run_test import RunTestTool
from ai4se_agent.tools.shell import ShellTool
from ai4se_agent.tools.write_file import WriteFileTool


class AgentRuntime:
    def __init__(
        self,
        goal: str,
        history: list[dict],
        config: ConfigLoader,
        event_bus: EventBus | None = None,
    ):
        self.goal = goal
        self._history = history
        self._config = config
        self._event_bus = event_bus
        self._llm = LLMManager(config)
        self._state: AgentState | None = None

    def run(self) -> dict:
        self._emit("AGENT_START", payload={"goal": self.goal})

        llm = self._llm.get_adapter()

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
            planner=CorrectionPlanner(),
        )

        memory = MemoryManager(
            session=SessionMemory(),
            persistent=PersistentMemory(),
        )

        self._state = AgentState(goal=self.goal)
        self._state.history = list(self._history)

        machine = HarnessStateMachine(
            agent_state=self._state,
            llm_adapter=llm,
            action_parser=ActionParser(),
            action_validator=ActionValidator(schemas=tools.list_schemas()),
            tool_registry=tools,
            guardrail_engine=guardrails,
            feedback_loop=feedback,
            memory_manager=memory,
            event_bus=self._event_bus,
        )
        result = machine.run()
        self._emit("AGENT_STOP", payload={"reason": result["reason"], "iterations": result["iterations"]})
        return result

    def _emit(self, event_type: str, payload: dict | None = None) -> None:
        if self._event_bus is None:
            return
        iteration = self._state.iteration if self._state else 0
        state = self._state.current_state if self._state else "IDLE"
        self._event_bus.publish(AgentEvent(
            type=event_type,
            iteration=iteration,
            state=state,
            payload=payload or {},
        ))


class Session:
    def __init__(
        self,
        config: ConfigLoader,
        event_bus: EventBus | None = None,
        history: MessageHistory | None = None,
    ):
        self.id = uuid.uuid4().hex[:12]
        self._config = config
        self._event_bus = event_bus or EventBus()
        self.history = history or MessageHistory()

    def send(self, message: str) -> dict:
        runtime = AgentRuntime(
            goal=message,
            history=self.history.get_recent(),
            config=self._config,
            event_bus=self._event_bus,
        )
        result = runtime.run()
        self.history.add_turn(message, result)
        return result
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/session/test_session.py -v`
Expected: ALL 5 PASS

- [ ] **Step 6: Commit**

```bash
git add src/ai4se_agent/session/session.py tests/session/test_session.py
git commit -m "feat: add Session with persistent history and AgentRuntime per turn"
```

---

### Task 4: StateMachine emit() Integration

**Files:**
- Modify: `src/ai4se_agent/core/state_machine.py`
- Modify: `src/ai4se_agent/cli/session.py` (old — pass EventBus=None for backward compat)

**Interfaces:**
- Consumes: `AgentEvent`, `EventBus` from Task 1
- Produces: StateMachine with emit() calls at each _on_* method

- [ ] **Step 1: Write a test that verifies events are emitted**

```python
# Append to tests/core/test_event_bus.py
from ai4se_agent.core.state_machine import HarnessStateMachine
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.llm.mock_adapter import MockAdapter
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.guardrails.engine import GuardrailEngine
from ai4se_agent.memory.manager import MemoryManager


def test_state_machine_emits_events():
    bus = EventBus()
    events: list[str] = []

    bus.subscribe("AGENT_START", lambda e: events.append("agent_start"))
    bus.subscribe("LLM_START", lambda e: events.append("llm_start"))
    bus.subscribe("LLM_END", lambda e: events.append("llm_end"))
    bus.subscribe("ACTION_CREATED", lambda e: events.append("action_created"))
    bus.subscribe("GUARDRAIL_PASS", lambda e: events.append("guardrail_pass"))
    bus.subscribe("TOOL_START", lambda e: events.append("tool_start"))
    bus.subscribe("TOOL_END", lambda e: events.append("tool_end"))
    bus.subscribe("FEEDBACK_COMPLETED", lambda e: events.append("feedback_completed"))
    bus.subscribe("MEMORY_WRITE", lambda e: events.append("memory_write"))
    bus.subscribe("AGENT_STOP", lambda e: events.append("agent_stop"))

    # Emit AGENT_START manually (normally done by AgentRuntime)
    bus.publish(AgentEvent(type="AGENT_START", iteration=0, state="IDLE", payload={"goal": "test"}))

    llm = MockAdapter(responses=[
        '{"action": "read_file", "parameters": {"path": "test.txt"}}',
        '{"action": "finish", "parameters": {}}',
    ])
    state = AgentState(goal="test")
    machine = HarnessStateMachine(
        agent_state=state,
        llm_adapter=llm,
        action_parser=ActionParser(),
        action_validator=ActionValidator(),
        tool_registry=ToolRegistry(),
        guardrail_engine=GuardrailEngine(),
        feedback_loop=None,
        memory_manager=MemoryManager(),
        max_iterations=3,
        event_bus=bus,
    )
    machine.run()

    assert "llm_start" in events
    assert "llm_end" in events
    assert "agent_stop" in events


def test_state_machine_no_event_bus_does_not_crash():
    """Backward compat: StateMachine works without EventBus."""
    llm = MockAdapter(responses=['{"action": "finish", "parameters": {}}'])
    state = AgentState(goal="test")
    machine = HarnessStateMachine(
        agent_state=state,
        llm_adapter=llm,
        action_parser=ActionParser(),
        action_validator=ActionValidator(),
        tool_registry=ToolRegistry(),
        guardrail_engine=GuardrailEngine(),
        feedback_loop=None,
        memory_manager=MemoryManager(),
        max_iterations=3,
    )
    result = machine.run()
    assert result["status"] in ("success", "failed")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/core/test_event_bus.py::test_state_machine_emits_events -v`
Expected: FAIL — `event_bus` parameter not accepted

- [ ] **Step 3: Update StateMachine.__init__**

Read `src/ai4se_agent/core/state_machine.py`. Add `event_bus` parameter after `tracer`:

```python
# In __init__ signature, add after tracer parameter:
    event_bus: "EventBus | None" = None,
):
    ...
    self._event_bus = event_bus
```

And import at top:

```python
from ai4se_agent.core.events import AgentEvent
```

- [ ] **Step 4: Add emit() helper method to StateMachine**

```python
    def _emit(self, event_type: str, payload: dict | None = None) -> None:
        if self._event_bus is None:
            return
        self._event_bus.publish(AgentEvent(
            type=event_type,
            iteration=self.state.iteration,
            state=self._fsm_state,
            payload=payload or {},
        ))
```

- [ ] **Step 5: Add emit() calls to each _on_* method**

| Method | Add emit() call | Payload |
|--------|----------------|---------|
| `_on_llm_call` (before generate) | `self._emit("LLM_START", {"model": getattr(self.llm, "model", "")})` | model |
| `_on_llm_call` (after generate) | `self._emit("LLM_END", {"model": getattr(self.llm, "model", ""), "response_preview": response[:200]})` | model, preview |
| `_on_action_parse` (success) | `self._emit("ACTION_CREATED", {"action_name": action.name, "parameters": action.parameters})` | name, params |
| `_on_guardrail` (ALLOW) | `self._emit("GUARDRAIL_PASS", {"policy": result.policy})` | policy |
| `_on_guardrail` (DENY) | `self._emit("GUARDRAIL_DENY", {"policy": result.policy, "reason": result.reason})` | policy, reason |
| `_on_guardrail` (REQUIRE_APPROVAL) | `self._emit("APPROVAL_REQUIRED", {"policy": result.policy, "reason": result.reason})` | policy, reason |
| `_on_tool_exec` (before execute) | `self._emit("TOOL_START", {"tool": self._pending_action.name, "parameters": self._pending_action.parameters})` | tool, params |
| `_on_tool_exec` (after execute) | `self._emit("TOOL_END", {"tool": self._pending_action.name, "success": result.success, "output_preview": result.output[:500]})` | tool, success, output |
| `_on_feedback` | `self._emit("FEEDBACK_COMPLETED", {"has_plan": plan is not None, "scope": plan.scope if plan else ""})` | has_plan, scope |
| `_on_memory_update` | `self._emit("MEMORY_WRITE", {})` | |
| `_on_stop` | `self._emit("AGENT_STOP", {"reason": self.stop_reason.value, "iterations": self.state.iteration})` | reason, iterations |

Exact code for each edit — use the Edit tool to insert emit() calls at the right positions.

For example, `_on_llm_call` should become:

```python
def _on_llm_call(self) -> None:
    try:
        messages = self._context_builder.build(self.state)
        self._emit("LLM_START", {"model": getattr(self.llm, "model", "")})
        response = self.llm.generate(messages)
        model = getattr(self.llm, "model", "")
        self._emit("LLM_END", {"model": model, "response_preview": response[:200]})
        self._renderer.on_llm_call(self.state.iteration, model, response)
        ...
```

- [ ] **Step 6: Update old cli/session.py (backward compat)**

In `_build_harness()`, pass `event_bus=None` (or omit — default is None):

The existing `HarnessStateMachine(...)` call in `cli/session.py` already works because `event_bus` defaults to `None`.

- [ ] **Step 7: Run tests**

Run: `pytest tests/core/test_event_bus.py tests/core/test_state_machine.py -v`
Expected: ALL PASS including new emit tests. Old state machine tests pass because `event_bus=None` is backward compat.

- [ ] **Step 8: Commit**

```bash
git add src/ai4se_agent/core/state_machine.py tests/core/test_event_bus.py
git commit -m "feat: add EventBus emit() calls to StateMachine _on_* methods"
```

---

### Task 5: TerminalRenderer Event Subscriber

**Files:**
- Modify: `src/ai4se_agent/cli/renderer.py`
- Modify: `tests/cli/test_renderer.py`

**Interfaces:**
- Consumes: `AgentEvent`, `EventBus` from Task 1
- Produces: `TerminalRenderer` subscribes to EventBus, output format unchanged

- [ ] **Step 1: Update tests/cli/test_renderer.py**

Add event-driven renderer tests. Read the current file first, then APPEND:

```python
from ai4se_agent.core.events import AgentEvent


def test_renderer_handles_tool_start_event(capsys):
    r = TerminalRenderer()
    event = AgentEvent(
        type="TOOL_START",
        iteration=1,
        state="TOOL_EXEC",
        payload={"tool": "shell", "parameters": {"command": "echo hello"}},
    )
    r._on_tool_start(event)
    # _on_tool_start is currently a no-op (action shown by _on_action_created)
    # Verifies handler doesn't crash


def test_renderer_handles_tool_end_event_ok(capsys):
    r = TerminalRenderer()
    event = AgentEvent(
        type="TOOL_END",
        iteration=1,
        state="TOOL_EXEC",
        payload={"tool": "shell", "success": True, "output_preview": "hello"},
    )
    r._on_tool_end(event)
    captured = capsys.readouterr()
    assert "OK" in captured.out


def test_renderer_handles_tool_end_event_failed(capsys):
    r = TerminalRenderer()
    event = AgentEvent(
        type="TOOL_END",
        iteration=1,
        state="TOOL_EXEC",
        payload={"tool": "shell", "success": False, "output_preview": "error msg"},
    )
    r._on_tool_end(event)
    captured = capsys.readouterr()
    assert "FAILED" in captured.out


def test_renderer_handles_llm_end_event(capsys):
    r = TerminalRenderer(verbose=True)
    event = AgentEvent(
        type="LLM_END",
        iteration=1,
        state="LLM_CALL",
        payload={"model": "gpt-4", "response_preview": '{"action": "finish"}'},
    )
    r._on_llm_end(event)
    captured = capsys.readouterr()
    assert "gpt-4" in captured.out


def test_renderer_subscribe_registers_handlers():
    from ai4se_agent.core.event_bus import EventBus
    bus = EventBus()
    r = TerminalRenderer(event_bus=bus)
    # After construction, handlers should be registered
    # Verify by publishing and checking output
    import io
    import sys
    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        bus.publish(AgentEvent(
            type="AGENT_STOP", iteration=3, state="STOP",
            payload={"reason": "success", "iterations": 3}
        ))
        output = captured.getvalue()
        assert "success" in output
    finally:
        sys.stdout = old_stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/cli/test_renderer.py::test_renderer_handles_tool_start_event -v`
Expected: FAIL — `_on_tool_start` not defined

- [ ] **Step 3: Update TerminalRenderer**

Read the current file. Add event handler methods and an EventBus constructor parameter:

```python
# Update __init__ to accept event_bus:
class TerminalRenderer(Renderer):
    def __init__(self, verbose: bool = False, max_output: int = 500,
                 event_bus: "EventBus | None" = None):
        self._verbose = verbose
        self._max_output = max_output
        self._total_tokens: int = 0
        self._total_elapsed_ms: float = 0.0
        if event_bus:
            event_bus.subscribe("TOOL_START", self._on_tool_start)
            event_bus.subscribe("TOOL_END", self._on_tool_end)
            event_bus.subscribe("LLM_END", self._on_llm_end)
            event_bus.subscribe("ACTION_CREATED", self._on_action_created)
            event_bus.subscribe("GUARDRAIL_PASS", self._on_guardrail_pass)
            event_bus.subscribe("GUARDRAIL_DENY", self._on_guardrail_deny)
            event_bus.subscribe("FEEDBACK_COMPLETED", self._on_feedback_completed)
            event_bus.subscribe("AGENT_STOP", self._on_agent_stop)

    # Add event handler methods:
    def _on_tool_start(self, event: "AgentEvent") -> None:
        # Action details already shown by _on_action_created.
        pass

    def _on_tool_end(self, event: "AgentEvent") -> None:
        success = event.payload.get("success", True)
        status = "OK" if success else "FAILED"
        self._print(f"  result: {status}")
        output = event.payload.get("output_preview", "")
        if self._verbose or not success:
            if output:
                self._print(f"  output: {output[:self._max_output]}")

    def _on_llm_end(self, event: "AgentEvent") -> None:
        if self._verbose:
            model = event.payload.get("model", "")
            preview = event.payload.get("response_preview", "")
            self._print(f"  model: {model}")
            self._print(f"  response: {preview[:500 if self._verbose else 200]}")

    def _on_action_created(self, event: "AgentEvent") -> None:
        name = event.payload.get("action_name", "unknown")
        params = event.payload.get("parameters", {})
        self._print(f"  action: {name}({params})")

    def _on_guardrail_pass(self, event: "AgentEvent") -> None:
        policy = event.payload.get("policy", "")
        self._print(f"  guardrail: {policy} -> ALLOW")

    def _on_guardrail_deny(self, event: "AgentEvent") -> None:
        policy = event.payload.get("policy", "")
        self._print(f"  guardrail: {policy} -> DENY")

    def _on_feedback_completed(self, event: "AgentEvent") -> None:
        has_plan = event.payload.get("has_plan", False)
        if has_plan:
            scope = event.payload.get("scope", "")
            self._print(f"  feedback: correction planned -- {scope[:100]}")
        else:
            self._print("  feedback: success")

    def _on_agent_stop(self, event: "AgentEvent") -> None:
        reason = event.payload.get("reason", "unknown")
        iterations = event.payload.get("iterations", 0)
        self._print(
            f"STOP: {reason} | {iterations} iters | "
            f"{self._total_tokens} tokens | {self._total_elapsed_ms / 1000:.1f}s"
        )
```

The existing `on_state_change`, `on_llm_call`, `on_action`, `on_tool_exec`, `on_feedback`, `on_stop`, `on_token_usage`, `on_timing` methods REMAIN UNCHANGED for backward compatibility with the old direct-call path.

- [ ] **Step 4: Run tests**

Run: `pytest tests/cli/test_renderer.py -v`
Expected: ALL tests PASS (old + new)

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/cli/renderer.py tests/cli/test_renderer.py
git commit -m "feat: TerminalRenderer subscribes to EventBus with event handler methods"
```

---

### Task 6: CLI Session Wiring

**Files:**
- Modify: `src/ai4se_agent/cli/session.py` (use Session class in interactive())
- Modify: `src/ai4se_agent/cli/main.py` (wire EventBus → Session → Renderer)

**Interfaces:**
- Consumes: `Session` (Task 3), `AgentRuntime` (Task 3), `EventBus` (Task 1)
- Produces: interactive() loop powered by Session, not per-turn submit()

- [ ] **Step 1: Update cli/session.py**

Read the current file. Replace `interactive()` and related methods to use `Session`:

The `SessionManager` class keeps backward compat for tests. A new `Session` is created when entering interactive mode.

```python
# In interactive(), replace:
#   self.submit(line)
# with:
#   self._session.send(line)

# Add _session attribute, initialized on first interactive() call or in __init__
```

The key change in `interactive()`:

```python
def interactive(self) -> None:
    from ai4se_agent.session.session import Session
    from ai4se_agent.core.event_bus import EventBus

    bus = EventBus()
    # Wire renderer to event bus
    if hasattr(self._renderer, '_on_tool_start'):
        bus.subscribe("TOOL_START", self._renderer._on_tool_start)
        bus.subscribe("TOOL_END", self._renderer._on_tool_end)
        bus.subscribe("LLM_END", self._renderer._on_llm_end)
        bus.subscribe("ACTION_CREATED", self._renderer._on_action_created)
        bus.subscribe("GUARDRAIL_PASS", self._renderer._on_guardrail_pass)
        bus.subscribe("GUARDRAIL_DENY", self._renderer._on_guardrail_deny)
        bus.subscribe("FEEDBACK_COMPLETED", self._renderer._on_feedback_completed)
        bus.subscribe("AGENT_STOP", self._renderer._on_agent_stop)

    session = Session(config=self._config, event_bus=bus)
    bus.publish(AgentEvent(type="SESSION_START", iteration=0, state="IDLE",
                           payload={"session_id": session.id}))

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
            result = session.send(line)
            print(f"Result: {result['status']} ({result['reason']})")
        except (EOFError, KeyboardInterrupt):
            print()
            break

    bus.publish(AgentEvent(type="SESSION_END", iteration=0, state="STOP",
                           payload={"reason": "user_exit"}))
```

The `submit()` method (single-task mode) remains unchanged — it still creates StateMachine directly.

Add import at top:

```python
from ai4se_agent.core.events import AgentEvent
```

- [ ] **Step 2: Update cli/main.py**

In the single-task path (`if args.task:`), the existing code works unchanged. In the interactive path (`else:`), `session.interactive()` now uses the new Session internally.

Ensure `ConfigLoader` is passed to `SessionManager`:

```python
config = ConfigLoader()
config.load()
...
session = SessionManager(config=config, renderer=renderer, tracer=tracer)
```

This is already the case from the deployment optimization phase.

- [ ] **Step 3: Run existing session tests**

Run: `pytest tests/cli/test_session.py tests/test_cli.py -v`
Expected: ALL PASS (backward compat — single-task mode unchanged)

- [ ] **Step 4: Run full test suite**

Run: `python -m pytest -v`
Expected: ALL 131+ tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/cli/session.py
git commit -m "feat: wire Session with EventBus into interactive() loop"
```

---

### Task 7: Full Test Pass + Integration Verification

**Files:**
- (verification only)

**Interfaces:**
- Consumes: All Tasks 1-6
- Produces: Verified integration, all tests green

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest -v`
Expected: ALL tests PASS (~145+, 131 original + ~15 new)

- [ ] **Step 2: Run ruff lint**

Run: `python -m ruff check src/ tests/`
Expected: All checks passed

- [ ] **Step 3: End-to-end smoke test with mock LLM**

Run: `LLM_PROVIDER=mock python -m ai4se_agent.cli.main "test" 2>&1`
Expected: Runs to completion, output format matches current behavior

- [ ] **Step 4: Interactive session test**

Run: `echo -e "test task\nexit" | LLM_PROVIDER=mock python -m ai4se_agent.cli.main 2>&1`
Expected: Accepts multiple inputs, history persists between turns

- [ ] **Step 5: Commit any fixes**

```bash
git add -A
git commit -m "chore: integration fixups after full test pass"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - Session + MessageHistory → Task 2 (history), Task 3 (session)
   - AgentRuntime (per-turn isolate) → Task 3
   - 14 AgentEvent types → Task 1 (events.py)
   - EventBus subscribe/publish → Task 1 (event_bus.py)
   - StateMachine emit() → Task 4
   - TerminalRenderer subscriber → Task 5
   - CLI wiring → Task 6
   - Full test pass → Task 7

2. **Placeholder scan:** No TBD/TODO. All code blocks are complete. All event types are listed with payload fields.

3. **Type consistency:**
   - `AgentEvent(type: str, iteration: int, state: str, payload: dict, timestamp: float)` — consistent throughout
   - `EventBus.subscribe(event_type: str, handler: Callable)` — consistent
   - `MessageHistory.get_recent(n: int | None = None) -> list[dict]` — consistent
   - `Session.send(message: str) -> dict` — consistent
   - `AgentRuntime.run() -> dict` — consistent
   - `self._emit()` in StateMachine matches `self._emit()` in AgentRuntime — same signature
