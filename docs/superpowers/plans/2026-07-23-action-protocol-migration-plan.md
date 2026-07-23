# Action Protocol Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate from text-based action protocol (`action: write_file key=value`) to JSON-based protocol (`{"action": "write_file", "parameters": {...}}`) with Tool self-describing schemas and `finish` action replacing `[DONE]` sentinel.

**Architecture:** Each Tool exposes a `schema` property (OpenAI function-calling compatible dict format). `ActionParser` uses dual strategy: JSON first with legacy text fallback. `ActionValidator` is schema-driven from ToolRegistry. `[DONE]` replaced by `finish` action that goes through validation. `Action.params` renamed to `Action.parameters` throughout.

**Tech Stack:** Python 3.10+, json (stdlib), re (stdlib)

## Global Constraints

- Python >=3.10
- All existing 69 tests must remain green (old parser fallback ensures backward compatibility)
- `Action.params` → `Action.parameters` rename across all files
- `ActionValidator` driven by Tool schemas, not hardcoded dict
- `ParseResult` replaces `None` return from parser
- `finish` action goes through validator but not guardrail engine
- `[DONE]` sentinel eliminated from prompt and state machine
- File paths relative to workspace root (`projects/`)
- Tests in `tests/` mirroring `src/` structure

---

### Task 1: Types + Tool Schema Foundation

**Files:**
- Modify: `src/ai4se_agent/types.py`
- Modify: `src/ai4se_agent/tools/base.py`
- Modify: `src/ai4se_agent/tools/registry.py`
- Create: `tests/tools/test_schema.py`

**Interfaces:**
- Consumes: Nothing from this project
- Produces: `ParseResult` dataclass, `Tool.schema` property, `ToolRegistry.list_schemas()`

- [ ] **Step 1: Write the failing tests**

```python
# tests/tools/test_schema.py
from ai4se_agent.tools.base import Tool
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.types import ParseResult


class _DummyTool(Tool):
    name = "dummy"

    @property
    def schema(self) -> dict:
        return {
            "name": "dummy",
            "description": "A dummy tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "msg": {"type": "string", "description": "A message"}
                },
                "required": ["msg"]
            }
        }

    def execute(self, params: dict):
        from ai4se_agent.types import ToolResult
        return ToolResult(success=True, output=params.get("msg", ""))


def test_tool_schema_is_dict():
    tool = _DummyTool()
    s = tool.schema
    assert isinstance(s, dict)
    assert s["name"] == "dummy"
    assert "parameters" in s


def test_registry_list_schemas():
    registry = ToolRegistry()
    registry.register(_DummyTool())
    schemas = registry.list_schemas()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "dummy"


def test_parse_result_creation():
    from ai4se_agent.types import Action
    r = ParseResult(success=True, action=Action(name="test", parameters={}))
    assert r.success is True
    assert r.action is not None
    assert r.error is None


def test_parse_result_failure():
    r = ParseResult(success=False, error="bad json")
    assert r.success is False
    assert r.action is None
    assert r.error == "bad json"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/tools/test_schema.py -v`
Expected: FAIL with ModuleNotFoundError or ImportError

- [ ] **Step 3: Add `ParseResult` to types.py**

```python
# src/ai4se_agent/types.py — add after existing dataclasses

@dataclass
class ParseResult:
    success: bool
    action: Optional["Action"] = None
    error: Optional[str] = None
```

- [ ] **Step 4: Rename `Action.params` → `Action.parameters` in types.py**

```python
# src/ai4se_agent/types.py — change Action dataclass
@dataclass
class Action:
    name: str
    parameters: dict = field(default_factory=dict)
```

- [ ] **Step 5: Add `schema` property to Tool ABC**

```python
# src/ai4se_agent/tools/base.py
from abc import ABC, abstractmethod
from ai4se_agent.types import ToolResult


class Tool(ABC):
    name: str

    @property
    @abstractmethod
    def schema(self) -> dict:
        pass

    @abstractmethod
    def execute(self, params: dict) -> ToolResult:
        pass
```

