diff --git a/src/ai4se_agent/types.py b/src/ai4se_agent/types.py
new file mode 100644
index 0000000..f16fa89
--- /dev/null
+++ b/src/ai4se_agent/types.py
@@ -0,0 +1,54 @@
+# src/ai4se_agent/types.py
+from dataclasses import dataclass, field
+from enum import Enum
+from typing import Literal, Optional
+
+
+class StopReason(Enum):
+    SUCCESS = "success"
+    MAX_ITERATION = "max_iteration"
+    REPEATED_FAILURE = "repeated_failure"
+    LLM_ERROR = "llm_error"
+    USER_CANCEL = "user_cancel"
+    APPROVAL_TIMEOUT = "approval_timeout"
+
+
+@dataclass
+class Action:
+    name: str
+    params: dict
+
+
+@dataclass
+class ToolResult:
+    success: bool
+    output: str
+    error: Optional[str] = None
+    metadata: dict = field(default_factory=dict)
+
+
+@dataclass
+class Feedback:
+    success: bool
+    category: str
+    message: str
+    details: dict = field(default_factory=dict)
+    severity: int = 0
+    source: str = ""
+
+
+@dataclass
+class GuardrailResult:
+    verdict: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"]
+    reason: str
+    policy: str
+    severity: int = 0
+    metadata: dict = field(default_factory=dict)
+
+
+@dataclass
+class CorrectionPlan:
+    scope: str
+    target_files: list
+    strategy: str
+    retry_count: int = 0
diff --git a/tests/core/test_types.py b/tests/core/test_types.py
new file mode 100644
index 0000000..377b07f
--- /dev/null
+++ b/tests/core/test_types.py
@@ -0,0 +1,31 @@
+# tests/core/test_types.py
+from ai4se_agent.types import Action, ToolResult, Feedback, GuardrailResult, CorrectionPlan, StopReason
+
+def test_action_creation():
+    action = Action(name="read_file", params={"path": "test.txt"})
+    assert action.name == "read_file"
+    assert action.params == {"path": "test.txt"}
+
+def test_tool_result_defaults():
+    result = ToolResult(success=True, output="file content", error=None)
+    assert result.success is True
+    assert result.metadata == {}
+
+def test_feedback_with_source():
+    fb = Feedback(success=False, category="test_failure", message="AssertionError",
+                  details={"line": 42}, severity=3, source="pytest")
+    assert fb.source == "pytest"
+    assert fb.severity == 3
+
+def test_guardrail_result_verdict():
+    gr = GuardrailResult(verdict="DENY", reason="dangerous command", policy="CommandPolicy",
+                         severity=5, metadata={"command": "rm -rf /"})
+    assert gr.verdict == "DENY"
+
+def test_correction_plan():
+    plan = CorrectionPlan(scope="validate()", target_files=["order.py"], strategy="Add null check", retry_count=0)
+    assert plan.retry_count == 0
+
+def test_stop_reason_values():
+    assert StopReason.SUCCESS.value == "success"
+    assert StopReason.MAX_ITERATION.value == "max_iteration"
