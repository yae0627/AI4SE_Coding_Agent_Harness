# Context Engineering & Observability Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split monolithic system prompt into composable sections with dynamic workspace context, enhance Renderer with token/timing info, and enrich Trace with timestamps and structured replay.

**Architecture:** `PromptComposer` orchestrates 6 `PromptSection` implementations fed by `PromptContext` dataclass. `WorkspaceCollector` provides OS/files/git snapshot with 5-second TTL cache. `Renderer` ABC gains `on_token_usage`/`on_timing` methods with `TerminalRenderer` concrete changes. `Event` base class gains `timestamp`/`elapsed_ms` fields auto-populated by `Tracer.record()`.

**Tech Stack:** Python 3.10+, pathlib, subprocess, json, time, datetime, dataclasses

## Global Constraints

- Python >=3.10
- All existing 90 tests must remain green
- B track (Tasks 1-4) and C track (Tasks 5-6) share no code dependencies — can be implemented in parallel
- Each new file gets a corresponding test file
- `PromptSection.build()` must not mutate `PromptContext`
- `WorkspaceSnapshot` is frozen (immutable)
- `Renderer` ABC changes require `NullRenderer` updates

---

### Task 1: PromptContext + PromptSection ABC

**Files:**
- Create: `src/ai4se_agent/context/prompt_context.py`
- Create: `src/ai4se_agent/context/prompt_section.py`
- Create: `tests/context/test_prompt_section.py`

**Interfaces:**
- Consumes: Nothing from this phase
- Produces: `PromptContext` dataclass, `PromptSection` ABC

- [ ] **Step 1: Write the failing tests**

```python
# tests/context/test_prompt_section.py
from ai4se_agent.context.prompt_context import PromptContext
from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.workspace import WorkspaceSnapshot


class _TestSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        return f"Tools: {len(ctx.tools)}, Goal: {ctx.goal}"


def test_prompt_context_defaults():
    ctx = PromptContext(tools=[], goal="test")
    assert ctx.tools == []
    assert ctx.goal == "test"
    assert ctx.workspace is None
    assert ctx.rules == []
    assert ctx.feedback == []


def test_prompt_context_with_all_fields():
    ws = WorkspaceSnapshot(
        os="win32", cwd="/tmp", git_branch="main",
        files=["a.py", "b.py"], timestamp="2026-07-23T00:00:00"
    )
    ctx = PromptContext(
        tools=[{"name": "shell"}],
        goal="build",
        workspace=ws,
        rules=["no rm -rf"],
        feedback=[{"role": "user", "content": "fix bug"}]
    )
    assert ctx.workspace.os == "win32"
    assert ctx.rules == ["no rm -rf"]
    assert len(ctx.feedback) == 1


def test_section_protocol():
    section = _TestSection()
    ctx = PromptContext(tools=[{"name": "x"}], goal="hi")
    result = section.build(ctx)
    assert "Tools: 1" in result
    assert "Goal: hi" in result


def test_prompt_context_immutable_pattern():
    """PromptContext fields should not be mutated by sections."""
    ctx = PromptContext(tools=[{"name": "x"}], goal="test")
    original_tools = list(ctx.tools)
    _TestSection().build(ctx)
    assert ctx.tools == original_tools
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/context/test_prompt_section.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Create src/ai4se_agent/context/prompt_context.py**

```python
from dataclasses import dataclass, field


@dataclass
class PromptContext:
    tools: list[dict]
    goal: str
    workspace: "WorkspaceSnapshot | None" = None
    rules: list[str] = field(default_factory=list)
    feedback: list[dict] = field(default_factory=list)
```

Note: `WorkspaceSnapshot` is forward-referenced as a string since it will be created in Task 3. The import goes in `prompt_composer.py` and `builder.py`, not here.

- [ ] **Step 4: Create src/ai4se_agent/context/prompt_section.py**

```python
from abc import ABC, abstractmethod
from ai4se_agent.context.prompt_context import PromptContext


class PromptSection(ABC):
    """A composable prompt section that builds its portion from PromptContext."""

    @abstractmethod
    def build(self, ctx: PromptContext) -> str:
        pass
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/context/test_prompt_section.py -v`
Expected: 4 PASS

- [ ] **Step 6: Commit**

```bash
git add src/ai4se_agent/context/prompt_context.py src/ai4se_agent/context/prompt_section.py tests/context/test_prompt_section.py
git commit -m "feat: add PromptContext dataclass and PromptSection ABC"
```

---

### Task 2: 6 Section Implementations + PromptComposer

**Files:**
- Create: `src/ai4se_agent/context/sections/__init__.py`
- Create: `src/ai4se_agent/context/sections/system_role.py`
- Create: `src/ai4se_agent/context/sections/tool_section.py`
- Create: `src/ai4se_agent/context/sections/format_section.py`
- Create: `src/ai4se_agent/context/sections/example_section.py`
- Create: `src/ai4se_agent/context/sections/workspace_section.py`
- Create: `src/ai4se_agent/context/sections/rules_section.py`
- Create: `src/ai4se_agent/context/prompt_composer.py`
- Modify: `tests/context/test_prompt_section.py` (append tests)

**Interfaces:**
- Consumes: `PromptContext`, `PromptSection` from Task 1
- Produces: 6 concrete sections, `PromptComposer`

- [ ] **Step 1: Write the failing tests (append to test_prompt_section.py)**

```python
# Append to tests/context/test_prompt_section.py

