# Session & Event Bus Architecture Design

> 2026-07-23 | Phase 1: Interaction Optimization

## Overview

Phase 1 of the interaction optimization track. Decouple the agent core from terminal output by introducing a Session layer (persistent conversation history across turns) and an Event Bus (structured event emission from the state machine). The user-visible output does not change, but the architecture is rebuilt to support subsequent phases (Structured Renderer, Human Interaction, Streaming, Rich UI).

## Architecture

```
interactive() loop
    │
    └── Session.send(message)
            │
            ├── Session.history (permanent, cross-turn)
            │
            └── AgentRuntime (created per turn, destroyed after)
                    ├── AgentState (goal = this turn's input)
                    ├── StateMachine
                    ├── LLMManager
                    └── ToolRegistry
                        │
                        │  StateMachine._on_*()
                        │       │
                        │       │  self.emit(AgentEvent)
                        │       ▼
                        │  EventBus
                        │       │
                        │       ├── TerminalRenderer (subscribe → print)
                        │       ├── Tracer (subscribe → record)
                        │       └── (future: RichRenderer, WebSocket...)
                        │
                        ▼
                 AgentRuntime destroyed, StateMachine result returned
```

---

## Session Layer

### Session

```python
class Session:
    id: str
    history: MessageHistory
    _config: ConfigLoader
    _tools: ToolRegistry

    def send(self, message: str) -> dict:
        runtime = AgentRuntime(
            goal=message,
            history=self.history.get_recent(n=20),
            config=self._config,
            tools=self._tools,
            event_bus=self._event_bus,
        )
        result = runtime.run()
        self.history.add_turn(message, result)
        return result
```

### MessageHistory

```python
class MessageHistory:
    def add_user(self, content: str) -> None
    def add_assistant(self, content: str) -> None
    def add_tool_result(self, action_name: str, output: str) -> None
    def add_system(self, content: str) -> None
    def get_recent(self, n: int = 20) -> list[dict]
    def clear(self) -> None
```

### AgentRuntime

A lightweight factory that assembles StateMachine dependencies per turn:

```python
class AgentRuntime:
    goal: str                       # this turn's user input
    history: list[dict]             # recent conversation history
    event_bus: EventBus             # shared event bus

    def run(self) -> dict:
        state = AgentState(goal=self.goal)
        state.history = self.history  # pre-populate with prior turns
        machine = HarnessStateMachine(
            agent_state=state,
            event_bus=self.event_bus,
            ...
        )
        return machine.run()
```

### Key design decisions

- **Session ≠ permanent AgentState.** AgentState is created fresh per turn with `goal = current message`. History is owned by Session and injected into each turn's AgentState.
- **`send()` is synchronous.** Returns only after the FSM reaches STOP. Future phases add interrupt.
- **History is injected into ContextBuilder** via `AgentState.history`, so the LLM sees prior conversation context.
- **Single-task mode (`ai4se-agent "task"`) unchanged.** Bypasses Session entirely, directly creates AgentRuntime.

---

## Event Bus Layer

### AgentEvent — unified structure

```python
@dataclass
class AgentEvent:
    type: str                       # EventType value
    timestamp: float                # time.time()
    iteration: int
    state: str                      # current FSM state name
    payload: dict                   # type-specific data
```

### EventType — 14 events

| Category | Event | Emitter | Key payload fields |
|----------|-------|---------|-------------------|
| Session | `SESSION_START` | `Session.start()` | session_id |
| Session | `SESSION_END` | `Session` (after send returns) | reason, total_turns |
| Agent | `AGENT_START` | `AgentRuntime.run()` (before FSM start) | goal |
| Agent | `AGENT_STOP` | `StateMachine._on_stop()` | reason, iterations |
| LLM | `LLM_START` | `StateMachine._on_llm_call()` (before generate) | model, message_count |
| LLM | `LLM_END` | `StateMachine._on_llm_call()` (after generate) | model, response_preview, tokens |
| Action | `ACTION_CREATED` | `StateMachine._on_action_parse()` (success) | action_name, parameters |
| Guardrail | `GUARDRAIL_PASS` | `StateMachine._on_guardrail()` (ALLOW) | policy |
| Guardrail | `GUARDRAIL_DENY` | `StateMachine._on_guardrail()` (DENY) | policy, reason |
| Guardrail | `APPROVAL_REQUIRED` | `StateMachine._on_guardrail()` (REQUIRE_APPROVAL) | policy, reason |
| Tool | `TOOL_START` | `StateMachine._on_tool_exec()` (before execute) | tool, parameters |
| Tool | `TOOL_END` | `StateMachine._on_tool_exec()` (after execute) | tool, success, duration, output_preview |
| Feedback | `FEEDBACK_COMPLETED` | `StateMachine._on_feedback()` | has_plan, scope, severity |
| Memory | `MEMORY_WRITE` | `StateMachine._on_memory_update()` | role, content_preview |

### EventBus — publish/subscribe

```python
class EventBus:
    def subscribe(self, event_type: str, handler: Callable[[AgentEvent], None]) -> None
    def publish(self, event: AgentEvent) -> None
```

