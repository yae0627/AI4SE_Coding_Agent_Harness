# Communication Channel & Session Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decouple communication (message) from execution (action) in the agent's response protocol, unify session history as a complete message store, and upgrade the Renderer to display agent messages in real-time.

**Architecture:** Four sequential phases. Phase 1 unifies `ConversationMemory` as the single message store — full turn history, no lossy summaries. Phase 2 upgrades the LLM response protocol so one turn can carry both a `message` (rendered via EventBus) and an `action` (processed by FSM). Phase 3 removes the `RESPOND` FSM state, replacing it with `ask` action → `WAIT_INPUT`. Phase 4 upgrades `TerminalRenderer` to display `LLM_MESSAGE` events inline.

**Tech Stack:** Python 3.10+, `transitions` FSM, EventBus (existing), `dataclasses`

---

## File Map

| Phase | Create | Modify | Delete |
|-------|--------|--------|--------|
| 1 | — | `session/history.py`, `session/session.py`, `core/agent_state.py` | — |
| 2 | — | `core/action.py`, `types.py`, `core/state_machine.py`, `context/sections/format_section.py` | — |
| 3 | — | `core/state_machine.py`, `core/action_schema.py`, `core/action.py`, `cli/session.py` | — |
| 4 | — | `cli/renderer.py` | — |

---

### Task 1.1: Add `type` field to ConversationMemory messages

**Files:**
- Modify: `src/ai4se_agent/session/history.py`
- Test: `tests/session/test_history.py`

- [ ] **Step 1: Write failing test for typed messages**

```python
def test_append_typed_action_message():
    mem = ConversationMemory()
    mem.append("assistant", '{"action":"read_file","parameters":{"path":"x.txt"}}', type="action")
    msg = mem.get_recent()[0]
    assert msg["role"] == "assistant"
    assert msg["type"] == "action"

def test_append_typed_message():
    mem = ConversationMemory()
    mem.append("assistant", "I will read the file now.", type="message")
    msg = mem.get_recent()[0]
    assert msg["type"] == "message"

def test_append_defaults_to_text():
    mem = ConversationMemory()
    mem.append("user", "hello")
    assert mem.get_recent()[0].get("type") == "text"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/session/test_history.py::test_append_typed_action_message tests/session/test_history.py::test_append_typed_message tests/session/test_history.py::test_append_defaults_to_text -v`
Expected: FAIL — `type` key not present

- [ ] **Step 3: Update `ConversationMemory.append` signature**

```python
def append(self, role: str, content: str, metadata: dict | None = None, type: str = "text") -> None:
    msg: dict = {"role": role, "content": content, "type": type}
    if metadata:
        msg["metadata"] = metadata
    self._messages.append(msg)
```

Note: `extend()` passes through existing dict keys unchanged, so no change needed there.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/session/test_history.py -v`
Expected: all PASS (new tests + 10 existing)

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/session/history.py tests/session/test_history.py
git commit -m "feat: add type field to ConversationMessage messages

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 1.2: Sync AgentState.history back to ConversationMemory after run

**Files:**
- Modify: `src/ai4se_agent/session/session.py`
- Test: `tests/session/test_session.py`

- [ ] **Step 1: Write failing test**

```python
def test_conversation_memory_records_full_turn_history():
    """After AgentRuntime.run(), ConversationMemory contains assistant+tool messages, not a summary."""
    from ai4se_agent.session.session import AgentRuntime
    from ai4se_agent.session.history import ConversationMemory

    bus = EventBus()
    mem = ConversationMemory()
    config = ConfigLoader()
    config.set("provider", "name", "mock")

    runtime = AgentRuntime(goal="read a file", memory=mem, config=config, event_bus=bus)
    result = runtime.run()

    messages = mem.get_all()
    roles = [m["role"] for m in messages]
    types = [m.get("type", "text") for m in messages]

    # Should have assistant (action) and tool messages, not a "success" summary
    assert "assistant" in roles, f"expected assistant in roles, got {roles}"
    assert "tool" in roles, f"expected tool in roles, got {roles}"
    # Should NOT be a lossy "Task completed: success"
    contents = " ".join(str(m.get("content", "")) for m in messages)
    assert "Task completed" not in contents, f"found lossy summary: {contents}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/session/test_session.py::test_conversation_memory_records_full_turn_history -v`
