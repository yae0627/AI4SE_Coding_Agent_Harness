diff --git a/src/ai4se_agent/tools/base.py b/src/ai4se_agent/tools/base.py
new file mode 100644
index 0000000..ab05a3a
--- /dev/null
+++ b/src/ai4se_agent/tools/base.py
@@ -0,0 +1,10 @@
+from abc import ABC, abstractmethod
+from ai4se_agent.types import ToolResult
+
+
+class Tool(ABC):
+    name: str
+
+    @abstractmethod
+    def execute(self, params: dict) -> ToolResult:
+        pass
diff --git a/src/ai4se_agent/tools/edit_file.py b/src/ai4se_agent/tools/edit_file.py
new file mode 100644
index 0000000..efc01ef
--- /dev/null
+++ b/src/ai4se_agent/tools/edit_file.py
@@ -0,0 +1,21 @@
+from pathlib import Path
+from ai4se_agent.tools.base import Tool
+from ai4se_agent.types import ToolResult
+
+
+class EditFileTool(Tool):
+    name = "edit_file"
+
+    def execute(self, params: dict) -> ToolResult:
+        path = Path(params["path"])
+        old = params["old_string"]
+        new = params["new_string"]
+        try:
+            content = path.read_text(encoding="utf-8")
+            if old not in content:
+                return ToolResult(success=False, output="", error=f"String not found: {old[:50]}")
+            new_content = content.replace(old, new, 1)
+            path.write_text(new_content, encoding="utf-8")
+            return ToolResult(success=True, output="Edit applied")
+        except Exception as e:
+            return ToolResult(success=False, output="", error=str(e))
diff --git a/src/ai4se_agent/tools/read_file.py b/src/ai4se_agent/tools/read_file.py
new file mode 100644
index 0000000..916575c
--- /dev/null
+++ b/src/ai4se_agent/tools/read_file.py
@@ -0,0 +1,15 @@
+from pathlib import Path
+from ai4se_agent.tools.base import Tool
+from ai4se_agent.types import ToolResult
+
+
+class ReadFileTool(Tool):
+    name = "read_file"
+
+    def execute(self, params: dict) -> ToolResult:
+        path = Path(params["path"])
+        try:
+            content = path.read_text(encoding="utf-8")
+            return ToolResult(success=True, output=content)
+        except Exception as e:
+            return ToolResult(success=False, output="", error=str(e))
diff --git a/src/ai4se_agent/tools/registry.py b/src/ai4se_agent/tools/registry.py
new file mode 100644
index 0000000..66d8ca8
--- /dev/null
+++ b/src/ai4se_agent/tools/registry.py
@@ -0,0 +1,19 @@
+from ai4se_agent.tools.base import Tool
+from ai4se_agent.types import Action, ToolResult
+
+
+class ToolRegistry:
+    def __init__(self):
+        self._tools: dict[str, Tool] = {}
+
+    def register(self, tool: Tool) -> None:
+        self._tools[tool.name] = tool
+
+    def execute(self, action: Action) -> ToolResult:
+        tool = self._tools.get(action.name)
+        if not tool:
+            return ToolResult(success=False, output="", error=f"Unknown tool: {action.name}")
+        try:
+            return tool.execute(action.params)
+        except Exception as e:
+            return ToolResult(success=False, output="", error=str(e))
diff --git a/src/ai4se_agent/tools/run_test.py b/src/ai4se_agent/tools/run_test.py
new file mode 100644
index 0000000..3a545d5
--- /dev/null
+++ b/src/ai4se_agent/tools/run_test.py
@@ -0,0 +1,24 @@
+import subprocess
+from ai4se_agent.tools.base import Tool
+from ai4se_agent.types import ToolResult
+
+
+class RunTestTool(Tool):
+    name = "run_test"
+
+    def execute(self, params: dict) -> ToolResult:
+        test_path = params.get("test_path", "")
+        args = params.get("args", "")
+        try:
+            cmd = f"python -m pytest {test_path} {args} -v"
+            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
+            output = result.stdout + result.stderr
+            return ToolResult(
+                success=result.returncode == 0,
+                output=output.strip(),
+                metadata={"exit_code": result.returncode}
+            )
+        except subprocess.TimeoutExpired:
+            return ToolResult(success=False, output="", error="Test timed out")
+        except Exception as e:
+            return ToolResult(success=False, output="", error=str(e))
diff --git a/src/ai4se_agent/tools/shell.py b/src/ai4se_agent/tools/shell.py
new file mode 100644
index 0000000..283e685
--- /dev/null
+++ b/src/ai4se_agent/tools/shell.py
@@ -0,0 +1,27 @@
+import subprocess
+from ai4se_agent.tools.base import Tool
+from ai4se_agent.types import ToolResult
+
+
+class ShellTool(Tool):
+    name = "shell"
+
+    def execute(self, params: dict) -> ToolResult:
+        command = params["command"]
+        timeout = params.get("timeout", 30)
+        workdir = params.get("workdir")
+        try:
+            result = subprocess.run(
+                command, shell=True, capture_output=True, text=True,
+                timeout=timeout, cwd=workdir
+            )
+            output = result.stdout + result.stderr
+            return ToolResult(
+                success=result.returncode == 0,
+                output=output.strip(),
+                metadata={"exit_code": result.returncode}
+            )
+        except subprocess.TimeoutExpired:
+            return ToolResult(success=False, output="", error="Command timed out")
+        except Exception as e:
+            return ToolResult(success=False, output="", error=str(e))
diff --git a/src/ai4se_agent/tools/write_file.py b/src/ai4se_agent/tools/write_file.py
new file mode 100644
index 0000000..fe92865
--- /dev/null
+++ b/src/ai4se_agent/tools/write_file.py
@@ -0,0 +1,17 @@
+from pathlib import Path
+from ai4se_agent.tools.base import Tool
+from ai4se_agent.types import ToolResult
+
+
+class WriteFileTool(Tool):
+    name = "write_file"
+
+    def execute(self, params: dict) -> ToolResult:
+        path = Path(params["path"])
+        content = params["content"]
+        try:
+            path.parent.mkdir(parents=True, exist_ok=True)
+            path.write_text(content, encoding="utf-8")
+            return ToolResult(success=True, output=f"Written {len(content)} bytes")
+        except Exception as e:
+            return ToolResult(success=False, output="", error=str(e))
diff --git a/tests/tools/test_edit_file.py b/tests/tools/test_edit_file.py
new file mode 100644
index 0000000..efd3e86
--- /dev/null
+++ b/tests/tools/test_edit_file.py
@@ -0,0 +1,19 @@
+from ai4se_agent.tools.edit_file import EditFileTool
+from ai4se_agent.types import Action
+
+def test_edit_file(tmp_path):
+    tool = EditFileTool()
+    target = tmp_path / "test.txt"
+    target.write_text("hello world\nfoo bar")
+    action = Action(name="edit_file", params={"path": str(target), "old_string": "foo bar", "new_string": "baz qux"})
+    result = tool.execute(action.params)
+    assert result.success is True
+    assert target.read_text() == "hello world\nbaz qux"
+
+def test_edit_file_no_match(tmp_path):
+    tool = EditFileTool()
+    target = tmp_path / "test.txt"
+    target.write_text("hello")
+    action = Action(name="edit_file", params={"path": str(target), "old_string": "nonexistent", "new_string": "replacement"})
+    result = tool.execute(action.params)
+    assert result.success is False
diff --git a/tests/tools/test_read_file.py b/tests/tools/test_read_file.py
new file mode 100644
index 0000000..34aa21c
--- /dev/null
+++ b/tests/tools/test_read_file.py
@@ -0,0 +1,18 @@
+from ai4se_agent.tools.read_file import ReadFileTool
+from ai4se_agent.types import Action
+
+def test_read_existing_file(tmp_path):
+    tool = ReadFileTool()
+    test_file = tmp_path / "test.txt"
+    test_file.write_text("line1\nline2")
+    action = Action(name="read_file", params={"path": str(test_file)})
+    result = tool.execute(action.params)
+    assert result.success is True
+    assert "line1" in result.output
+
+def test_read_nonexistent_file():
+    tool = ReadFileTool()
+    action = Action(name="read_file", params={"path": "/nonexistent/file.txt"})
+    result = tool.execute(action.params)
+    assert result.success is False
+    assert result.error is not None
diff --git a/tests/tools/test_registry.py b/tests/tools/test_registry.py
new file mode 100644
index 0000000..270b599
--- /dev/null
+++ b/tests/tools/test_registry.py
@@ -0,0 +1,13 @@
+from ai4se_agent.tools.registry import ToolRegistry
+from ai4se_agent.tools.read_file import ReadFileTool
+from ai4se_agent.types import Action
+
+def test_register_and_execute(tmp_path):
+    registry = ToolRegistry()
+    registry.register(ReadFileTool())
+    test_file = tmp_path / "test.txt"
+    test_file.write_text("hello")
+    action = Action(name="read_file", params={"path": str(test_file)})
+    result = registry.execute(action)
+    assert result.success is True
+    assert result.output == "hello"
diff --git a/tests/tools/test_run_test.py b/tests/tools/test_run_test.py
new file mode 100644
index 0000000..02bd0d6
--- /dev/null
+++ b/tests/tools/test_run_test.py
@@ -0,0 +1,6 @@
+from ai4se_agent.tools.run_test import RunTestTool
+
+def test_run_test_nonexistent_path():
+    tool = RunTestTool()
+    result = tool.execute({"test_path": "/nonexistent"})
+    assert result.success is False
diff --git a/tests/tools/test_shell.py b/tests/tools/test_shell.py
new file mode 100644
index 0000000..aed75c0
--- /dev/null
+++ b/tests/tools/test_shell.py
@@ -0,0 +1,12 @@
+from ai4se_agent.tools.shell import ShellTool
+
+def test_shell_success():
+    tool = ShellTool()
+    result = tool.execute({"command": "echo hello", "timeout": 5})
+    assert result.success is True
+    assert "hello" in result.output
+
+def test_shell_failure():
+    tool = ShellTool()
+    result = tool.execute({"command": "exit 1", "timeout": 5})
+    assert result.success is False
diff --git a/tests/tools/test_write_file.py b/tests/tools/test_write_file.py
new file mode 100644
index 0000000..fa5a7e2
--- /dev/null
+++ b/tests/tools/test_write_file.py
@@ -0,0 +1,10 @@
+from ai4se_agent.tools.write_file import WriteFileTool
+from ai4se_agent.types import Action
+
+def test_write_file(tmp_path):
+    tool = WriteFileTool()
+    target = tmp_path / "out.txt"
+    action = Action(name="write_file", params={"path": str(target), "content": "new content"})
+    result = tool.execute(action.params)
+    assert result.success is True
+    assert target.read_text() == "new content"