- [ ] **Step 6: Add `list_schemas()` to ToolRegistry**

```python
# src/ai4se_agent/tools/registry.py
from ai4se_agent.tools.base import Tool
from ai4se_agent.types import Action, ToolResult


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def execute(self, action: Action) -> ToolResult:
        tool = self._tools.get(action.name)
        if not tool:
            return ToolResult(success=False, output="", error=f"Unknown tool: {action.name}")
        try:
            return tool.execute(action.parameters)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    def list_schemas(self) -> list[dict]:
        return [tool.schema for tool in self._tools.values()]
```

- [ ] **Step 7: Run tests**

Run: `pytest tests/tools/test_schema.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/ai4se_agent/types.py src/ai4se_agent/tools/base.py src/ai4se_agent/tools/registry.py tests/tools/test_schema.py
git commit -m "feat: add ParseResult, Tool.schema, ToolRegistry.list_schemas; Action.params->parameters"
```

---

### Task 2: Tool Schema Implementations

**Files:**
- Modify: `src/ai4se_agent/tools/read_file.py`
- Modify: `src/ai4se_agent/tools/write_file.py`
- Modify: `src/ai4se_agent/tools/edit_file.py`
- Modify: `src/ai4se_agent/tools/shell.py`
- Modify: `src/ai4se_agent/tools/run_test.py`
- Test: `tests/tools/test_schema.py` (add to existing)

**Interfaces:**
- Consumes: `Tool.schema` ABC from Task 1
- Produces: 5 concrete `schema` implementations

- [ ] **Step 1: Write the failing tests (add to test_schema.py)**

```python
# tests/tools/test_schema.py — append these tests
from ai4se_agent.tools.read_file import ReadFileTool
from ai4se_agent.tools.write_file import WriteFileTool
from ai4se_agent.tools.edit_file import EditFileTool
from ai4se_agent.tools.shell import ShellTool
from ai4se_agent.tools.run_test import RunTestTool


def test_read_file_schema():
    tool = ReadFileTool()
    s = tool.schema
    assert s["name"] == "read_file"
    assert "path" in s["parameters"]["properties"]
    assert "path" in s["parameters"]["required"]


def test_write_file_schema():
    tool = WriteFileTool()
    s = tool.schema
    assert s["name"] == "write_file"
    assert "path" in s["parameters"]["properties"]
    assert "content" in s["parameters"]["properties"]
    assert "path" in s["parameters"]["required"]
    assert "content" in s["parameters"]["required"]


def test_edit_file_schema():
    tool = EditFileTool()
    s = tool.schema
    assert s["name"] == "edit_file"
    assert "path" in s["parameters"]["properties"]
    assert "old_string" in s["parameters"]["properties"]
    assert "new_string" in s["parameters"]["properties"]


def test_shell_schema():
    tool = ShellTool()
    s = tool.schema
    assert s["name"] == "shell"
    assert "command" in s["parameters"]["properties"]
    assert "timeout" in s["parameters"]["properties"]
    assert "command" in s["parameters"]["required"]


def test_run_test_schema():
    tool = RunTestTool()
    s = tool.schema
    assert s["name"] == "run_test"
    assert "test_path" in s["parameters"]["properties"]
    assert "args" in s["parameters"]["properties"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/tools/test_schema.py -v`
Expected: FAIL (schema property not implemented)

- [ ] **Step 3: Implement schema on each tool**