from ai4se_agent.context.prompt_composer import PromptComposer
from ai4se_agent.context.sections.system_role import SystemRoleSection
from ai4se_agent.context.sections.tool_section import ToolSection
from ai4se_agent.context.sections.format_section import FormatSection
from ai4se_agent.context.sections.example_section import ExampleSection
from ai4se_agent.context.sections.workspace_section import WorkspaceSection
from ai4se_agent.context.sections.rules_section import RulesSection
from ai4se_agent.context.workspace import WorkspaceSnapshot


def test_system_role_section():
    section = SystemRoleSection()
    result = section.build(PromptContext(tools=[], goal=""))
    assert "coding agent" in result.lower()


def test_tool_section_lists_all_tools():
    section = ToolSection()
    ctx = PromptContext(tools=[
        {"name": "read_file", "description": "Read a file",
         "parameters": {"type": "object", "properties": {}, "required": []}}
    ], goal="")
    result = section.build(ctx)
    assert "read_file" in result


def test_format_section_includes_json_escaping():
    section = FormatSection()
    result = section.build(PromptContext(tools=[], goal=""))
    assert '{"action"' in result
    assert '\\"' in result  # escaping instruction


def test_example_section_has_finish():
    section = ExampleSection()
    result = section.build(PromptContext(tools=[], goal=""))
    assert "finish" in result


def test_workspace_section_shows_os():
    section = WorkspaceSection()
    ws = WorkspaceSnapshot(
        os="linux", cwd="/home/user/project",
        git_branch="main", files=["README.md", "src/main.py"],
        timestamp="2026-07-23T12:00:00"
    )
    ctx = PromptContext(tools=[], goal="", workspace=ws)
    result = section.build(ctx)
    assert "linux" in result
    assert "/home/user/project" in result
    assert "main" in result
    assert "README.md" in result


def test_workspace_section_none_workspace():
    section = WorkspaceSection()
    ctx = PromptContext(tools=[], goal="", workspace=None)
    result = section.build(ctx)
    assert result == ""


def test_rules_section_with_rules():
    section = RulesSection()
    ctx = PromptContext(tools=[], goal="", rules=["no rm -rf", "use pathlib"])
    result = section.build(ctx)
    assert "no rm -rf" in result
    assert "use pathlib" in result


def test_rules_section_empty():
    section = RulesSection()
    ctx = PromptContext(tools=[], goal="", rules=[])
    result = section.build(ctx)
    assert result == ""


def test_prompt_composer_joins_sections():
    composer = PromptComposer([
        SystemRoleSection(), ToolSection(), FormatSection()
    ])
    ctx = PromptContext(tools=[
        {"name": "shell", "description": "Run command",
         "parameters": {"type": "object", "properties": {}, "required": []}}
    ], goal="")
    result = composer.compose(ctx)
    assert len(result) > 0
    assert "shell" in result
    assert "coding agent" in result.lower()


def test_prompt_composer_skips_empty_sections():
    composer = PromptComposer([
        SystemRoleSection(), RulesSection()  # RulesSection returns "" when empty
    ])
    ctx = PromptContext(tools=[], goal="")
    result = composer.compose(ctx)
    assert "coding agent" in result.lower()
    # No blank "## Rules\n(none)" text
    assert "Rules" not in result


def test_composed_prompt_no_workflow_text():
    """B.2: No workflow text in composed prompt."""
    composer = PromptComposer([
        SystemRoleSection(), ToolSection(), FormatSection(),
        ExampleSection(), RulesSection()
    ])
    ctx = PromptContext(tools=[], goal="")
    result = composer.compose(ctx)
    assert "Workflow" not in result
    assert "To complete a task, use tools to" not in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/context/test_prompt_section.py::test_system_role_section -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Create src/ai4se_agent/context/sections/__init__.py**

```python
from ai4se_agent.context.sections.system_role import SystemRoleSection
from ai4se_agent.context.sections.tool_section import ToolSection
from ai4se_agent.context.sections.format_section import FormatSection
from ai4se_agent.context.sections.example_section import ExampleSection
from ai4se_agent.context.sections.workspace_section import WorkspaceSection
from ai4se_agent.context.sections.rules_section import RulesSection

__all__ = [
    "SystemRoleSection", "ToolSection", "FormatSection",
    "ExampleSection", "WorkspaceSection", "RulesSection",
]
```

- [ ] **Step 4: Create src/ai4se_agent/context/sections/system_role.py**

```python
from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.prompt_context import PromptContext


class SystemRoleSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        return "You are a coding agent. You can use tools to read, write, edit files, run shell commands, and execute tests."
```

- [ ] **Step 5: Create src/ai4se_agent/context/sections/tool_section.py**

