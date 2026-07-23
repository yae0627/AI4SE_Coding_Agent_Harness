# Context Engineering & Observability Enhancement Design

> 2026-07-23 | Status: Design Approved

## Overview

Two independent enhancement tracks on the AI4SE agent harness:

- **B. Context Engineering** — Split monolithic system prompt into composable sections, add dynamic workspace context, remove redundant workflow text
- **C. Observability** — Enhance Renderer with token/timing info, enrich Trace with timestamps and structured replay

B and C share no code dependencies and can be implemented in parallel.

---

## B. Context Engineering

### B.1 Prompt Section Architecture

**Current state** (`prompt.py`): single `build_system_prompt(schemas)` returns one monolithic string mixing tool descriptions, format instructions, examples, and role text.

**Target**: modular sections composed by `PromptComposer`:

```
ContextBuilder.build()
    │
    ├─ WorkspaceCollector.collect() → WorkspaceSnapshot
    ├─ MemoryManager.get_rules() → list[str]
    │
    └─ PromptComposer.compose(ctx)
        ├─ SystemRoleSection
        ├─ ToolSection          ← ctx.tools
        ├─ FormatSection
        ├─ ExampleSection
        ├─ WorkspaceSection     ← ctx.workspace
        └─ RulesSection         ← ctx.rules
```

**New files:**

```
context/
├── prompt_context.py     [NEW]  PromptContext dataclass
├── prompt_section.py     [NEW]  PromptSection ABC
├── prompt_composer.py    [NEW]  PromptComposer orchestrator
├── sections/             [NEW]
│   ├── __init__.py
│   ├── system_role.py
│   ├── tool_section.py
│   ├── format_section.py
│   ├── example_section.py
│   ├── workspace_section.py
│   └── rules_section.py
├── workspace.py          [NEW]  WorkspaceCollector + WorkspaceSnapshot
├── prompt.py             [MODIFY]  Keep build_tool_descriptions(), remove build_system_prompt()
└── builder.py            [MODIFY]  Use PromptComposer instead of build_system_prompt()
```

**`PromptContext`** (`prompt_context.py`):

```python
@dataclass
class PromptContext:
    tools: list[dict]                    # ToolRegistry.list_schemas()
    goal: str                            # AgentState.goal
    workspace: WorkspaceSnapshot | None  # from WorkspaceCollector
    rules: list[str]                     # from MemoryManager.get_rules()
    feedback: list[dict]                 # active correction feedback
```

**`PromptSection`** ABC (`prompt_section.py`):

```python
class PromptSection(ABC):
    """A composable prompt section that builds its portion from PromptContext."""
    @abstractmethod
    def build(self, ctx: PromptContext) -> str: ...
```

**`PromptComposer`** (`prompt_composer.py`):

```python
class PromptComposer:
    def __init__(self, sections: list[PromptSection]): ...
    def compose(self, ctx: PromptContext) -> str:
        # join sections with "\n\n", skip empty sections
```

**6 Sections:**

| Section | Input | Output |
|---------|-------|--------|
| `SystemRoleSection` | (static) | `"You are a coding agent..."` |
| `ToolSection` | `ctx.tools` | `"## Tools\n- read_file: ..."` |
| `FormatSection` | (static) | JSON format + `\"` escaping rules |
| `ExampleSection` | (static) | Few-shot examples (write_file→shell→finish) |
| `WorkspaceSection` | `ctx.workspace` | `"## Environment\nOS: win32\n..."` |
| `RulesSection` | `ctx.rules` | `"## Rules\n- ..."` (empty if no rules) |

**`ContextBuilder` change:**

```python
# Before
build_system_prompt(self._schemas)

# After
self._composer.compose(PromptContext(
    tools=self._schemas, workspace=ws, rules=rules,
    goal=state.goal, feedback=state.feedback
))
```

### B.2 Workflow Optimization

Remove any residual "Workflow: To complete a task, use tools to..." text from the prompt. The FSM already encodes this logic:

```
CONTEXT_ORG → LLM_CALL → ACTION_PARSE → GUARDRAIL → TOOL_EXEC → FEEDBACK → MEMORY_UPDATE
```

Feedback-driven `CorrectionPlan` injection is a code mechanism, not a prompt text substitute.

