diff --git a/.gitignore b/.gitignore
index 383fec4..dba7e09 100644
--- a/.gitignore
+++ b/.gitignore
@@ -36,15 +36,15 @@ htmlcov/
 coverage.xml
 
 # Distribution
 *.tar.gz
 *.whl
 
 # Agent logs (runtime generated)
 *.agent-log.json
 
 # Runtime storage
-memory/
+/memory/
 *.db
 
 # Git worktrees
 .worktrees/
\ No newline at end of file
diff --git a/src/ai4se_agent/memory/manager.py b/src/ai4se_agent/memory/manager.py
new file mode 100644
index 0000000..98750ba
--- /dev/null
+++ b/src/ai4se_agent/memory/manager.py
@@ -0,0 +1,14 @@
+from ai4se_agent.memory.session import SessionMemory
+from ai4se_agent.memory.persistent import PersistentMemory
+
+
+class MemoryManager:
+    def __init__(self, session: SessionMemory | None = None, persistent: PersistentMemory | None = None):
+        self.session = session or SessionMemory()
+        self.persistent = persistent or PersistentMemory()
+
+    def add_to_session(self, role: str, content: str) -> None:
+        self.session.add(role, content)
+
+    def get_session_history(self) -> list:
+        return self.session.get_all()
diff --git a/src/ai4se_agent/memory/persistent.py b/src/ai4se_agent/memory/persistent.py
new file mode 100644
index 0000000..4598c0c
--- /dev/null
+++ b/src/ai4se_agent/memory/persistent.py
@@ -0,0 +1,25 @@
+from pathlib import Path
+
+
+class PersistentMemory:
+    def __init__(self, base_dir: str = "memory"):
+        self._rules_dir = Path(base_dir) / "project_rules"
+        self._summaries_dir = Path(base_dir) / "session_summaries"
+        self._rules_dir.mkdir(parents=True, exist_ok=True)
+        self._summaries_dir.mkdir(parents=True, exist_ok=True)
+
+    def save_rule(self, name: str, content: str) -> None:
+        (self._rules_dir / f"{name}.md").write_text(content, encoding="utf-8")
+
+    def load_rule(self, name: str) -> str | None:
+        path = self._rules_dir / f"{name}.md"
+        return path.read_text(encoding="utf-8") if path.exists() else None
+
+    def list_rules(self) -> list[str]:
+        return [p.stem for p in self._rules_dir.glob("*.md")]
+
+    def save_summary(self, session_id: str, summary: str) -> None:
+        (self._summaries_dir / f"{session_id}.md").write_text(summary, encoding="utf-8")
+
+    def list_summaries(self) -> list[str]:
+        return [p.stem for p in self._summaries_dir.glob("*.md")]
diff --git a/src/ai4se_agent/memory/session.py b/src/ai4se_agent/memory/session.py
new file mode 100644
index 0000000..11955f0
--- /dev/null
+++ b/src/ai4se_agent/memory/session.py
@@ -0,0 +1,18 @@
+from collections import deque
+
+
+class SessionMemory:
+    def __init__(self, max_turns: int = 50):
+        self._turns = deque(maxlen=max_turns)
+
+    def add(self, role: str, content: str) -> None:
+        self._turns.append({"role": role, "content": content})
+
+    def get_recent(self, n: int) -> list:
+        return list(self._turns)[-n:]
+
+    def get_all(self) -> list:
+        return list(self._turns)
+
+    def clear(self) -> None:
+        self._turns.clear()
diff --git a/tests/memory/__init__.py b/tests/memory/__init__.py
new file mode 100644
index 0000000..e69de29
diff --git a/tests/memory/test_manager.py b/tests/memory/test_manager.py
new file mode 100644
index 0000000..bf2a785
--- /dev/null
+++ b/tests/memory/test_manager.py
@@ -0,0 +1,8 @@
+from ai4se_agent.memory.manager import MemoryManager
+from ai4se_agent.memory.session import SessionMemory
+from ai4se_agent.memory.persistent import PersistentMemory
+
+def test_manager_adds_to_session(tmp_path):
+    mgr = MemoryManager(session=SessionMemory(), persistent=PersistentMemory(base_dir=str(tmp_path)))
+    mgr.add_to_session("user", "test")
+    assert len(mgr.get_session_history()) == 1
diff --git a/tests/memory/test_persistent.py b/tests/memory/test_persistent.py
new file mode 100644
index 0000000..3f573c9
--- /dev/null
+++ b/tests/memory/test_persistent.py
@@ -0,0 +1,13 @@
+from ai4se_agent.memory.persistent import PersistentMemory
+
+def test_save_and_load_rule(tmp_path):
+    mem = PersistentMemory(base_dir=str(tmp_path))
+    mem.save_rule("branch_naming", "Use feat/ prefix")
+    loaded = mem.load_rule("branch_naming")
+    assert loaded == "Use feat/ prefix"
+
+def test_save_summary(tmp_path):
+    mem = PersistentMemory(base_dir=str(tmp_path))
+    mem.save_summary("session-1", "Fixed bug in validator")
+    summaries = mem.list_summaries()
+    assert len(summaries) >= 1
diff --git a/tests/memory/test_session.py b/tests/memory/test_session.py
new file mode 100644
index 0000000..8a39e1b
--- /dev/null
+++ b/tests/memory/test_session.py
@@ -0,0 +1,17 @@
+from ai4se_agent.memory.session import SessionMemory
+
+def test_session_add_and_get():
+    mem = SessionMemory(max_turns=5)
+    mem.add("user", "hello")
+    mem.add("assistant", "hi")
+    turns = mem.get_recent(2)
+    assert len(turns) == 2
+    assert turns[0]["role"] == "user"
+
+def test_session_lru_eviction():
+    mem = SessionMemory(max_turns=3)
+    for i in range(5):
+        mem.add("user", f"msg{i}")
+    turns = mem.get_recent(10)
+    assert len(turns) == 3
+    assert turns[0]["content"] == "msg2"