```python
from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.prompt_context import PromptContext


class ToolSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        lines = ["## Tools"]
        for s in ctx.tools:
            name = s["name"]
            desc = s.get("description", "")
            params = s["parameters"]["properties"]
            required = set(s["parameters"].get("required", []))
            param_strs = []
            for pname, pinfo in params.items():
                ptype = pinfo.get("type", "string")
                req = " (required)" if pname in required else ""
                param_strs.append(f"    {pname}: {ptype}{req}")
            param_block = "\n".join(param_strs) if param_strs else "    (none)"
            lines.append(f"  {name}: {desc}\n{param_block}")
        return "\n".join(lines)
```

- [ ] **Step 6: Create src/ai4se_agent/context/sections/format_section.py**

```python
from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.prompt_context import PromptContext


class FormatSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        return (
            "## Response Format\n\n"
            "Respond with exactly one JSON object per turn:\n\n"
            '  {"action": "<tool_name>", "parameters": {"key": "value"}}\n\n'
            "Important rules:\n"
            "- Each response must contain exactly one JSON action.\n"
            "- For multi-line content, use \\n for newlines inside JSON strings.\n"
            "- All double quotes inside string values MUST be escaped with backslash: \\\"\n"
            "- Example of properly escaped code string:\n"
            '  {"action": "write_file", "parameters": {"path": "x.cpp", "content": "#include <iostream>\\nint main() { std::cout << \\"hi\\"; }\\n"}}\n\n'
            "- To finish the task, use the finish action:\n"
            '  {"action": "finish", "parameters": {"summary": "Task completed"}}'
        )
```

- [ ] **Step 7: Create src/ai4se_agent/context/sections/example_section.py**

```python
from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.prompt_context import PromptContext


class ExampleSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        return (
            "## Example Session\n\n"
            '{"action": "write_file", "parameters": {"path": "main.cpp", "content": "#include <iostream>\\nint main() { std::cout << \\"hello\\"; }\\n"}}\n'
            '{"action": "shell", "parameters": {"command": "g++ -o main main.cpp"}}\n'
            '{"action": "shell", "parameters": {"command": "./main"}}\n'
            '{"action": "finish", "parameters": {"summary": "Compiled and ran successfully"}}'
        )
```

- [ ] **Step 8: Create src/ai4se_agent/context/sections/workspace_section.py**

```python
from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.prompt_context import PromptContext


class WorkspaceSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        ws = ctx.workspace
        if ws is None:
            return ""
        lines = [
            "## Environment",
            f"  OS: {ws.os}",
            f"  Working directory: {ws.cwd}",
            f"  Git branch: {ws.git_branch}",
            f"  Time: {ws.timestamp}",
        ]
        if ws.files:
            lines.append("  Visible files:")
            for f in ws.files:
                lines.append(f"    - {f}")
        return "\n".join(lines)
```

- [ ] **Step 9: Create src/ai4se_agent/context/sections/rules_section.py**

```python
from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.prompt_context import PromptContext


class RulesSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        if not ctx.rules:
            return ""
        lines = ["## Project Rules"]
        for r in ctx.rules:
            lines.append(f"  - {r}")
        return "\n".join(lines)
```

- [ ] **Step 10: Create src/ai4se_agent/context/prompt_composer.py**

```python
from ai4se_agent.context.prompt_context import PromptContext
from ai4se_agent.context.prompt_section import PromptSection


class PromptComposer:
    def __init__(self, sections: list[PromptSection]):
        self._sections = sections

    def compose(self, ctx: PromptContext) -> str:
        parts = []
        for section in self._sections:
            text = section.build(ctx)
            if text:
                parts.append(text)
        return "\n\n".join(parts)
```

- [ ] **Step 11: Run section tests**

Run: `pytest tests/context/test_prompt_section.py -v`
Expected: ALL 15 tests PASS

- [ ] **Step 12: Commit**

```bash
git add src/ai4se_agent/context/sections/ src/ai4se_agent/context/prompt_composer.py tests/context/test_prompt_section.py
git commit -m "feat: add 6 PromptSection implementations and PromptComposer"
```

---

### Task 3: WorkspaceCollector + WorkspaceSnapshot

**Files:**
- Create: `src/ai4se_agent/context/workspace.py`
- Create: `tests/context/test_workspace.py`

**Interfaces:**
- Consumes: Nothing
- Produces: `WorkspaceSnapshot` dataclass, `WorkspaceCollector` with cache

- [ ] **Step 1: Write the failing tests**