Expected: FAIL — "tool" not in roles (currently history is discarded, memory only gets summary)

- [ ] **Step 3: Update `AgentRuntime.run()` to sync history back**

In `src/ai4se_agent/session/session.py`, change the end of `AgentRuntime.run()`:

Current (lines 83-86):
```python
        result = machine.run()
        new_messages = self._state.history[history_start:]
        self._memory.extend(new_messages)
        return result
```

Change to:
```python
        result = machine.run()

        # Sync full turn history back to ConversationMemory
        # Tag assistant messages that carry raw LLM output as type="action"
        new_messages = self._state.history[history_start:]
        for msg in new_messages:
            if msg["role"] == "assistant" and "type" not in msg:
                msg["type"] = "action"  # legacy: raw LLM response = action format
        self._memory.extend(new_messages)
        return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/session/test_session.py -v`
Expected: all PASS

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -q`
Expected: all 201+ tests pass

- [ ] **Step 6: Commit**

```bash
git add src/ai4se_agent/session/session.py tests/session/test_session.py
git commit -m "feat: sync full turn history to ConversationMemory after run

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 1.3: Remove MemoryManager.session — use ConversationMemory directly

**Files:**
- Modify: `src/ai4se_agent/memory/manager.py`
- Modify: `src/ai4se_agent/core/agent_state.py` (minor — needs no change, just verify)
- Test: `tests/memory/test_manager.py`

- [ ] **Step 1: Remove `session` from MemoryManager**

Current `MemoryManager.__init__`:
```python
def __init__(
    self,
    session: ConversationMemory | None = None,
    persistent: PersistentMemory | None = None,
    failure_log_dir: str | None = None,
):
    self.session = session or ConversationMemory()
```

Change to:
```python
def __init__(
    self,
    persistent: PersistentMemory | None = None,
    failure_log_dir: str | None = None,
):
```

Remove the `from ai4se_agent.session.history import ConversationMemory` import at the top.

- [ ] **Step 2: Update tests that reference `manager.session`**

In `tests/memory/test_manager.py`, find tests that reference `manager.session` and update them:

```python
# test_manager_aggregates_conversation_and_persistent
# Remove the ConversationMemory check — MemoryManager no longer owns one
def test_manager_aggregates_conversation_and_persistent():
    persistent = PersistentMemory()
    manager = MemoryManager(persistent=persistent)
    assert manager.persistent is persistent
    # Manager no longer owns conversation memory — Session owns it directly

def test_manager_get_rules_empty_when_no_rules():
    persistent = PersistentMemory()
    manager = MemoryManager(persistent=persistent)
    assert manager.get_rules() == []

def test_manager_get_rules_sorted():
    persistent = PersistentMemory()
    persistent.save_rule("b_rule", "second")
    persistent.save_rule("a_rule", "first")
    manager = MemoryManager(persistent=persistent)
    rules = manager.get_rules()
    assert rules == ["first", "second"]

def test_manager_log_failure():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        manager = MemoryManager(failure_log_dir=d)
        entry = {"type": "test", "message": "oops"}
        fid = manager.log_failure(entry)
        assert fid is not None
        failures = manager.list_failures()
        assert len(failures) >= 1

def test_manager_no_failure_dir_no_op():
    manager = MemoryManager()
    fid = manager.log_failure({"msg": "test"})
    assert fid is None
    assert manager.list_failures() == []
```

- [ ] **Step 3: Run memory tests**

Run: `pytest tests/memory/test_manager.py tests/memory/test_persistent.py -v`
Expected: all PASS

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -q`
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/memory/manager.py tests/memory/test_manager.py
git commit -m "refactor: remove session from MemoryManager, Session owns ConversationMemory directly

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2.1: Upgrade ParseResult and ActionParser for message+action protocol

**Files:**
- Modify: `src/ai4se_agent/types.py`
- Modify: `src/ai4se_agent/core/action.py`
- Test: `tests/core/test_action_json.py`

- [ ] **Step 1: Add `message` field to `ParseResult`**

In `src/ai4se_agent/types.py`:

```python
@dataclass
class ParseResult:
    success: bool
    action: Optional["Action"] = None
    message: Optional[str] = None
    error: Optional[str] = None
