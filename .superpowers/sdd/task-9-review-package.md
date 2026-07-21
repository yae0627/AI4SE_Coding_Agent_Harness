diff --git a/src/ai4se_agent/feedback/classifier.py b/src/ai4se_agent/feedback/classifier.py
new file mode 100644
index 0000000..7443f34
--- /dev/null
+++ b/src/ai4se_agent/feedback/classifier.py
@@ -0,0 +1,16 @@
+from ai4se_agent.types import Feedback
+
+
+class FailureClassifier:
+    def classify(self, feedback: Feedback) -> dict:
+        if feedback.category == "lint_error":
+            return {"type": "syntax_error", "category": feedback.category, "message": feedback.message}
+        if feedback.category == "type_error":
+            return {"type": "type_error", "category": feedback.category, "message": feedback.message}
+        if "AssertionError" in feedback.message:
+            return {"type": "logic_error", "category": feedback.category, "message": feedback.message}
+        if "ImportError" in feedback.message or "ModuleNotFoundError" in feedback.message:
+            return {"type": "missing_dependency", "category": feedback.category, "message": feedback.message}
+        if "timeout" in feedback.message.lower():
+            return {"type": "timeout", "category": feedback.category, "message": feedback.message}
+        return {"type": "unknown", "category": feedback.category, "message": feedback.message}
diff --git a/src/ai4se_agent/feedback/failure_db.py b/src/ai4se_agent/feedback/failure_db.py
new file mode 100644
index 0000000..505e2ae
--- /dev/null
+++ b/src/ai4se_agent/feedback/failure_db.py
@@ -0,0 +1,38 @@
+import sqlite3
+from pathlib import Path
+
+
+class FailureDB:
+    def __init__(self, db_path: str = "memory/failure.db"):
+        self._db_path = db_path
+        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
+        self._init_db()
+
+    def _init_db(self) -> None:
+        with sqlite3.connect(self._db_path) as conn:
+            conn.execute("""
+                CREATE TABLE IF NOT EXISTS failure_patterns (
+                    id INTEGER PRIMARY KEY AUTOINCREMENT,
+                    failure_type TEXT NOT NULL,
+                    pattern TEXT NOT NULL,
+                    fix_strategy TEXT,
+                    count INTEGER DEFAULT 1,
+                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
+                )
+            """)
+
+    def record_failure(self, failure_type: str, pattern: str, fix_strategy: str = "") -> None:
+        with sqlite3.connect(self._db_path) as conn:
+            conn.execute(
+                "INSERT INTO failure_patterns (failure_type, pattern, fix_strategy) VALUES (?, ?, ?)",
+                (failure_type, pattern, fix_strategy)
+            )
+
+    def query_similar(self, failure_type: str) -> list[dict]:
+        with sqlite3.connect(self._db_path) as conn:
+            conn.row_factory = sqlite3.Row
+            cursor = conn.execute(
+                "SELECT * FROM failure_patterns WHERE failure_type = ? ORDER BY count DESC LIMIT 5",
+                (failure_type,)
+            )
+            return [dict(row) for row in cursor.fetchall()]
diff --git a/src/ai4se_agent/feedback/loop.py b/src/ai4se_agent/feedback/loop.py
new file mode 100644
index 0000000..4fd5aee
--- /dev/null
+++ b/src/ai4se_agent/feedback/loop.py
@@ -0,0 +1,22 @@
+from ai4se_agent.feedback.sensor import Sensor
+from ai4se_agent.feedback.classifier import FailureClassifier
+from ai4se_agent.feedback.planner import CorrectionPlanner
+from ai4se_agent.types import ToolResult, CorrectionPlan
+
+
+class FeedbackLoop:
+    def __init__(self, sensors: list[Sensor], classifier: FailureClassifier, planner: CorrectionPlanner):
+        self._sensors = sensors
+        self._classifier = classifier
+        self._planner = planner
+
+    def run(self, result: ToolResult, retry_count: int = 0) -> CorrectionPlan | None:
+        if result.success:
+            return None
+        for sensor in self._sensors:
+            feedback = sensor.sense(result)
+            if feedback and not feedback.success:
+                classification = self._classifier.classify(feedback)
+                plan = self._planner.plan(result, classification, retry_count)
+                return plan
+        return None
diff --git a/src/ai4se_agent/feedback/planner.py b/src/ai4se_agent/feedback/planner.py
new file mode 100644
index 0000000..ea1c966
--- /dev/null
+++ b/src/ai4se_agent/feedback/planner.py
@@ -0,0 +1,31 @@
+from ai4se_agent.types import ToolResult, CorrectionPlan
+
+
+class CorrectionPlanner:
+    def plan(self, result: ToolResult, classification: dict, retry_count: int = 0) -> CorrectionPlan:
+        if classification["type"] == "logic_error":
+            return CorrectionPlan(
+                scope="Fix assertion failure in test output",
+                target_files=self._extract_files(result.output),
+                strategy="Analyze the test failure and fix the logic in the relevant code",
+                retry_count=retry_count
+            )
+        elif classification["type"] == "syntax_error":
+            return CorrectionPlan(
+                scope="Fix lint/type errors",
+                target_files=self._extract_files(result.output),
+                strategy="Fix the reported syntax or type issues",
+                retry_count=retry_count
+            )
+        else:
+            return CorrectionPlan(
+                scope="General fix",
+                target_files=self._extract_files(result.output),
+                strategy="Review the error and fix the issue",
+                retry_count=retry_count
+            )
+
+    def _extract_files(self, output: str) -> list:
+        import re
+        files = re.findall(r'(\S+\.py):', output)
+        return list(set(files)) if files else ["unknown"]
diff --git a/src/ai4se_agent/feedback/sensor.py b/src/ai4se_agent/feedback/sensor.py
new file mode 100644
index 0000000..f2d02a3
--- /dev/null
+++ b/src/ai4se_agent/feedback/sensor.py
@@ -0,0 +1,41 @@
+from abc import ABC, abstractmethod
+from ai4se_agent.types import ToolResult, Feedback
+
+
+class Sensor(ABC):
+    @abstractmethod
+    def sense(self, result: ToolResult) -> Feedback | None:
+        pass
+
+
+class TestSensor(Sensor):
+    def sense(self, result: ToolResult) -> Feedback | None:
+        if result.metadata.get("exit_code") == 0:
+            return Feedback(success=True, category="test_success", message="All tests passed",
+                            source="pytest")
+        return Feedback(
+            success=False, category="test_failure", message=result.output,
+            source="pytest", severity=3, details={"exit_code": result.metadata.get("exit_code", 1)}
+        )
+
+
+class LintSensor(Sensor):
+    def sense(self, result: ToolResult) -> Feedback | None:
+        if result.success:
+            return Feedback(success=True, category="lint_success", message="Clean lint",
+                            source="ruff")
+        return Feedback(
+            success=False, category="lint_error", message=result.output,
+            source="ruff", severity=2
+        )
+
+
+class TypeSensor(Sensor):
+    def sense(self, result: ToolResult) -> Feedback | None:
+        if result.success:
+            return Feedback(success=True, category="type_success", message="Clean types",
+                            source="mypy")
+        return Feedback(
+            success=False, category="type_error", message=result.output,
+            source="mypy", severity=2
+        )
diff --git a/tests/feedback/test_classifier.py b/tests/feedback/test_classifier.py
new file mode 100644
index 0000000..d29033f
--- /dev/null
+++ b/tests/feedback/test_classifier.py
@@ -0,0 +1,16 @@
+from ai4se_agent.feedback.classifier import FailureClassifier
+from ai4se_agent.types import Feedback
+
+def test_classify_assertion_error():
+    classifier = FailureClassifier()
+    fb = Feedback(success=False, category="test_failure", message="AssertionError: expected 5 got 3",
+                  details={"line": 42}, severity=3, source="pytest")
+    result = classifier.classify(fb)
+    assert result["type"] == "logic_error"
+
+def test_classify_lint_error():
+    classifier = FailureClassifier()
+    fb = Feedback(success=False, category="lint_error", message="F401 imported but unused",
+                  details={}, severity=2, source="ruff")
+    result = classifier.classify(fb)
+    assert result["type"] == "syntax_error"
diff --git a/tests/feedback/test_failure_db.py b/tests/feedback/test_failure_db.py
new file mode 100644
index 0000000..0fccb0e
--- /dev/null
+++ b/tests/feedback/test_failure_db.py
@@ -0,0 +1,8 @@
+from ai4se_agent.feedback.failure_db import FailureDB
+
+def test_failure_db_save_and_query(tmp_path):
+    db = FailureDB(db_path=str(tmp_path / "test_failure.db"))
+    db.record_failure("logic_error", "Missing null check on order_id", "Add guard clause before query")
+    results = db.query_similar("logic_error")
+    assert len(results) >= 1
+    assert results[0]["failure_type"] == "logic_error"
diff --git a/tests/feedback/test_loop.py b/tests/feedback/test_loop.py
new file mode 100644
index 0000000..43017b4
--- /dev/null
+++ b/tests/feedback/test_loop.py
@@ -0,0 +1,16 @@
+from ai4se_agent.feedback.loop import FeedbackLoop
+from ai4se_agent.feedback.sensor import TestSensor
+from ai4se_agent.feedback.classifier import FailureClassifier
+from ai4se_agent.feedback.planner import CorrectionPlanner
+from ai4se_agent.types import ToolResult
+
+def test_feedback_loop_produces_correction():
+    loop = FeedbackLoop(
+        sensors=[TestSensor()],
+        classifier=FailureClassifier(),
+        planner=CorrectionPlanner()
+    )
+    result = ToolResult(success=False, output="FAILED - AssertionError", metadata={"exit_code": 1})
+    plan = loop.run(result)
+    assert plan is not None
+    assert plan.retry_count == 0
diff --git a/tests/feedback/test_planner.py b/tests/feedback/test_planner.py
new file mode 100644
index 0000000..54a276c
--- /dev/null
+++ b/tests/feedback/test_planner.py
@@ -0,0 +1,11 @@
+from ai4se_agent.feedback.planner import CorrectionPlanner
+from ai4se_agent.types import ToolResult
+
+def test_planner_generates_plan():
+    planner = CorrectionPlanner()
+    result = ToolResult(success=False, output="FAILED test_order.py::test_validate - AssertionError",
+                        metadata={"exit_code": 1})
+    plan = planner.plan(result, {"type": "logic_error", "category": "test_failure"})
+    assert plan.scope is not None
+    assert len(plan.target_files) > 0
+    assert plan.retry_count == 0
diff --git a/tests/feedback/test_sensor.py b/tests/feedback/test_sensor.py
new file mode 100644
index 0000000..20c57fa
--- /dev/null
+++ b/tests/feedback/test_sensor.py
@@ -0,0 +1,17 @@
+from ai4se_agent.feedback.sensor import TestSensor
+from ai4se_agent.types import ToolResult
+
+def test_test_sensor_parses_failure():
+    sensor = TestSensor()
+    result = ToolResult(success=False, output="FAILED test_order.py::test_validate - AssertionError: expected True got False",
+                        metadata={"exit_code": 1})
+    feedback = sensor.sense(result)
+    assert feedback.success is False
+    assert feedback.category == "test_failure"
+    assert feedback.source == "pytest"
+
+def test_test_sensor_parses_success():
+    sensor = TestSensor()
+    result = ToolResult(success=True, output="1 passed", metadata={"exit_code": 0})
+    feedback = sensor.sense(result)
+    assert feedback.success is True