```python
# src/ai4se_agent/tools/read_file.py
from pathlib import Path
from ai4se_agent.tools.base import Tool
from ai4se_agent.types import ToolResult


class ReadFileTool(Tool):
    name = "read_file"

    @property
    def schema(self) -> dict:
        return {
            "name": "read_file",
            "description": "Read the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                },
                "required": ["path"]
            }
        }

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

    @property
    def schema(self) -> dict:
        return {
            "name": "write_file",
            "description": "Write content to a file (overwrites existing)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["path", "content"]
            }
        }

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

    @property
    def schema(self) -> dict:
        return {
            "name": "edit_file",
            "description": "Edit a file by replacing the first occurrence of old_string with new_string",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to edit"
                    },
                    "old_string": {
                        "type": "string",
                        "description": "Text to search for (first occurrence)"
                    },
                    "new_string": {
                        "type": "string",
                        "description": "Replacement text"
                    }
                },
                "required": ["path", "old_string", "new_string"]
            }
        }

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
from ai4se_agent.tools.base import Tool
from ai4se_agent.types import ToolResult


class ShellTool(Tool):
    name = "shell"

    @property
    def schema(self) -> dict:
        return {
            "name": "shell",
            "description": "Run a shell command and capture output",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default 30)"
                    },
                    "workdir": {
                        "type": "string",
                        "description": "Working directory for the command"
                    }
                },
                "required": ["command"]
            }
        }

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

    @property
    def schema(self) -> dict:
        return {
            "name": "run_test",
            "description": "Run pytest tests and capture results",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_path": {
                        "type": "string",
                        "description": "Path to test file or directory"
                    },
                    "args": {
                        "type": "string",
                        "description": "Additional pytest arguments"
                    }
                },
                "required": []
            }
        }

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

Run: `pytest tests/tools/test_schema.py -v`
Expected: PASS (all 10 tests)

- [ ] **Step 5: Commit**

```bash
git add src/ai4se_agent/tools/ tests/tools/test_schema.py
git commit -m "feat: implement Tool.schema for all 5 tools"
```

---

### Task 3: ActionParser + ActionValidator Rewrite

**Files:**
- Modify: `src/ai4se_agent/core/action.py`
- Modify: `src/ai4se_agent/core/state_machine.py` (action.params -> action.parameters)
- Modify: `src/ai4se_agent/core/agent_state.py` (action.params -> action.parameters)
- Modify: `src/ai4se_agent/cli/renderer.py` (action.params -> action.parameters)
- Modify: `src/ai4se_agent/guardrails/command_policy.py` (action.params -> action.parameters)
- Modify: `src/ai4se_agent/guardrails/file_policy.py` (action.params -> action.parameters)
- Modify: `src/ai4se_agent/guardrails/git_policy.py` (action.params -> action.parameters)
- Modify: `src/ai4se_agent/guardrails/workspace_policy.py` (action.params -> action.parameters)
- Modify: `src/ai4se_agent/observability/events.py` (action.params -> action.parameters)
- Create: `tests/core/test_action_json.py`

**Interfaces:**
- Consumes: `Action.parameters`, `ParseResult`, `Tool.schema` from Tasks 1-2
- Produces: `ActionParser.parse(text) -> ParseResult`, `ActionValidator.validate(action) -> list[str]` (schema-driven)

- [ ] **Step 1: Write the failing tests**

```python
# tests/core/test_action_json.py
import json
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.types import Action


SCHEMAS = [
    {
        "name": "write_file",
        "description": "Write content to a file",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "File content"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "shell",
        "description": "Run a shell command",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command"},
                "timeout": {"type": "integer", "description": "Timeout"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "finish",
        "description": "Signal task completion",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Summary"}
            },
            "required": []
        }
    }
]


def test_parse_json_action():
    parser = ActionParser()
    result = parser.parse('{"action": "write_file", "parameters": {"path": "a.cpp", "content": "int main() {}"}}')
    assert result.success is True
    assert result.action is not None
    assert result.action.name == "write_file"
    assert result.action.parameters["path"] == "a.cpp"
    assert result.action.parameters["content"] == "int main() {}"


def test_parse_json_with_code_block():
    parser = ActionParser()
    text = '```json\n{"action": "shell", "parameters": {"command": "g++ -o a a.cpp"}}\n```'
    result = parser.parse(text)
    assert result.success is True
    assert result.action.name == "shell"