```

- [ ] **Step 2: Write failing test for message+action parsing**

Add to `tests/core/test_action_json.py`:

```python
def test_parse_message_with_action():
    parser = ActionParser()
    text = '{"message": "I will now read the file.", "action": {"name": "read_file", "parameters": {"path": "test.txt"}}}'
    result = parser.parse(text)
    assert result.success is True
    assert result.message == "I will now read the file."
    assert result.action.name == "read_file"
    assert result.action.parameters["path"] == "test.txt"

def test_parse_action_only_no_message():
    parser = ActionParser()
    text = '{"action": {"name": "shell", "parameters": {"command": "ls"}}}'
    result = parser.parse(text)
    assert result.success is True
    assert result.message is None
    assert result.action.name == "shell"

def test_parse_message_only_no_action():
    parser = ActionParser()
    text = '{"message": "Hello, how can I help?"}'
    result = parser.parse(text)
    assert result.success is True
    assert result.message == "Hello, how can I help?"
    assert result.action is None

def test_parse_finish_with_message():
    parser = ActionParser()
    text = '{"message": "Analysis complete. Found 3 issues.", "action": {"name": "finish", "parameters": {}}}'
    result = parser.parse(text)
    assert result.success is True
    assert result.message == "Analysis complete. Found 3 issues."
    assert result.action.name == "finish"

def test_parse_message_with_escaped_quotes():
    parser = ActionParser()
    text = '{"message": "Found issue in \\"auth.py\\"", "action": {"name": "finish", "parameters": {}}}'
    result = parser.parse(text)
    assert result.success is True
    assert 'Found issue in "auth.py"' in result.message
```

Run: `pytest tests/core/test_action_json.py::test_parse_message_with_action tests/core/test_action_json.py::test_parse_action_only_no_message tests/core/test_action_json.py::test_parse_message_only_no_action tests/core/test_action_json.py::test_parse_finish_with_message tests/core/test_action_json.py::test_parse_message_with_escaped_quotes -v`
Expected: FAIL — no `message` field in ParseResult yet

- [ ] **Step 3: Update `_try_json` to extract message**

In `src/ai4se_agent/core/action.py`, modify the `_try_json` method around line 162:

Current:
```python
        if "action" not in obj:
            return ParseResult(success=False, error="Missing 'action' field in JSON")
        return ParseResult(
            success=True,
            action=Action(name=obj["action"], parameters=obj.get("parameters", {}))
        )
```

Change to:
```python
        # Extract optional message from the response
        message = obj.get("message")

        # Action is optional — message-only responses are valid
        action = None
        if "action" in obj:
            action = Action(
                name=obj["action"],
                parameters=obj.get("parameters", {})
            )

        if message is None and action is None:
            return ParseResult(success=False, error="Response must have 'message' and/or 'action' field")

        return ParseResult(success=True, action=action, message=message)
```

- [ ] **Step 4: Update `LegacyActionParser` for backward compat**

In `LegacyActionParser.parse()`, the existing logic already handles `action: respond message="..."` which maps to the old respond format. No change needed for Phase 2 — legacy fallback continues to produce actions only (message=None).

- [ ] **Step 5: Update `parse()` method to propagate message**

In `ActionParser.parse()`:

Current:
```python
    def parse(self, text: str) -> ParseResult:
        result = self._try_json(text)
        if result.success:
            return result
        if self._fallback:
            action = self._legacy.parse(text)
            if action:
                return ParseResult(success=True, action=action)
        return result
```

No change needed — `_try_json` already handles message, and legacy fallback returns action-only (message=None).

- [ ] **Step 6: Run tests**

Run: `pytest tests/core/test_action_json.py -v`
Expected: all PASS (existing + 5 new)

- [ ] **Step 7: Run full test suite**

Run: `pytest tests/ -q`
Expected: all existing tests still pass (ParseResult.message=None is backward compatible)

- [ ] **Step 8: Commit**

```bash
git add src/ai4se_agent/types.py src/ai4se_agent/core/action.py tests/core/test_action_json.py
git commit -m "feat: add optional message field to ParseResult for message+action protocol

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2.2: Emit LLM_MESSAGE event from state machine when message is present

**Files:**
- Modify: `src/ai4se_agent/core/state_machine.py`
- Test: `tests/core/test_state_machine.py`