```python
# tests/context/test_workspace.py
import time
from ai4se_agent.context.workspace import WorkspaceCollector, WorkspaceSnapshot


def test_snapshot_is_immutable():
    ws = WorkspaceSnapshot(
        os="win32", cwd="/tmp", git_branch="main",
        files=["a.py"], timestamp="2026-07-23T00:00:00"
    )
    try:
        ws.os = "linux"
    except Exception:
        pass
    assert ws.os == "win32"


def test_collector_returns_snapshot(tmp_path):
    (tmp_path / "README.md").write_text("# Project")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hi')")
    (tmp_path / ".git").mkdir()

    collector = WorkspaceCollector(str(tmp_path), max_files=50)
    snapshot = collector.collect()
    assert isinstance(snapshot, WorkspaceSnapshot)
    assert len(snapshot.os) > 0
    assert snapshot.cwd == str(tmp_path.resolve())
    files = snapshot.files
    assert "README.md" in files or any("README.md" in f for f in files)
    assert ".git" not in str(files)


def test_collector_skips_hidden_and_cache(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "main.py").write_text("x")
    collector = WorkspaceCollector(str(tmp_path), max_files=50)
    snapshot = collector.collect()
    assert "main.py" in str(snapshot.files)
    assert ".git" not in str(snapshot.files)
    assert "__pycache__" not in str(snapshot.files)


def test_collector_file_limit(tmp_path):
    for i in range(10):
        (tmp_path / f"file_{i:02d}.py").write_text("x")
    collector = WorkspaceCollector(str(tmp_path), max_files=5)
    snapshot = collector.collect()
    assert len(snapshot.files) <= 7  # 5 files + truncation message + maybe parent dir entries
    assert any("more" in f.lower() for f in snapshot.files[-1:])


def test_collector_cache(tmp_path):
    collector = WorkspaceCollector(str(tmp_path), max_files=50)
    s1 = collector.collect()
    s2 = collector.collect()
    assert s1 is s2  # Same object from cache


def test_collector_cache_expiry(tmp_path):
    collector = WorkspaceCollector(str(tmp_path), max_files=50)
    collector._cache_ttl = 0.01  # 10ms TTL for testing
    s1 = collector.collect()
    time.sleep(0.02)
    s2 = collector.collect()
    assert s1 is not s2  # New object after cache expiry


def test_collector_invalidate(tmp_path):
    collector = WorkspaceCollector(str(tmp_path), max_files=50)
    s1 = collector.collect()
    collector.invalidate()
    s2 = collector.collect()
    assert s1 is not s2


def test_collector_force_refresh(tmp_path):
    collector = WorkspaceCollector(str(tmp_path), max_files=50)
    collector.collect()
    s2 = collector.collect(force=True)
    assert s2 is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/context/test_workspace.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Create src/ai4se_agent/context/workspace.py**

```python
import datetime
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache",
             "node_modules", ".venv", "venv", ".mypy_cache", ".idea"}
SKIP_PATTERNS = ("*.pyc", "*.pyo", ".DS_Store")


@dataclass(frozen=True)
class WorkspaceSnapshot:
    os: str
    cwd: str
    git_branch: str
    files: list[str]
    timestamp: str


class WorkspaceCollector:
    def __init__(self, workspace_root: str, max_files: int = 50):
        self._root = Path(workspace_root).resolve()
        self._max_files = max_files
        self._cache: WorkspaceSnapshot | None = None
        self._cache_ttl: float = 5.0
        self._last_collect: float = 0.0

    def collect(self, force: bool = False) -> WorkspaceSnapshot:
        now = time.time()
        if not force and self._cache is not None and (now - self._last_collect) < self._cache_ttl:
            return self._cache
        snapshot = WorkspaceSnapshot(
            os=sys.platform,
            cwd=str(self._root),
            git_branch=self._get_git_branch(),
            files=self._summarize_files(),
            timestamp=datetime.datetime.now().isoformat(),
        )
        self._cache = snapshot
        self._last_collect = now
        return snapshot

    def invalidate(self) -> None:
        self._cache = None
        self._last_collect = 0.0

    def _get_git_branch(self) -> str:
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, timeout=5, cwd=str(self._root)
            )
            branch = result.stdout.strip()
            return branch if branch else "unknown"
        except Exception:
            return "unknown"

    def _summarize_files(self) -> list[str]:
        entries: list[str] = []
        try:
            for item in sorted(self._root.iterdir()):
                name = item.name
                if name in SKIP_DIRS:
                    continue
                if any(item.match(p) for p in SKIP_PATTERNS):
                    continue
                if item.is_dir():
                    entries.append(f"{name}/")
                else:
                    entries.append(name)
                if len(entries) >= self._max_files:
                    remaining = sum(1 for _ in self._root.iterdir()) - len(entries)
                    if remaining > 0:
                        entries.append(f"... and {remaining} more files")
                    break
        except PermissionError:
            pass
        return entries
```

- [ ] **Step 4: Run workspace tests**

Run: `pytest tests/context/test_workspace.py -v`
Expected: ALL 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/context/workspace.py tests/context/test_workspace.py
git commit -m "feat: add WorkspaceCollector with WorkspaceSnapshot and TTL cache"
```

---

### Task 4: ContextBuilder Integration + Session Wiring

**Files:**
- Modify: `src/ai4se_agent/context/prompt.py` (remove `build_system_prompt`, keep `build_tool_descriptions`)
- Modify: `src/ai4se_agent/context/builder.py` (use `PromptComposer`)
- Modify: `src/ai4se_agent/memory/manager.py` (add `get_rules()`)
- Modify: `src/ai4se_agent/cli/session.py` (create `WorkspaceCollector`, pass to `ContextBuilder`)
- Modify: `tests/context/test_builder.py` (update tests)