- Handlers registered by event type string.
- `publish()` calls all matching handlers synchronously.
- StateMachine injects EventBus via constructor. If EventBus is None, emit is a no-op (backward compat for tests).
- Session owns the EventBus instance and subscribes TerminalRenderer + Tracer.

### StateMachine changes — emit points

Each `_on_*` method gets one `self.emit(...)` call. No transition logic changes, no new states.

```python
# Before
def _on_llm_call(self) -> None:
    messages = self._context_builder.build(self.state)
    response = self.llm.generate(messages)
    ...

# After
def _on_llm_call(self) -> None:
    self.emit(AgentEvent(type="LLM_START", ...))
    messages = self._context_builder.build(self.state)
    response = self.llm.generate(messages)
    self.emit(AgentEvent(type="LLM_END", ...))
    ...
```

`self.emit()` is a no-op when `self._event_bus is None`.

---

## Renderer Migration

### TerminalRenderer becomes an EventBus subscriber

```python
class TerminalRenderer(Renderer):
    def __init__(self, event_bus: EventBus | None = None, ...):
        ...
        if event_bus:
            event_bus.subscribe("LLM_START", self._on_llm_start)
            event_bus.subscribe("LLM_END", self._on_llm_end)
            event_bus.subscribe("TOOL_START", self._on_tool_start)
            event_bus.subscribe("TOOL_END", self._on_tool_end)
            event_bus.subscribe("ACTION_CREATED", self._on_action_created)
            event_bus.subscribe("GUARDRAIL_DENY", self._on_guardrail_deny)
            event_bus.subscribe("FEEDBACK_COMPLETED", self._on_feedback_completed)
            event_bus.subscribe("AGENT_STOP", self._on_agent_stop)
```

### Output compatibility

The text output format after migration matches the current output. Events carry the same data that `_print()` currently uses. The renderer methods transform events back to text lines that pass existing `capsys` test assertions.

### Test migration

```python
# Old: assert on stdout
result = capsys.readouterr()
assert "[TOOL_EXEC]" in result.out

# New: assert on rendered event
event = AgentEvent(type="TOOL_START", payload={"tool": "shell", ...})
renderer._on_tool_start(event)
result = capsys.readouterr()
assert "shell" in result.out
```

---

## File Structure

```
src/ai4se_agent/
├── core/
│   ├── state_machine.py   [MODIFY] add emit() to each _on_*
│   ├── agent_state.py     [MODIFY] add_user_message()
│   ├── events.py          [NEW]     EventType enum + AgentEvent dataclass
│   └── event_bus.py       [NEW]     EventBus with subscribe/publish
│
├── session/
│   ├── __init__.py
│   ├── session.py         [NEW]     Session + AgentRuntime
│   └── history.py         [NEW]     MessageHistory
│
├── cli/
│   ├── session.py         [MODIFY]  interactive() uses Session
│   ├── main.py            [MODIFY]  pass EventBus to Session
│   └── renderer.py        [MODIFY]  TerminalRenderer subscribes to EventBus
│
└── tests/
    ├── core/
    │   ├── test_events.py      [NEW]
    │   └── test_event_bus.py   [NEW]
    ├── session/
    │   ├── test_session.py     [NEW]
    │   └── test_history.py     [NEW]
    ├── cli/
    │   └── test_renderer.py    [MODIFY] event-driven assertions
    └── ...
```

---

## Non-Goals

- Rich UI / colors / markdown rendering
- Streaming token output
- Human interrupt (`/stop` mid-execution)
- Async agent execution
- Multi-agent coordination

---

## Test Strategy

| Test file | What it covers |
|-----------|---------------|
| `test_events.py` | AgentEvent creation, to_dict/from_dict, all 14 event types have correct payload fields |
| `test_event_bus.py` | subscribe, publish dispatches to correct handler, multiple subscribers per event, unsubscribe |
| `test_session.py` | history accumulates across turns, Runtime is isolated per turn, single-task mode unchanged |
| `test_history.py` | add/get_recent ordering, add_turn atomicity, n=20 truncation, clear |
| `test_renderer.py` | event-driven assertions replace capsys-on-fsm assertions, output format unchanged |

All existing 131 tests must pass with the migrated TerminalRenderer.

---

## Key Design Decisions

1. **Session owns history, AgentRuntime owns AgentState.** Prevents semantic conflict where `goal` (current task) and `history` (prior conversation) get mixed in the same object.
2. **EventBus is optional.** `self.emit()` no-ops when `_event_bus is None`. Existing tests that construct StateMachine directly don't break.
3. **SESSION_START/END emitted by Session, not StateMachine.** StateMachine doesn't know about session lifecycle — it only knows about agent execution boundaries (AGENT_START/STOP).
4. **FEEDBACK_COMPLETED replaces FEEDBACK_RESULT.** Event name describes behavior, not outcome. Success/failure is in the payload.
5. **TerminalRenderer subscribes to events, doesn't poll.** Each relevant event type has a handler method. Output format matches current behavior for test compatibility.