- [ ] **Step 1: Write failing test for LLM_MESSAGE event**

```python
def test_llm_message_event_emitted():
    bus = EventBus()
    message_events = []
    bus.subscribe("LLM_MESSAGE", lambda e: message_events.append(e.payload))

    llm = MockAdapter(responses=[
        '{"message": "Let me check the file.", "action": {"name": "read_file", "parameters": {"path": "test.txt"}}}',
        '{"action": {"name": "finish", "parameters": {}}}',
    ])
    registry = ToolRegistry()
    registry.register(ReadFileTool())

    sm = HarnessStateMachine(
        agent_state=AgentState(goal="test message"),
        llm_adapter=llm, action_parser=ActionParser(),
        action_validator=ActionValidator(), tool_registry=registry,
        guardrail_engine=GuardrailEngine(), feedback_loop=None,
        max_iterations=5, event_bus=bus, interactive=False,
    )
    sm.run()
    assert len(message_events) == 1
    assert "Let me check the file" in message_events[0]["message"]


def test_llm_message_finish_with_message():
    bus = EventBus()
    message_events = []
    bus.subscribe("LLM_MESSAGE", lambda e: message_events.append(e.payload))

    llm = MockAdapter(responses=[
        '{"message": "Analysis complete. Found 3 bugs.", "action": {"name": "finish", "parameters": {}}}',
    ])
    sm = HarnessStateMachine(
        agent_state=AgentState(goal="test finish message"),
        llm_adapter=llm, action_parser=ActionParser(),
        action_validator=ActionValidator(), tool_registry=ToolRegistry(),
        guardrail_engine=GuardrailEngine(), feedback_loop=None,
        max_iterations=5, event_bus=bus, interactive=False,
    )
    sm.run()
    assert len(message_events) == 1
    assert "Analysis complete" in message_events[0]["message"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_state_machine.py::test_llm_message_event_emitted tests/core/test_state_machine.py::test_llm_message_finish_with_message -v`
Expected: FAIL — no LLM_MESSAGE event emitted

- [ ] **Step 3: Update `_on_action_parse` to emit LLM_MESSAGE and handle message-only responses**

Replace the `_on_action_parse` method in `state_machine.py`:

```python
    def _on_action_parse(self) -> None:
        last_msg = self.state.history[-1]["content"]
        result = self.parser.parse(last_msg)
        if not result.success:
            self.state.record_feedback(
                f"Your last response could not be parsed as a valid action. "
                f"Error: {result.error}. "
                f"Please respond with a JSON object: "
                f'{{"message": "<optional text>", "action": {{"name": "<tool_name>", "parameters": {{...}}}}}}. '
                f"Make sure all double quotes inside string values are escaped with backslash (\\\")."
            )
            self.retry_parse()
            return

        # Emit message if present (before action processing)
        if result.message:
            self._emit("LLM_MESSAGE", {"message": result.message})

        # Message-only response (no action) → loop back for next action
        if result.action is None:
            self.retry_parse()
            return

        action = result.action
        if action.name == "finish":
            self.stop_reason = StopReason.SUCCESS
            self.stop()
            return
        if action.name == "respond":
            self._pending_action = action
            self._emit("LLM_MESSAGE", {"message": action.parameters.get("message", "")})
            self.respond_to_user()
            return
        errors = self.validator.validate(action)
        if errors:
            self.state.record_feedback(
                f"Action validation failed: {'; '.join(errors)}. "
                f"Please fix the missing or incorrect parameters and try again."
            )
            self.retry_parse()
            return
        self._pending_action = action
        self._emit("ACTION_CREATED", {"action_name": action.name, "parameters": dict(action.parameters)})
        self._tracer.record(
            ActionEvent(self.state.iteration, action.name, action.parameters)
        )
        self.check_guardrails()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/core/test_state_machine.py -v`