**Interfaces:**
- Consumes: All from Tasks 1, 2, 3
- Produces: Wired `ContextBuilder` with dynamic sections

- [ ] **Step 1: Update tests/context/test_builder.py**

Read the current file first, then rewrite:

```python
from ai4se_agent.context.builder import ContextBuilder
from ai4se_agent.context.workspace import WorkspaceCollector
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.tools.read_file import ReadFileTool
from ai4se_agent.tools.write_file import WriteFileTool
from ai4se_agent.tools.shell import ShellTool
from ai4se_agent.types import Action


def test_build_initial_context(tmp_path):
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    builder = ContextBuilder(tool_registry=registry, workspace_root=str(tmp_path))
    state = AgentState(goal="test task")
    messages = builder.build(state)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "test task"


def test_system_prompt_includes_tools():
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(ShellTool())
    builder = ContextBuilder(tool_registry=registry, workspace_root=".")
    state = AgentState(goal="test")
    messages = builder.build(state)
    prompt = messages[0]["content"]
    assert "read_file" in prompt
    assert "shell" in prompt
    assert "finish" in prompt


def test_system_prompt_includes_workspace(tmp_path):
    (tmp_path / "main.py").write_text("x")
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    builder = ContextBuilder(tool_registry=registry, workspace_root=str(tmp_path))
    state = AgentState(goal="test")
    messages = builder.build(state)
    prompt = messages[0]["content"]
    assert "Environment" in prompt or "main.py" in prompt


def test_system_prompt_no_workflow_text():
    """B.2: composed prompt must not contain workflow instructions."""
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    builder = ContextBuilder(tool_registry=registry, workspace_root=".")
    state = AgentState(goal="test")
    messages = builder.build(state)
    prompt = messages[0]["content"]
    assert "Workflow" not in prompt


def test_system_prompt_includes_json_format():
    registry = ToolRegistry()
    builder = ContextBuilder(tool_registry=registry, workspace_root=".")
    state = AgentState(goal="test")
    messages = builder.build(state)
    prompt = messages[0]["content"]
    assert "json" in prompt.lower() or '{"action"' in prompt


def test_build_with_history(tmp_path):
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    builder = ContextBuilder(tool_registry=registry, workspace_root=str(tmp_path))
    state = AgentState(goal="test")
    action = Action(name="shell", parameters={"command": "dir"})
    state.record_turn(action, "file1.txt\nfile2.txt")
    messages = builder.build(state)
    assert len(messages) == 4
    assert messages[2]["role"] == "assistant"
    assert messages[3]["role"] == "tool"


def test_build_with_feedback(tmp_path):
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    builder = ContextBuilder(tool_registry=registry, workspace_root=str(tmp_path))
    state = AgentState(goal="fix bug")
    state.record_feedback("pytest failed")
    messages = builder.build(state)
    assert len(messages) == 3
    assert messages[2]["role"] == "user"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/context/test_builder.py -v`
Expected: FAIL — old tests reference removed signatures

- [ ] **Step 3: Update src/ai4se_agent/context/prompt.py**

Read the file first. Remove `build_system_prompt()` and `FINISH_SCHEMA` constant. Keep `build_tool_descriptions()`. The file becomes:

```python
def build_tool_descriptions(schemas: list[dict]) -> str:
    lines = []
    for s in schemas:
        name = s["name"]
        desc = s.get("description", "")
        params = s["parameters"]["properties"]
        required = set(s["parameters"].get("required", []))
        param_strs = []
        for pname, pinfo in params.items():
            ptype = pinfo.get("type", "string")
            req = " (required)" if pname in required else " (optional)"
            param_strs.append(f"      {pname}: {ptype}{req}")
        param_block = "\n".join(param_strs) if param_strs else "      (none)"
        lines.append(f"  - {name}: {desc}\n{param_block}")
    return "\n".join(lines)
```

- [ ] **Step 4: Update src/ai4se_agent/memory/manager.py**

Read the file first. Add `get_rules()` method:

```python
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

    def get_rules(self) -> list[str]:
        rule_names = self.persistent.list_rules()
        rules = []
        for name in rule_names:
            content = self.persistent.load_rule(name)
            if content:
                rules.append(content.strip())
        return rules
```

- [ ] **Step 5: Rewrite src/ai4se_agent/context/builder.py**

Read the file first, then replace entirely:

```python
from ai4se_agent.context.prompt_context import PromptContext
from ai4se_agent.context.prompt_composer import PromptComposer
from ai4se_agent.context.sections import (
    SystemRoleSection, ToolSection, FormatSection,
    ExampleSection, WorkspaceSection, RulesSection,
)
from ai4se_agent.context.workspace import WorkspaceCollector
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.tools.registry import ToolRegistry


class ContextBuilder:
    def __init__(self, tool_registry: ToolRegistry, workspace_root: str = "."):
        self._schemas = tool_registry.list_schemas()
        self._collector = WorkspaceCollector(workspace_root)
        self._composer = PromptComposer([
            SystemRoleSection(),
            ToolSection(),
            FormatSection(),
            ExampleSection(),
            WorkspaceSection(),
            RulesSection(),
        ])

    def build(self, state: AgentState) -> list[dict]:
        workspace = self._collector.collect()
        ctx = PromptContext(
            tools=self._schemas,
            goal=state.goal,
            workspace=workspace,
            rules=[],  # populated by harness if memory manager is available
            feedback=state.feedback,
        )
        system_prompt = self._composer.compose(ctx)

        messages: list[dict] = []
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": state.goal})
        messages.extend(state.history)
        messages.extend(state.feedback)
        return messages
```

