# Task 5: Tool System

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

## Step 1: Write the failing tests

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

## Step 2: Run tests to verify they fail

Run: `pytest tests/tools/ -v`
Expected: FAIL

## Step 3: Write minimal implementations

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

## Step 4: Run tests

Run: `pytest tests/tools/ -v`
Expected: PASS

## Step 5: Commit

```bash
git add src/ai4se_agent/tools/ tests/tools/
git commit -m "feat: add Tool system with registry and 5 core tools"
```

## Global Constraints

- Python >=3.10
- All core mechanisms must be testable with mock LLM (no network, no real LLM)
- No use of agent orchestration frameworks
- Tests in `tests/` mirroring `src/` structure
- No comments in code unless specified