Expected: all PASS (existing 6 + 2 new)

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -q`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add src/ai4se_agent/core/state_machine.py tests/core/test_state_machine.py
git commit -m "feat: emit LLM_MESSAGE event when response has message field

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2.3: Update FormatSection prompt to teach LLM the new protocol

**Files:**
- Modify: `src/ai4se_agent/context/sections/format_section.py`
- Test: `tests/context/test_prompt_section.py`

- [ ] **Step 1: Write failing test for new format in prompt output**

```python
def test_format_section_includes_message_field():
    from ai4se_agent.context.prompt_section import PromptSection
    from ai4se_agent.context.prompt_context import PromptContext
    from ai4se_agent.context.sections.format_section import FormatSection

    ctx = PromptContext(tools=[], goal="test", workspace=None, rules=[], feedback=[])
    section = FormatSection()
    output = section.build(ctx)

    # New format: message field should be mentioned
    assert '"message"' in output, "prompt should teach LLM about optional message field"
    # Old respond action should still be mentioned (backward compat, removed in Phase 3)
    # Action is now a nested object, not a top-level string
    assert '"action"' in output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/context/test_prompt_section.py::test_format_section_includes_message_field -v`
Expected: FAIL — `"message"` not found in prompt

- [ ] **Step 3: Update FormatSection**

Replace the entire `build()` method:

```python
    def build(self, ctx: PromptContext) -> str:
        return (
            "## Response Format\n\n"
            "Respond with exactly one JSON object per turn:\n\n"
            '  {\n'
            '    "message": "<optional: text to show the user>",\n'
            '    "action": {\n'
            '      "name": "<action_name>",\n'
            '      "parameters": {"key": "value"}\n'
            '    }\n'
            '  }\n\n'
            "The 'message' field is optional — include it when you want to explain "
            "your reasoning, report progress, or summarize results. "
            "Omit it for routine tool executions (read_file, shell, etc.).\n\n"
            "The 'action' field is optional — omit it when you only want to send a message. "
            "When both are present, the message is shown to the user before the action executes.\n\n"
            "Available action names are listed in Tools and Conversation sections above.\n\n"
            "Important rules:\n"
            "- Each response must contain at least one of 'message' or 'action'.\n"
            "- For multi-line content, use \\n for newlines inside JSON strings.\n"
            "- All double quotes inside string values MUST be escaped with backslash: \\\"\n"
            "- Example of properly escaped code string:\n"
            '  {"message": "Writing the C++ file", "action": {"name": "write_file", "parameters": {"path": "x.cpp", "content": "#include <iostream>\\\nint main() { std::cout << \\\"hi\\\"; }\\\n"}}}\n\n'
            "- To communicate with the user without executing a tool, send only a message:\n"
            '  {"message": "I found 3 potential issues in the codebase..."}\n\n'
            "- To finish the task, use the finish action:\n"
            '  {"message": "Task completed: all tests pass.", "action": {"name": "finish", "parameters": {}}}\n\n'
            "- To ask the user a question (and wait for their response), use the ask action:\n"
            '  {"action": {"name": "ask", "parameters": {"question": "Which file should I modify?"}}}'
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/context/test_prompt_section.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/context/sections/format_section.py tests/context/test_prompt_section.py
git commit -m "feat: update prompt format to teach LLM message+action protocol

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3.1: Replace RESPOND state with ask action → WAIT_INPUT

**Files:**
- Modify: `src/ai4se_agent/core/state_machine.py`
- Modify: `src/ai4se_agent/cli/session.py`
- Test: `tests/core/test_state_machine.py`

- [ ] **Step 1: Write failing tests for ask action and WAIT_INPUT**

```python
def test_ask_action_enters_wait_input():
    bus = EventBus()
    message_events = []
    bus.subscribe("LLM_MESSAGE", lambda e: message_events.append(e.payload))

    ch = InterruptChannel()
    llm = MockAdapter(responses=[
        '{"action": {"name": "ask", "parameters": {"question": "Which file?"}}}',
        '{"message": "Got it.", "action": {"name": "finish", "parameters": {}}}',
    ])
    registry = ToolRegistry()
    state = AgentState(goal="test ask")

    import threading
    def answer_later():
        import time
        time.sleep(0.05)
        ch.send_approval(True)  # reuse approval queue for input

    threading.Thread(target=answer_later, daemon=True).start()

    sm = HarnessStateMachine(
        agent_state=state, llm_adapter=llm,
        action_parser=ActionParser(), action_validator=ActionValidator(),
        tool_registry=registry, guardrail_engine=GuardrailEngine(),
        feedback_loop=None, max_iterations=5, event_bus=bus,
        interrupt=ch, interactive=False,
    )
    sm.run()
    # ask question should be emitted as LLM_MESSAGE
    assert len(message_events) >= 1
    assert "Which file?" in str(message_events[0])


def test_respond_action_still_works_as_message():
    """Backward compat: old respond action still emits LLM_MESSAGE."""
    bus = EventBus()
    message_events = []
    bus.subscribe("LLM_MESSAGE", lambda e: message_events.append(e.payload))

    llm = MockAdapter(responses=[
        '{"action": "respond", "parameters": {"message": "old style message"}}',
        '{"action": {"name": "finish", "parameters": {}}}',
    ])
    sm = HarnessStateMachine(
        agent_state=AgentState(goal="backward compat"),
        llm_adapter=llm, action_parser=ActionParser(),
        action_validator=ActionValidator(), tool_registry=ToolRegistry(),
        guardrail_engine=GuardrailEngine(), feedback_loop=None,
        max_iterations=5, event_bus=bus, interactive=False,
    )
    sm.run()
    assert len(message_events) >= 1
    assert "old style message" in str(message_events[0])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/core/test_state_machine.py::test_ask_action_enters_wait_input tests/core/test_state_machine.py::test_respond_action_still_works_as_message -v`
Expected: FAIL — ask not handled, RESPOND state still activates

- [ ] **Step 3: Update FSM — remove RESPOND state, add WAIT_INPUT**

In `HarnessStateMachine`:

Change the `states` list (remove "RESPOND"):
```python
    states = [
        "IDLE", "CONTEXT_ORG", "LLM_CALL", "ACTION_PARSE",
        "GUARDRAIL", "WAIT_APPROVAL", "WAIT_INPUT", "TOOL_EXEC", "TOOL_ERROR",
        "FEEDBACK", "MEMORY_UPDATE", "STOP"
    ]
```

Change transitions (remove respond-related, add ask-related):
```python
        # Remove:
        # self.machine.add_transition("respond_to_user", "ACTION_PARSE", "RESPOND", after="_on_respond")
        # self.machine.add_transition("continue_after_respond", "RESPOND", "CONTEXT_ORG", after="_on_context_org")

        # Add:
        self.machine.add_transition("request_input", "ACTION_PARSE", "WAIT_INPUT", after="_on_wait_input")
        self.machine.add_transition("input_received", "WAIT_INPUT", "CONTEXT_ORG", after="_on_context_org")
```

Remove `_on_respond` method, add `_on_wait_input`:

```python
    def _on_wait_input(self) -> None:
        """Wait for user response to an ask action."""
        assert self._pending_action is not None
        question = self._pending_action.parameters.get("question", "")
        if self._interactive:
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                self.stop_reason = StopReason.USER_CANCEL
                self.stop()
                return
            if user_input:
                self.state.record_feedback(user_input)
                self.state.history.append({"role": "user", "content": user_input})
        self.input_received()
```

Update `_on_action_parse` to handle ask:

At the top of the action dispatch section, add ask handling before the respond backward-compat block:

```python
        if action.name == "ask":
            self._pending_action = action
            self._emit("LLM_MESSAGE", {"message": action.parameters.get("question", "")})
            self.request_input()
            return
```

- [ ] **Step 4: Run all state machine tests**

Run: `pytest tests/core/test_state_machine.py -v`
Expected: all PASS (adjust existing respond tests if needed)

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -q`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add src/ai4se_agent/core/state_machine.py tests/core/test_state_machine.py
git commit -m "refactor: replace RESPOND state with ask action -> WAIT_INPUT

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3.2: Update control schemas — remove respond, add ask

**Files:**
- Modify: `src/ai4se_agent/core/action_schema.py`
- Test: `tests/tools/test_schema.py`

- [ ] **Step 1: Replace respond with ask in CONTROL_SCHEMAS**

```python
CONTROL_SCHEMAS = [
    {
        "name": "ask",
        "_category": "control",
        "description": "Ask the user a question and wait for their response. Use this when you need clarification, a decision, or additional information before proceeding.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The question to ask the user"}
            },
            "required": ["question"]
        }
    },
    {
        "name": "finish",
        "_category": "control",
        "description": "Complete the current task. Use the message field to summarize what was accomplished.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
]
```

- [ ] **Step 2: Run schema tests**

Run: `pytest tests/tools/test_schema.py -v`
Expected: all PASS

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -q`
Expected: all tests pass

