diff --git a/src/ai4se_agent/guardrails/base.py b/src/ai4se_agent/guardrails/base.py
new file mode 100644
index 0000000..bf9b063
--- /dev/null
+++ b/src/ai4se_agent/guardrails/base.py
@@ -0,0 +1,8 @@
+from abc import ABC, abstractmethod
+from ai4se_agent.types import Action, GuardrailResult
+
+
+class Policy(ABC):
+    @abstractmethod
+    def check(self, action: Action) -> GuardrailResult | None:
+        pass
diff --git a/src/ai4se_agent/guardrails/command_policy.py b/src/ai4se_agent/guardrails/command_policy.py
new file mode 100644
index 0000000..2bd1f92
--- /dev/null
+++ b/src/ai4se_agent/guardrails/command_policy.py
@@ -0,0 +1,23 @@
+import re
+from ai4se_agent.guardrails.base import Policy
+from ai4se_agent.types import Action, GuardrailResult
+
+
+DANGEROUS_PATTERNS = [
+    r'\brm\s+-rf\s+/', r'\bdd\b', r'\bwget\b', r'\bcurl\b.*[-][-]output',
+    r'\bmkfs', r'\bformat', r'\b> /dev/sda', r'\| sh', r'> /dev/',
+]
+
+
+class CommandPolicy(Policy):
+    def check(self, action: Action) -> GuardrailResult | None:
+        if action.name != "shell":
+            return None
+        command = action.params.get("command", "")
+        for pattern in DANGEROUS_PATTERNS:
+            if re.search(pattern, command):
+                return GuardrailResult(
+                    verdict="DENY", reason=f"Dangerous command matched: {pattern}",
+                    policy="CommandPolicy", severity=5, metadata={"command": command}
+                )
+        return GuardrailResult(verdict="ALLOW", reason="Safe command", policy="CommandPolicy")
diff --git a/src/ai4se_agent/guardrails/engine.py b/src/ai4se_agent/guardrails/engine.py
new file mode 100644
index 0000000..f27700f
--- /dev/null
+++ b/src/ai4se_agent/guardrails/engine.py
@@ -0,0 +1,24 @@
+from ai4se_agent.guardrails.base import Policy
+from ai4se_agent.types import Action, GuardrailResult
+
+
+class GuardrailEngine:
+    def __init__(self):
+        self._policies: list[Policy] = []
+
+    def add_policy(self, policy: Policy) -> None:
+        self._policies.append(policy)
+
+    def check(self, action: Action) -> GuardrailResult:
+        results = []
+        for policy in self._policies:
+            result = policy.check(action)
+            if result is not None:
+                results.append(result)
+        for r in results:
+            if r.verdict == "DENY":
+                return r
+        for r in results:
+            if r.verdict == "REQUIRE_APPROVAL":
+                return r
+        return GuardrailResult(verdict="ALLOW", reason="All policies passed", policy="all")
diff --git a/src/ai4se_agent/guardrails/file_policy.py b/src/ai4se_agent/guardrails/file_policy.py
new file mode 100644
index 0000000..0f90a18
--- /dev/null
+++ b/src/ai4se_agent/guardrails/file_policy.py
@@ -0,0 +1,19 @@
+from ai4se_agent.guardrails.base import Policy
+from ai4se_agent.types import Action, GuardrailResult
+
+
+PROTECTED_PATTERNS = ['.git/', 'node_modules/']
+
+
+class FilePolicy(Policy):
+    def check(self, action: Action) -> GuardrailResult | None:
+        if action.name not in ("write_file", "edit_file", "read_file"):
+            return None
+        path = action.params.get("path", "")
+        for pattern in PROTECTED_PATTERNS:
+            if pattern in path:
+                return GuardrailResult(
+                    verdict="DENY", reason=f"Protected path: {pattern}",
+                    policy="FilePolicy", severity=4, metadata={"path": path}
+                )
+        return GuardrailResult(verdict="ALLOW", reason="Safe path", policy="FilePolicy")
diff --git a/src/ai4se_agent/guardrails/git_policy.py b/src/ai4se_agent/guardrails/git_policy.py
new file mode 100644
index 0000000..cab0602
--- /dev/null
+++ b/src/ai4se_agent/guardrails/git_policy.py
@@ -0,0 +1,20 @@
+import re
+from ai4se_agent.guardrails.base import Policy
+from ai4se_agent.types import Action, GuardrailResult
+
+
+HIGH_RISK_GIT = [r'git\s+push', r'git\s+reset\s+--hard', r'git\s+merge', r'git\s+rebase']
+
+
+class GitPolicy(Policy):
+    def check(self, action: Action) -> GuardrailResult | None:
+        if action.name != "shell":
+            return None
+        command = action.params.get("command", "")
+        for pattern in HIGH_RISK_GIT:
+            if re.search(pattern, command):
+                return GuardrailResult(
+                    verdict="REQUIRE_APPROVAL", reason=f"High-risk git operation: {pattern}",
+                    policy="GitPolicy", severity=3, metadata={"command": command}
+                )
+        return GuardrailResult(verdict="ALLOW", reason="Safe git command", policy="GitPolicy")
diff --git a/src/ai4se_agent/guardrails/workspace_policy.py b/src/ai4se_agent/guardrails/workspace_policy.py
new file mode 100644
index 0000000..cef064b
--- /dev/null
+++ b/src/ai4se_agent/guardrails/workspace_policy.py
@@ -0,0 +1,20 @@
+import os
+from ai4se_agent.guardrails.base import Policy
+from ai4se_agent.types import Action, GuardrailResult
+
+
+class WorkspacePolicy(Policy):
+    def __init__(self, workspace: str):
+        self.workspace = os.path.realpath(workspace)
+
+    def check(self, action: Action) -> GuardrailResult | None:
+        if action.name not in ("read_file", "write_file", "edit_file"):
+            return None
+        path = action.params.get("path", "")
+        real_path = os.path.realpath(path)
+        if not real_path.startswith(self.workspace):
+            return GuardrailResult(
+                verdict="DENY", reason=f"Path escapes workspace: {real_path}",
+                policy="WorkspacePolicy", severity=5, metadata={"path": path, "real_path": real_path}
+            )
+        return GuardrailResult(verdict="ALLOW", reason="Path within workspace", policy="WorkspacePolicy")
diff --git a/tests/guardrails/test_command_policy.py b/tests/guardrails/test_command_policy.py
new file mode 100644
index 0000000..2a6894e
--- /dev/null
+++ b/tests/guardrails/test_command_policy.py
@@ -0,0 +1,14 @@
+from ai4se_agent.guardrails.command_policy import CommandPolicy
+from ai4se_agent.types import Action
+
+def test_block_rm_rf():
+    policy = CommandPolicy()
+    action = Action(name="shell", params={"command": "rm -rf /"})
+    result = policy.check(action)
+    assert result.verdict == "DENY"
+
+def test_allow_safe_command():
+    policy = CommandPolicy()
+    action = Action(name="shell", params={"command": "echo hello"})
+    result = policy.check(action)
+    assert result.verdict == "ALLOW"
diff --git a/tests/guardrails/test_engine.py b/tests/guardrails/test_engine.py
new file mode 100644
index 0000000..edb2ace
--- /dev/null
+++ b/tests/guardrails/test_engine.py
@@ -0,0 +1,10 @@
+from ai4se_agent.guardrails.engine import GuardrailEngine
+from ai4se_agent.guardrails.command_policy import CommandPolicy
+from ai4se_agent.types import Action
+
+def test_engine_block_dangerous():
+    engine = GuardrailEngine()
+    engine.add_policy(CommandPolicy())
+    action = Action(name="shell", params={"command": "rm -rf /"})
+    result = engine.check(action)
+    assert result.verdict == "DENY"
diff --git a/tests/guardrails/test_file_policy.py b/tests/guardrails/test_file_policy.py
new file mode 100644
index 0000000..967d849
--- /dev/null
+++ b/tests/guardrails/test_file_policy.py
@@ -0,0 +1,8 @@
+from ai4se_agent.guardrails.file_policy import FilePolicy
+from ai4se_agent.types import Action
+
+def test_block_git_write():
+    policy = FilePolicy()
+    action = Action(name="write_file", params={"path": "/workspace/.git/config", "content": ""})
+    result = policy.check(action)
+    assert result.verdict == "DENY"
diff --git a/tests/guardrails/test_git_policy.py b/tests/guardrails/test_git_policy.py
new file mode 100644
index 0000000..91bfa35
--- /dev/null
+++ b/tests/guardrails/test_git_policy.py
@@ -0,0 +1,14 @@
+from ai4se_agent.guardrails.git_policy import GitPolicy
+from ai4se_agent.types import Action
+
+def test_block_push():
+    policy = GitPolicy()
+    action = Action(name="shell", params={"command": "git push origin main"})
+    result = policy.check(action)
+    assert result.verdict == "REQUIRE_APPROVAL"
+
+def test_allow_status():
+    policy = GitPolicy()
+    action = Action(name="shell", params={"command": "git status"})
+    result = policy.check(action)
+    assert result.verdict == "ALLOW"
diff --git a/tests/guardrails/test_workspace_policy.py b/tests/guardrails/test_workspace_policy.py
new file mode 100644
index 0000000..f29212a
--- /dev/null
+++ b/tests/guardrails/test_workspace_policy.py
@@ -0,0 +1,17 @@
+from ai4se_agent.guardrails.workspace_policy import WorkspacePolicy
+from ai4se_agent.types import Action
+
+def test_block_path_escape(tmp_path):
+    policy = WorkspacePolicy(workspace=str(tmp_path))
+    action = Action(name="read_file", params={"path": str(tmp_path / "../../etc/passwd")})
+    result = policy.check(action)
+    assert result.verdict == "DENY"
+
+def test_allow_inside_workspace(tmp_path):
+    policy = WorkspacePolicy(workspace=str(tmp_path))
+    inner = tmp_path / "subdir" / "file.txt"
+    inner.parent.mkdir()
+    inner.write_text("")
+    action = Action(name="read_file", params={"path": str(inner)})
+    result = policy.check(action)
+    assert result.verdict == "ALLOW"