def test_parse_json_with_plain_code_block():
    parser = ActionParser()
    text = '```\n{"action": "shell", "parameters": {"command": "g++ -o a a.cpp"}}\n```'
    result = parser.parse(text)
    assert result.success is True
    assert result.action.name == "shell"


def test_parse_invalid_json():
    parser = ActionParser()
    result = parser.parse("not json at all")
    assert result.success is False
    assert result.error is not None


def test_parse_missing_action_field():
    parser = ActionParser()
    result = parser.parse('{"name": "write_file", "params": {}}')
    assert result.success is False


def test_parse_finish_action():
    parser = ActionParser()
    result = parser.parse('{"action": "finish", "parameters": {"summary": "done"}}')
    assert result.success is True
    assert result.action.name == "finish"


def test_validate_known_action():
    validator = ActionValidator(SCHEMAS)
    action = Action(name="write_file", parameters={"path": "x.cpp", "content": "x"})
    errors = validator.validate(action)
    assert errors == []


def test_validate_missing_required():
    validator = ActionValidator(SCHEMAS)
    action = Action(name="write_file", parameters={"path": "x.cpp"})
    errors = validator.validate(action)
    assert len(errors) == 1
    assert "content" in errors[0]


def test_validate_unknown_action():
    validator = ActionValidator(SCHEMAS)
    action = Action(name="nonexistent", parameters={})
    errors = validator.validate(action)
    assert len(errors) == 1
    assert "unknown" in errors[0].lower() or "nonexistent" in errors[0]


def test_validate_type_check():
    validator = ActionValidator(SCHEMAS)
    action = Action(name="shell", parameters={"command": 42})
    errors = validator.validate(action)
    assert len(errors) == 1
    assert "string" in errors[0]


def test_validate_finish_action():
    validator = ActionValidator(SCHEMAS)
    action = Action(name="finish", parameters={"summary": "done"})
    errors = validator.validate(action)
    assert errors == []


def test_legacy_fallback():
    parser = ActionParser(fallback=True)
    result = parser.parse("action: write_file path=test.txt content=hello")
    assert result.success is True
    assert result.action.name == "write_file"
    assert result.action.parameters["path"] == "test.txt"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/core/test_action_json.py -v`
Expected: FAIL (import or function errors)

- [ ] **Step 3: Rewrite ActionParser and ActionValidator**

```python
# src/ai4se_agent/core/action.py
import json
import re
from ai4se_agent.types import Action, ParseResult


class LegacyActionParser:
    """Fallback parser for legacy text format: action: name key=value"""

    def parse(self, text: str) -> Action | None:
        match = re.match(r'action:\s*(\w+)(.*)', text.strip())
        if not match:
            return None
        name = match.group(1)
        rest = match.group(2).strip()
        params = {}
        pos = 0
        while pos < len(rest):
            while pos < len(rest) and rest[pos] in ' \t':
                pos += 1
            key_match = re.match(r'(\w+)=', rest[pos:])
            if not key_match:
                break
            key = key_match.group(1)
            pos += key_match.end()
            if pos < len(rest) and rest[pos] == '"':
                pos += 1
                value = []
                while pos < len(rest):
                    if rest[pos] == '\\' and pos + 1 < len(rest) and rest[pos + 1] == '"':
                        value.append('"')
                        pos += 2
                    elif rest[pos] == '\\' and pos + 1 < len(rest) and rest[pos + 1] == 'n':
                        value.append('\n')
                        pos += 2
                    elif rest[pos] == '\\' and pos + 1 < len(rest) and rest[pos + 1] == 't':
                        value.append('\t')
                        pos += 2
                    elif rest[pos] == '\\' and pos + 1 < len(rest) and rest[pos + 1] == 'r':
                        value.append('\r')
                        pos += 2
                    elif rest[pos] == '"':
                        pos += 1
                        break
                    else:
                        value.append(rest[pos])
                        pos += 1
                params[key] = ''.join(value)
            elif pos < len(rest) and rest[pos] == "'":
                pos += 1
                value = []
                while pos < len(rest):
                    if rest[pos] == '\\' and pos + 1 < len(rest) and rest[pos + 1] == "'":
                        value.append("'")
                        pos += 2
                    elif rest[pos] == "'":
                        pos += 1
                        break
                    else:
                        value.append(rest[pos])
                        pos += 1
                params[key] = ''.join(value)
            else:
                next_key = re.search(r'\s+\w+=', rest[pos:])
                if next_key:
                    end = pos + next_key.start()
                    value = rest[pos:end].strip()
                    pos = end
                else:
                    value = rest[pos:].strip()
                    pos = len(rest)
                value = value.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
                params[key] = value
        return Action(name=name, parameters=params)