- [ ] **Step 6: Update src/ai4se_agent/core/state_machine.py line 61**

Read the file first. Change:

```python
# Old
self._context_builder = ContextBuilder(tool_registry=self.tools)

# New — pass workspace_root from config or default to "."
self._context_builder = ContextBuilder(
    tool_registry=self.tools, workspace_root="."
)
```

- [ ] **Step 7: Update src/ai4se_agent/cli/session.py**

Read the file first. In `_build_harness()`, the `ContextBuilder` is no longer directly instantiated here (state_machine handles it). No change needed in session.py for ContextBuilder. But verify the `HarnessStateMachine` constructor still passes `tool_registry`.

- [ ] **Step 8: Run context tests**

Run: `pytest tests/context/test_builder.py tests/context/test_prompt_section.py tests/context/test_workspace.py -v`
Expected: ALL PASS

- [ ] **Step 9: Run full test suite**

Run: `python -m pytest -v`
Expected: ALL 90+ tests PASS

- [ ] **Step 10: Commit**

```bash
git add src/ai4se_agent/context/prompt.py src/ai4se_agent/context/builder.py src/ai4se_agent/memory/manager.py src/ai4se_agent/core/state_machine.py tests/context/test_builder.py
git commit -m "feat: wire PromptComposer into ContextBuilder with workspace context support"
```

---

### Task 5: Renderer ABC + TerminalRenderer Enhancement

**Files:**
- Modify: `src/ai4se_agent/cli/renderer.py`
- Modify: `tests/cli/test_renderer.py`

**Interfaces:**
- Consumes: Nothing from B track
- Produces: Enhanced `Renderer` ABC, improved `TerminalRenderer`

- [ ] **Step 1: Update tests/cli/test_renderer.py**

Read the current file first, then rewrite to add new tests:

```python
from ai4se_agent.cli.renderer import NullRenderer, Renderer, TerminalRenderer
from ai4se_agent.types import Action, GuardrailResult, StopReason, ToolResult


def test_null_renderer_does_nothing():
    r = NullRenderer()
    r.on_state_change("IDLE", "CONTEXT_ORG", 1)
    r.on_token_usage(1, 100, 50)
    r.on_timing("LLM_CALL", 123.4)
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


def test_terminal_renderer_token_usage(capsys):
    r = TerminalRenderer(verbose=True)
    r.on_token_usage(2, 500, 200)
    captured = capsys.readouterr()
    assert "500" in captured.out
    assert "200" in captured.out


def test_terminal_renderer_timing_verbose(capsys):
    r = TerminalRenderer(verbose=True)
    r.on_timing("LLM_CALL", 850.5)
    captured = capsys.readouterr()
    assert "LLM_CALL" in captured.out
    assert "850" in captured.out


def test_terminal_renderer_timing_non_verbose(capsys):
    r = TerminalRenderer(verbose=False)
    r.on_timing("LLM_CALL", 850.5)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_terminal_renderer_on_stop_with_summary(capsys):
    r = TerminalRenderer()
    r._total_tokens = 700
    r._total_elapsed_ms = 5000.0
    r.on_stop(StopReason.SUCCESS, 3)
    captured = capsys.readouterr()
    assert "success" in captured.out
    assert "700" in captured.out


def test_terminal_renderer_on_llm_call_verbose(capsys):
    r = TerminalRenderer(verbose=True)
    r.on_llm_call(1, "test-model", '{"action": "shell", "parameters": {"command": "echo hello"}}')
    captured = capsys.readouterr()
    assert "test-model" in captured.out
    assert "echo hello" in captured.out


def test_terminal_renderer_truncates_long_output(capsys):
    r = TerminalRenderer(max_output=20)
    result = ToolResult(success=False, output="a" * 100, error="err")
    r.on_tool_exec(1, "shell", result)
    captured = capsys.readouterr()
    assert len(captured.out.splitlines()[-1]) <= 40
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/cli/test_renderer.py -v`
Expected: FAIL — `on_token_usage` and `on_timing` not defined

- [ ] **Step 3: Update src/ai4se_agent/cli/renderer.py**

Read the file first, then apply these edits:

**Edit 1**: Add `on_token_usage` and `on_timing` to `Renderer` ABC (after line 31, before `NullRenderer`):

```python
    @abstractmethod
    def on_token_usage(self, iteration: int, prompt_tokens: int, completion_tokens: int) -> None:
        pass

    @abstractmethod
    def on_timing(self, state_name: str, elapsed_ms: float) -> None:
        pass
```