- [ ] **Step 4: Commit**

```bash
git add src/ai4se_agent/core/action_schema.py tests/tools/test_schema.py
git commit -m "refactor: replace respond with ask in control schemas

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4.1: Add LLM_MESSAGE handler to TerminalRenderer

**Files:**
- Modify: `src/ai4se_agent/cli/renderer.py`
- Test: `tests/cli/test_renderer.py`

- [ ] **Step 1: Write failing test for LLM_MESSAGE rendering**

```python
def test_renderer_llm_message_event(capsys):
    r = TerminalRenderer()
    event = AgentEvent(
        type="LLM_MESSAGE", iteration=1, state="ACTION_PARSE",
        payload={"message": "I will now analyze the codebase structure."},
    )
    r._on_llm_message(event)
    captured = capsys.readouterr()
    assert "analyze the codebase" in captured.out

def test_renderer_llm_message_multiline(capsys):
    r = TerminalRenderer()
    event = AgentEvent(
        type="LLM_MESSAGE", iteration=2, state="ACTION_PARSE",
        payload={"message": "Found 3 issues:\n1. Missing import\n2. Typo in auth.py\n3. Unused variable"},
    )
    r._on_llm_message(event)
    captured = capsys.readouterr()
    assert "Missing import" in captured.out
    assert "auth.py" in captured.out