class ActionParser:
    def __init__(self, fallback: bool = True):
        self._fallback = fallback
        self._legacy = LegacyActionParser()

    def _try_json(self, text: str) -> ParseResult:
        text = text.strip()
        code_block = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if code_block:
            text = code_block.group(1).strip()
        brace_start = text.find('{')
        brace_end = text.rfind('}')
        if brace_start == -1 or brace_end == -1 or brace_end <= brace_start:
            return ParseResult(success=False, error="No JSON object found")
        text = text[brace_start:brace_end + 1]
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as e:
            return ParseResult(success=False, error=f"Invalid JSON: {e}")
        if "action" not in obj:
            return ParseResult(success=False, error="Missing 'action' field in JSON")
        return ParseResult(
            success=True,
            action=Action(name=obj["action"], parameters=obj.get("parameters", {}))
        )

    def parse(self, text: str) -> ParseResult:
        result = self._try_json(text)
        if result.success:
            return result
        if self._fallback:
            action = self._legacy.parse(text)
            if action:
                return ParseResult(success=True, action=action)
        return result


class ActionValidator:
    def __init__(self, schemas: list[dict]):
        self._schemas = {s["name"]: s for s in schemas}

    def validate(self, action: Action) -> list[str]:
        errors = []
        schema = self._schemas.get(action.name)
        if not schema:
            errors.append(f"Unknown action: {action.name}")
            return errors
        required = schema["parameters"].get("required", [])
        for param in required:
            if param not in action.parameters:
                errors.append(f"Missing required parameter: {param}")
        for key, value in action.parameters.items():
            prop = schema["parameters"]["properties"].get(key)
            if prop and prop.get("type") == "string" and not isinstance(value, str):
                errors.append(f"Parameter '{key}' should be string, got {type(value).__name__}")
        return errors
```

- [ ] **Step 4: Update all `action.params` → `action.parameters` references**

```python
# src/ai4se_agent/core/agent_state.py — line 20
self.history.append({"role": "assistant", "content": f"action: {action.name} {action.parameters}"})

# src/ai4se_agent/core/state_machine.py — line 145
ActionEvent(self.state.iteration, action.name, action.parameters)

# src/ai4se_agent/cli/renderer.py — line 78
self._print(f"  action: {action.name}({action.parameters})")

# src/ai4se_agent/guardrails/command_policy.py — line 16
command = action.parameters.get("command", "")

# src/ai4se_agent/guardrails/file_policy.py — line 12
path = action.parameters.get("path", "")

# src/ai4se_agent/guardrails/git_policy.py — line 13
command = action.parameters.get("command", "")

# src/ai4se_agent/guardrails/workspace_policy.py — line 13
path = action.parameters.get("path", "")
```

- [ ] **Step 5: Update test files' `action.params` → `action.parameters`**

```python
# tests/core/test_types.py — line 7
assert action.parameters == {"path": "test.txt"}

# tests/core/test_action.py — line 9
assert action.parameters["path"] == "test.txt"

# tests/tools/test_read_file.py — lines 9, 16
result = tool.execute(action.parameters)
result = tool.execute(action.parameters)

# tests/tools/test_write_file.py — line 8
result = tool.execute(action.parameters)