**Edit 2**: Add empty implementations to `NullRenderer` (after `on_stop`):

```python
    def on_token_usage(self, iteration: int, prompt_tokens: int, completion_tokens: int) -> None:
        pass

    def on_timing(self, state_name: str, elapsed_ms: float) -> None:
        pass
```

**Edit 3**: Replace `TerminalRenderer.__init__`:

```python
class TerminalRenderer(Renderer):
    def __init__(self, verbose: bool = False, max_output: int = 500):
        self._verbose = verbose
        self._max_output = max_output
        self._total_tokens: int = 0
        self._total_elapsed_ms: float = 0.0
```

**Edit 4**: Replace `on_llm_call`:

```python
    def on_llm_call(self, iteration: int, model: str, response: str) -> None:
        if self._verbose:
            self._print(f"  model: {model}")
            limit = 500 if self._verbose else 200
            self._print(f"  response: {response[:limit]}")
```

**Edit 5**: Replace `on_tool_exec` output truncation:

```python
    def on_tool_exec(self, iteration: int, tool: str, result: ToolResult) -> None:
        status = "OK" if result.success else "FAILED"
        self._print(f"  result: {status}")
        if self._verbose or not result.success:
            self._print(f"  output: {result.output[:self._max_output]}")
```

**Edit 6**: Replace `on_stop`:

```python
    def on_stop(self, reason: StopReason, iteration: int) -> None:
        self._print(
            f"STOP: {reason.value} | {iteration} iters | "
            f"{self._total_tokens} tokens | {self._total_elapsed_ms / 1000:.1f}s"
        )
```

**Edit 7**: Add new methods to `TerminalRenderer` (after `on_stop`):

```python
    def on_token_usage(self, iteration: int, prompt_tokens: int, completion_tokens: int) -> None:
        self._total_tokens += prompt_tokens + completion_tokens
        self._print(f"  token: {prompt_tokens}↑/{completion_tokens}↓")

    def on_timing(self, state_name: str, elapsed_ms: float) -> None:
        self._total_elapsed_ms += elapsed_ms
        if self._verbose:
            self._print(f"  [{state_name}] {elapsed_ms:.1f}ms")
```

- [ ] **Step 4: Run renderer tests**

Run: `pytest tests/cli/test_renderer.py -v`
Expected: ALL 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/cli/renderer.py tests/cli/test_renderer.py
git commit -m "feat: add on_token_usage/on_timing to Renderer, improve TerminalRenderer output control"
```

---

### Task 6: Trace Enhancement

**Files:**
- Modify: `src/ai4se_agent/observability/events.py`
- Modify: `src/ai4se_agent/observability/tracer.py`
- Modify: `tests/observability/test_events.py`
- Modify: `tests/observability/test_tracer.py`

**Interfaces:**
- Consumes: Nothing from B track
- Produces: Enhanced `Event` with timestamp/elapsed_ms, `Tracer` with record_token/replay_filtered

- [ ] **Step 1: Update tests**

**Update tests/observability/test_events.py:**

```python
# tests/observability/test_events.py
from ai4se_agent.observability.events import EventType, StateEvent, LLMEvent

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

def test_event_to_dict_includes_timestamp():
    event = StateEvent(iteration=1, old_state="IDLE", new_state="CONTEXT_ORG")
    event.timestamp = "2026-07-23T12:00:00"
    event.elapsed_ms = 150.0
    d = event.to_dict()
    assert d["timestamp"] == "2026-07-23T12:00:00"
    assert d["elapsed_ms"] == 150.0

def test_event_default_timestamp_empty():
    event = StateEvent(iteration=1, old_state="IDLE", new_state="CONTEXT_ORG")
    d = event.to_dict()
    assert d["timestamp"] == ""
    assert d["elapsed_ms"] == 0.0
```

**Update tests/observability/test_tracer.py:**

```python
# tests/observability/test_tracer.py
import json
from ai4se_agent.observability.tracer import Tracer, NullTracer
from ai4se_agent.observability.events import StateEvent, ToolEvent

def test_tracer_records_and_saves(tmp_path):
    tracer = Tracer()
    tracer.record(StateEvent(iteration=1, old_state="IDLE", new_state="CONTEXT_ORG"))
    tracer.record(ToolEvent(iteration=1, tool="shell", success=True))
    path = tmp_path / "trace.json"
    tracer.save(str(path))
    data = json.loads(path.read_text())
    assert len(data) == 2
    assert data[0]["type"] == "state_changed"
    assert "timestamp" in data[0]
    assert "elapsed_ms" in data[0]

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

def test_tracer_record_token():
    tracer = Tracer()
    tracer.record_token(100, 50)
    assert tracer.total_tokens == 150

def test_tracer_replay_filtered_by_type(tmp_path):
    tracer = Tracer()
    tracer.record(StateEvent(iteration=1, old_state="IDLE", new_state="CONTEXT_ORG"))
    tracer.record(ToolEvent(iteration=1, tool="shell", success=True))
    path = tmp_path / "trace.json"
    tracer.save(str(path))
    state_events = tracer.replay_filtered(str(path), event_type="state_changed")
    assert len(state_events) == 1
    assert state_events[0]["type"] == "state_changed"

