diff --git a/src/ai4se_agent/core/agent_state.py b/src/ai4se_agent/core/agent_state.py
new file mode 100644
index 0000000..4a4dea7
--- /dev/null
+++ b/src/ai4se_agent/core/agent_state.py
@@ -0,0 +1,25 @@
+from dataclasses import dataclass, field
+from typing import Optional
+
+from ai4se_agent.types import Action
+
+
+@dataclass
+class AgentState:
+    goal: str
+    current_state: str = "IDLE"
+    iteration: int = 0
+    context: list = field(default_factory=list)
+    history: list = field(default_factory=list)
+    last_action: Optional[Action] = None
+    last_observation: Optional[str] = None
+    error_count: int = 0
+    retry_count: int = 0
+
+    def record_turn(self, action: Action, observation: str) -> None:
+        self.history.append({"action": action, "observation": observation})
+        self.last_action = action
+        self.last_observation = observation
+
+    def increment_iteration(self) -> None:
+        self.iteration += 1
diff --git a/tests/core/test_agent_state.py b/tests/core/test_agent_state.py
new file mode 100644
index 0000000..1f0d8ce
--- /dev/null
+++ b/tests/core/test_agent_state.py
@@ -0,0 +1,21 @@
+from ai4se_agent.core.agent_state import AgentState
+from ai4se_agent.types import Action
+
+def test_agent_state_initialization():
+    state = AgentState(goal="fix the bug")
+    assert state.goal == "fix the bug"
+    assert state.current_state == "IDLE"
+    assert state.iteration == 0
+    assert state.retry_count == 0
+
+def test_agent_state_record_turn():
+    state = AgentState(goal="test")
+    action = Action(name="shell", params={"command": "pytest"})
+    state.record_turn(action, "test output")
+    assert len(state.history) == 1
+    assert state.history[0]["action"].name == "shell"
+
+def test_agent_state_increment():
+    state = AgentState(goal="test")
+    state.increment_iteration()
+    assert state.iteration == 1