# tests/tools/test_edit_file.py — lines 9, 18
result = tool.execute(action.parameters)
result = tool.execute(action.parameters)
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/core/test_action_json.py tests/core/test_action.py tests/core/test_types.py tests/tools/test_read_file.py tests/tools/test_write_file.py tests/tools/test_edit_file.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/ai4se_agent/core/action.py src/ai4se_agent/core/state_machine.py src/ai4se_agent/core/agent_state.py src/ai4se_agent/cli/renderer.py src/ai4se_agent/guardrails/ src/ai4se_agent/observability/events.py tests/core/test_action_json.py tests/core/test_action.py tests/core/test_types.py tests/tools/test_read_file.py tests/tools/test_write_file.py tests/tools/test_edit_file.py
git commit -m "feat: rewrite ActionParser with JSON+fallback, schema-driven ActionValidator, params->parameters"
```

---

### Task 4: ContextBuilder + Prompt Dynamic Generation

**Files:**
- Modify: `src/ai4se_agent/context/prompt.py`
- Modify: `src/ai4se_agent/context/builder.py`
- Modify: `src/ai4se_agent/core/state_machine.py` (pass ToolRegistry not list[Tool])
- Test: `tests/context/test_builder.py`

**Interfaces:**
- Consumes: `ToolRegistry.list_schemas()` from Task 1
- Produces: Dynamic system prompt from tool schemas, JSON action format examples

- [ ] **Step 1: Write the failing tests**

```python
# tests/context/test_builder.py — update existing tests
from ai4se_agent.context.builder import ContextBuilder
from ai4se_agent.context.prompt import build_system_prompt
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.tools.read_file import ReadFileTool
from ai4se_agent.tools.write_file import WriteFileTool


def test_system_prompt_includes_all_tools():
    prompt = build_system_prompt([ReadFileTool(), WriteFileTool()])
    assert "read_file" in prompt
    assert "write_file" in prompt
    assert "finish" in prompt  # finish is always included
    assert "json" in prompt.lower()  # mentions JSON format
    assert "[DONE]" not in prompt  # no longer uses [DONE]


def test_build_initial_context():
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    builder = ContextBuilder(registry)
    state = AgentState(goal="test task")
    messages = builder.build(state)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "test task"


def test_build_with_history():
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    builder = ContextBuilder(registry)
    state = AgentState(goal="test")
    state.history.append({"role": "assistant", "content": "response"})
    messages = builder.build(state)
    assert len(messages) == 3


def test_build_with_feedback():
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    builder = ContextBuilder(registry)
    state = AgentState(goal="test")
    state.record_feedback("fix the bug")
    messages = builder.build(state)
    assert len(messages) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/context/test_builder.py -v`
Expected: FAIL (old tests reference old signatures)

- [ ] **Step 3: Rewrite ContextBuilder to accept ToolRegistry**

```python
# src/ai4se_agent/context/builder.py
from ai4se_agent.context.prompt import build_system_prompt
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.tools.registry import ToolRegistry


class ContextBuilder:
    def __init__(self, tool_registry: ToolRegistry):
        self._schemas = tool_registry.list_schemas()

    def build(self, state: AgentState) -> list[dict]:
        messages: list[dict] = []
        messages.append({"role": "system", "content": build_system_prompt(self._schemas)})
        messages.append({"role": "user", "content": state.goal})
        messages.extend(state.history)
        messages.extend(state.feedback)
        return messages
```

- [ ] **Step 4: Rewrite prompt.py with dynamic schema generation**

```python
# src/ai4se_agent/context/prompt.py
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


FINISH_SCHEMA = {
    "name": "finish",
    "description": "Signal that the task is complete",
    "parameters": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Brief summary of what was accomplished"
            }
        },
        "required": []
    }
}