### B.3 Workspace Context

**`WorkspaceSnapshot`** (`workspace.py`):

```python
@dataclass(frozen=True)
class WorkspaceSnapshot:
    os: str              # sys.platform
    cwd: str             # Path.cwd().resolve()
    git_branch: str      # from subprocess or "unknown"
    files: list[str]     # summarized file listing
    timestamp: str       # ISO 8601
```

**`WorkspaceCollector`** (`workspace.py`):

```python
class WorkspaceCollector:
    def __init__(self, workspace_root: str, max_files: int = 50):
        self._root = Path(workspace_root)
        self._max_files = max_files
        self._cache: WorkspaceSnapshot | None = None
        self._cache_ttl: float = 5.0
        self._last_collect: float = 0.0

    def collect(self, force: bool = False) -> WorkspaceSnapshot: ...
    def invalidate(self) -> None: ...
    def _summarize_files(self) -> list[str]: ...
        # Skip: .git, __pycache__, *.pyc, node_modules, .pytest_cache
        # Truncate with "... and N more files" when exceeding max_files
```

**Integration point:** `SessionManager._build_harness()` creates `WorkspaceCollector`, passes it to `ContextBuilder`. `ContextBuilder.build()` calls `collector.collect()` before composing.

---

## C. Observability

### C.1 Renderer Enhancement

**New abstract methods on `Renderer` ABC:**

```python
@abstractmethod
def on_token_usage(self, iteration: int, prompt_tokens: int, completion_tokens: int) -> None: ...

@abstractmethod
def on_timing(self, state_name: str, elapsed_ms: float) -> None: ...
```

**`TerminalRenderer` changes:**

| Method | Before | After |
|--------|--------|-------|
| `on_llm_call` | `response[:200]` (verbose only) | `response[:500]` verbose; `response[:200]` non-verbose |
| `on_tool_exec` | `output[:300]` (verbose/failure only) | `output[:max_output]` with configurable `max_output=500` |
| `on_stop` | `STOP: {reason} after {N} iterations` | `STOP: {reason} | {N} iters | {total_tokens} tokens | {total_elapsed:.1f}s` |
| `on_token_usage` | N/A | `token: {prompt}↑/{completion}↓` |
| `on_timing` | N/A | `[{state}] {elapsed_ms}ms` (verbose only) |

**`NullRenderer`**: add empty implementations for new methods.

### C.2 Trace Enhancement

**`Event` base class** — add `timestamp` and `elapsed_ms` fields:

```python
@dataclass
class Event:
    type: EventType
    iteration: int
    timestamp: str = ""       # ISO 8601, set on record()
    elapsed_ms: float = 0.0   # ms from tracer start_time to event
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "iteration": self.iteration,
            "timestamp": self.timestamp,
            "elapsed_ms": self.elapsed_ms,
            **self.data,
        }
```

**`Tracer` enhancements:**

```python
class Tracer:
    def __init__(self):
        self._events: list[Event] = []
        self._start_time: float = time.time()
        self._token_usage: dict[str, int] = {"prompt": 0, "completion": 0}

    def record(self, event: Event) -> None:
        event.timestamp = datetime.datetime.now().isoformat()
        event.elapsed_ms = (time.time() - self._start_time) * 1000
        self._events.append(event)

    def record_token(self, prompt: int, completion: int) -> None: ...

    def replay_filtered(self, path: str, *, event_type: str | None = None,
                        min_iteration: int = 0) -> list[dict]: ...
```

---

## Non-Goals

- No dependency injection framework or prompt AST compiler
- No hot-reload of prompt sections (sections are static at runtime)
- No LLM-based few-shot example selection (future work)
- No distributed tracing or external observability backend

## Test Strategy

- **B.1**: Unit test each Section with mock `PromptContext`; integration test `PromptComposer.compose()` with all sections
- **B.2**: Verify no workflow text in composed prompt output
- **B.3**: Unit test `WorkspaceCollector` with temp directory; test cache invalidation; test file summarization truncation
- **C.1**: Unit test `on_token_usage`/`on_timing` call count; test `on_stop` format string
- **C.2**: Unit test `Event.to_dict()` includes new fields; test `replay_filtered()` filtering logic

All existing 90 tests must remain green.