def test_renderer_subscribe_includes_llm_message():
    from ai4se_agent.core.event_bus import EventBus
    bus = EventBus()
    r = TerminalRenderer(event_bus=bus)
    # Should have registered LLM_MESSAGE handler
    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        bus.publish(AgentEvent(
            type="LLM_MESSAGE", iteration=1, state="ACTION_PARSE",
            payload={"message": "test message"}
        ))
        output = captured.getvalue()
        assert "test message" in output
    finally:
        sys.stdout = old_stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/cli/test_renderer.py::test_renderer_llm_message_event tests/cli/test_renderer.py::test_renderer_llm_message_multiline tests/cli/test_renderer.py::test_renderer_subscribe_includes_llm_message -v`
Expected: FAIL — `_on_llm_message` not found / no handler registered

- [ ] **Step 3: Add `_on_llm_message` handler and wire it in `__init__`**

In `TerminalRenderer.__init__`, add subscription:
```python
            event_bus.subscribe("LLM_MESSAGE", self._on_llm_message)
```

Add the handler method:
```python
    def _on_llm_message(self, event: AgentEvent) -> None:
        message = event.payload.get("message", "")
        if not message:
            return
        for line in message.splitlines():
            self._print(f"  {line}")
```

Update `_on_respond_event` to delegate (backward compat for old RESPOND events):
```python
    def _on_respond_event(self, event: AgentEvent) -> None:
        # Backward compat: old RESPOND events → treat as LLM_MESSAGE
        self._on_llm_message(event)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/cli/test_renderer.py -v`
Expected: all PASS

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -q`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add src/ai4se_agent/cli/renderer.py tests/cli/test_renderer.py
git commit -m "feat: add LLM_MESSAGE handler to TerminalRenderer

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4.2: Update CLI session to wire LLM_MESSAGE event

**Files:**
- Modify: `src/ai4se_agent/cli/session.py`
- Test: `tests/cli/test_session.py`

- [ ] **Step 1: Add LLM_MESSAGE subscription in `_wire_renderer`**

In `SessionManager._wire_renderer`, add:
```python
    bus.subscribe("LLM_MESSAGE", self._renderer._on_llm_message)
```

- [ ] **Step 2: Run CLI session tests**

Run: `pytest tests/cli/test_session.py -v`
Expected: all PASS

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -q`
Expected: all tests pass

- [ ] **Step 4: Commit**

```bash
git add src/ai4se_agent/cli/session.py
git commit -m "feat: wire LLM_MESSAGE event to renderer in SessionManager

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Execution Order

Tasks must run sequentially in this order:
1.1 → 1.2 → 1.3 → 2.1 → 2.2 → 2.3 → 3.1 → 3.2 → 4.1 → 4.2

Each task is a self-contained commit. Run full test suite (`pytest tests/ -q`) after each task before committing.