def build_system_prompt(schemas: list[dict]) -> str:
    all_schemas = list(schemas) + [FINISH_SCHEMA]
    tool_descriptions = build_tool_descriptions(all_schemas)

    return (
        "You are a coding agent. You can use the following tools:\n\n"
        f"{tool_descriptions}\n\n"
        "Respond with a JSON object in exactly this format:\n"
        '{"action": "<tool_name>", "parameters": {"key": "value"}}\n\n'
        "For multi-line content, use \\n for newlines inside the JSON string:\n"
        '{"action": "write_file", "parameters": {"path": "main.cpp", "content": "#include <iostream>\\nint main() {}\\n"}}\n\n'
        "To finish the task, use the finish action:\n"
        '{"action": "finish", "parameters": {"summary": "Task completed"}}\n\n'
        "Example:\n"
        '{"action": "write_file", "parameters": {"path": "main.cpp", "content": "#include <iostream>\\nint main() { std::cout << \\"hello\\"; }\\n"}}\n'
        '{"action": "shell", "parameters": {"command": "g++ -o main main.cpp"}}\n'
        '{"action": "shell", "parameters": {"command": "main.exe"}}\n'
        '{"action": "finish", "parameters": {"summary": "Compiled and ran successfully"}}'
    )
```

- [ ] **Step 5: Update state_machine.py to pass ToolRegistry**

```python
# src/ai4se_agent/core/state_machine.py — line 61
self._context_builder = ContextBuilder(tool_registry=self.tools)
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/context/test_builder.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/ai4se_agent/context/prompt.py src/ai4se_agent/context/builder.py src/ai4se_agent/core/state_machine.py tests/context/test_builder.py
git commit -m "feat: dynamic system prompt from Tool schemas, JSON format, context builder takes ToolRegistry"
```

---

### Task 5: State Machine — finish action + [DONE] removal

**Files:**
- Modify: `src/ai4se_agent/core/state_machine.py`
- Modify: `src/ai4se_agent/cli/session.py`
- Modify: `src/ai4se_agent/cli/main.py`
- Test: `tests/core/test_state_machine.py`

**Interfaces:**
- Consumes: `finish` action from Task 3, `ActionValidator` from Task 3
- Produces: `[DONE]`-free state machine, `finish` triggers STOP

- [ ] **Step 1: Write the failing tests**

```python
# tests/core/test_state_machine.py — update
from ai4se_agent.core.state_machine import HarnessStateMachine
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.llm.mock_adapter import MockAdapter
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.guardrails.engine import GuardrailEngine
from ai4se_agent.memory.manager import MemoryManager
from ai4se_agent.cli.renderer import NullRenderer
from ai4se_agent.observability.tracer import NullTracer


SCHEMAS = [
    {
        "name": "read_file",
        "description": "Read a file",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path"}},
            "required": ["path"]
        }
    },
    {
        "name": "finish",
        "description": "Finish task",
        "parameters": {
            "type": "object",
            "properties": {"summary": {"type": "string", "description": "Summary"}},
            "required": []
        }
    }
]


def test_state_machine_finish_action(tmp_path):
    llm = MockAdapter(responses=[
        '{"action": "read_file", "parameters": {"path": "' + str(tmp_path / "test.txt") + '"}}',
        '{"action": "finish", "parameters": {"summary": "done"}}'
    ])
    registry = ToolRegistry()
    guardrails = GuardrailEngine()
    state = AgentState(goal="test task")
    machine = HarnessStateMachine(
        agent_state=state,
        llm_adapter=llm,
        action_parser=ActionParser(),
        action_validator=ActionValidator(SCHEMAS),
        tool_registry=registry,
        guardrail_engine=guardrails,
        feedback_loop=None,
        memory_manager=MemoryManager(),
        max_iterations=5
    )
    result = machine.run()
    assert result["status"] == "success"
    assert result["iterations"] == 2