def test_tracer_replay_filtered_by_iteration(tmp_path):
    tracer = Tracer()
    tracer.record(StateEvent(iteration=1, old_state="IDLE", new_state="CONTEXT_ORG"))
    tracer.record(StateEvent(iteration=5, old_state="CONTEXT_ORG", new_state="LLM_CALL"))
    tracer.record(StateEvent(iteration=10, old_state="LLM_CALL", new_state="STOP"))
    path = tmp_path / "trace.json"
    tracer.save(str(path))
    filtered = tracer.replay_filtered(str(path), min_iteration=5)
    assert len(filtered) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/observability/test_events.py tests/observability/test_tracer.py -v`
Expected: FAIL — `timestamp`/`elapsed_ms` not in to_dict, `record_token`/`replay_filtered` not defined

- [ ] **Step 3: Update src/ai4se_agent/observability/events.py**

Read the file first. Change the `Event` base class only (line 16-22):

```python
@dataclass
class Event:
    type: EventType
    iteration: int
    timestamp: str = ""
    elapsed_ms: float = 0.0
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

Other event subclasses (StateEvent, LLMEvent, ActionEvent, ToolEvent, FeedbackEvent, GuardrailEvent) remain unchanged — their `data` dict already carries type-specific fields.

- [ ] **Step 4: Update src/ai4se_agent/observability/tracer.py**

Read the file first, then replace entirely:

```python
# src/ai4se_agent/observability/tracer.py
import json
import time
from pathlib import Path
from ai4se_agent.observability.events import Event


class Tracer:
    def __init__(self):
        self._events: list[Event] = []
        self._start_time: float = time.time()
        self.total_tokens: int = 0

    def record(self, event: Event) -> None:
        import datetime
        event.timestamp = datetime.datetime.now().isoformat()
        event.elapsed_ms = (time.time() - self._start_time) * 1000
        self._events.append(event)

    def record_token(self, prompt: int, completion: int) -> None:
        self.total_tokens += prompt + completion

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

    @staticmethod
    def replay_filtered(path: str, *, event_type: str | None = None,
                        min_iteration: int = 0) -> list[dict]:
        events = Tracer.replay(path)
        result = []
        for e in events:
            if event_type is not None and e.get("type") != event_type:
                continue
            if e.get("iteration", 0) < min_iteration:
                continue
            result.append(e)
        return result


class NullTracer(Tracer):
    def record(self, event: Event) -> None:
        pass

    def save(self, path: str) -> None:
        pass
```

- [ ] **Step 5: Run trace tests**

Run: `pytest tests/observability/test_events.py tests/observability/test_tracer.py -v`
Expected: ALL 10 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/ai4se_agent/observability/events.py src/ai4se_agent/observability/tracer.py tests/observability/test_events.py tests/observability/test_tracer.py
git commit -m "feat: add timestamp/elapsed_ms to Event, record_token and replay_filtered to Tracer"
```

---

### Task 7: Full Test Pass + Integration Verification

**Files:**
- (verification only, no code changes unless tests fail)

**Interfaces:**
- Consumes: All Tasks 1-6
- Produces: Verified integration

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest -v`
Expected: ALL tests PASS (90+ original + ~30 new)

- [ ] **Step 2: End-to-end smoke test with mock LLM**

Run: `LLM_PROVIDER=mock python -m ai4se_agent.cli.main "test task" 2>&1`
Expected: Runs to completion, output shows sections being used

- [ ] **Step 3: Verify trace output**

Run:
```python
import json
from ai4se_agent.observability.tracer import Tracer
events = Tracer.replay("sessions/session_latest.json")  # if exists
```

Expected: Each event has `timestamp` and `elapsed_ms` fields.

- [ ] **Step 4: Commit any fixups (if needed)**

```bash
git add -A
git commit -m "chore: integration fixups after full test pass"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - B.1 Prompt Section Architecture → Task 1 (ABC + Context), Task 2 (6 sections + Composer)
   - B.2 Workflow Optimization → Task 2 Step 11 test `test_composed_prompt_no_workflow_text`, Task 4 Step 1 test `test_system_prompt_no_workflow_text`
   - B.3 Workspace Context → Task 3 (Collector + Snapshot), Task 4 (integration)
   - C.1 Renderer Enhancement → Task 5
   - C.2 Trace Enhancement → Task 6
   - Integration verification → Task 7

2. **Placeholder scan:** No TBD/TODO/fill-in-later. Every step has complete code.

3. **Type consistency:**
   - `PromptContext.tools: list[dict]` — consistent across all sections
   - `PromptSection.build(ctx: PromptContext) -> str` — consistent ABC
   - `WorkspaceSnapshot` is frozen dataclass — consistent usage
   - `Renderer.on_token_usage(iteration, prompt_tokens, completion_tokens)` — consistent signature
   - `Event.timestamp: str`, `Event.elapsed_ms: float` — consistent field types
   - `Tracer.total_tokens: int` — matches `record_token` accumulator