def test_state_machine_stops_on_finish():
    llm = MockAdapter(responses=['{"action": "finish", "parameters": {}}'])
    registry = ToolRegistry()
    guardrails = GuardrailEngine()
    state = AgentState(goal="test")
    machine = HarnessStateMachine(
        agent_state=state,
        llm_adapter=llm,
        action_parser=ActionParser(),
        action_validator=ActionValidator(SCHEMAS),
        tool_registry=registry,
        guardrail_engine=guardrails,
        feedback_loop=None,
        memory_manager=MemoryManager(),
        max_iterations=5
    )
    result = machine.run()
    assert result["status"] == "success"
    assert result["iterations"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/core/test_state_machine.py -v`
Expected: FAIL (old tests reference [DONE], new tests expect finish action)

- [ ] **Step 3: Update state machine — replace [DONE] with finish action**

```python
# src/ai4se_agent/core/state_machine.py — replace _on_action_parse
def _on_action_parse(self) -> None:
    last_msg = self.state.history[-1]["content"]
    result = self.parser.parse(last_msg)
    if not result.success:
        self.retry_parse()
        return
    action = result.action
    errors = self.validator.validate(action)
    if errors:
        self.retry_parse()
        return
    if action.name == "finish":
        self.stop_reason = StopReason.SUCCESS
        self._renderer.on_state_change("ACTION_PARSE", "STOP", self.state.iteration)
        self.stop()
        return
    self._pending_action = action
    self._tracer.record(
        ActionEvent(self.state.iteration, action.name, action.parameters)
    )
    self.check_guardrails()
```

- [ ] **Step 4: Update session.py — replace [DONE] with finish action**

```python
# src/ai4se_agent/cli/session.py — line 48
llm: Any = MockAdapter(
    responses=['{"action": "shell", "parameters": {"command": "echo hello"}}', '{"action": "finish", "parameters": {}}']
)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/core/test_state_machine.py -v`
Expected: PASS (all tests)

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest -v`
Expected: 69+ tests pass (new tests added in Tasks 1-5)

- [ ] **Step 7: Commit**

```bash
git add src/ai4se_agent/core/state_machine.py src/ai4se_agent/cli/session.py tests/core/test_state_machine.py
git commit -m "feat: replace [DONE] with finish action in state machine"
```

---

### Task 6: Integration Wiring + Full Test Pass

**Files:**
- Modify: `src/ai4se_agent/cli/session.py` (wire ActionValidator with schemas)
- No new tests needed — full suite pass is the verification

**Interfaces:**
- Consumes: All previous tasks
- Produces: Fully wired harness

- [ ] **Step 1: Wire ActionValidator with ToolRegistry schemas in SessionManager**

```python
# src/ai4se_agent/cli/session.py — in _build_harness, after tools are registered
validator = ActionValidator(schemas=tools.list_schemas())

return HarnessStateMachine(
    ...
    action_validator=validator,
    ...
)
```

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest -v`
Expected: ALL PASS

- [ ] **Step 3: End-to-end test with mock LLM**

Run: `ai4se-agent "write a hello world C++ program"` (uses mock adapter if configured)
Expected: Runs successfully

- [ ] **Step 4: Commit**

```bash
git add src/ai4se_agent/cli/session.py
git commit -m "feat: wire ActionValidator with ToolRegistry schemas in SessionManager"
```

---

## Self-Review Checklist

1. **Spec coverage:** Every item from the spec has a corresponding task:
   - ToolSchema (dict parameters) → Task 1-2
   - Action.parameters → Task 1, Task 3 Step 4
   - ParseResult → Task 1
   - JSON extraction (text wrapping) → Task 3 (ActionParser._try_json)
   - finish through Validator → Task 3 (finish schema), Task 5 (state machine)
   - Validator type checking → Task 3 (ActionValidator)
   - Legacy parser fallback → Task 3 (LegacyActionParser)

2. **Placeholder scan:** All code blocks contain complete, runnable implementations. No TBD/TODO.

3. **Type consistency:** `Action.parameters` used throughout. `ParseResult.success`/`.action`/`.error` consistent. `Tool.schema` returns dict matching OpenAI function calling format.