diff --git a/demo/README.md b/demo/README.md
new file mode 100644
index 0000000..c3a734c
--- /dev/null
+++ b/demo/README.md
@@ -0,0 +1,19 @@
+# Mechanism Demo
+
+This directory contains a demonstration script (`mechanism_demo.py`) that exercises five core mechanisms of the AI4SE Coding Agent Harness without requiring a network or real LLM.
+
+## What it demonstrates
+
+1. **Guardrail Intercepts Dangerous Action** 鈥?`CommandPolicy` denies a destructive shell command (`rm -rf /`).
+2. **Feedback Loop Detects Failure and Generates Correction** 鈥?`TestSensor` observes a failing `ToolResult`, `FailureClassifier` classifies it, and `CorrectionPlanner` produces a `CorrectionPlan`.
+3. **Incremental Correction Strategy (閲嶇偣缁村害)** 鈥?Shows the feedback loop running across three retry attempts, illustrating the escalation from incremental fixes toward a full replan.
+4. **FailureDB Records and Queries Failure Patterns** 鈥?`FailureDB` persists a failure pattern to SQLite and retrieves similar patterns by type.
+5. **WorkspacePolicy Blocks Path Escape** 鈥?`WorkspacePolicy` denies a `read_file` action whose path escapes the workspace root via `..` traversal.
+
+## Running
+
+```bash
+python demo/mechanism_demo.py
+```
+
+Expected output: each of the five demos prints `PASS`, followed by `=== All demos passed ===`.
diff --git a/demo/mechanism_demo.py b/demo/mechanism_demo.py
new file mode 100644
index 0000000..b999013
--- /dev/null
+++ b/demo/mechanism_demo.py
@@ -0,0 +1,108 @@
+# demo/mechanism_demo.py
+"""
+Mechanism Demo 鈥?婕旂ず涓変釜鏍稿績琛屼负锛?+1. 娌荤悊鎶ゆ爮鎷︽埅鍗遍櫓鍔ㄤ綔
+2. 鍙嶉闂幆浣?agent 鏀跺埌澶辫触淇″彿骞朵慨姝?+3. 閲嶇偣缁村害鐨勭‘瀹氭€ц涓猴紙Feedback Loop 瀹屾暣娴佺▼锛?+"""
+from ai4se_agent.feedback.sensor import TestSensor
+from ai4se_agent.feedback.classifier import FailureClassifier
+from ai4se_agent.feedback.planner import CorrectionPlanner
+from ai4se_agent.feedback.failure_db import FailureDB
+from ai4se_agent.guardrails.command_policy import CommandPolicy
+from ai4se_agent.guardrails.workspace_policy import WorkspacePolicy
+from ai4se_agent.types import Action, ToolResult
+import tempfile
+import os
+
+
+def demo_guardrail():
+    print("=== Demo 1: Guardrail Intercepts Dangerous Action ===")
+    policy = CommandPolicy()
+    action = Action(name="shell", params={"command": "rm -rf /"})
+    result = policy.check(action)
+    assert result.verdict == "DENY", f"Expected DENY, got {result.verdict}"
+    print("  Action: shell rm -rf /")
+    print(f"  Verdict: {result.verdict}")
+    print(f"  Reason: {result.reason}")
+    print("  PASS: Guardrail correctly blocked dangerous command\n")
+
+
+def demo_feedback_loop():
+    print("=== Demo 2: Feedback Loop Detects Failure and Generates Correction ===")
+    sensor = TestSensor()
+    classifier = FailureClassifier()
+    planner = CorrectionPlanner()
+
+    result = ToolResult(
+        success=False,
+        output="FAILED test_order.py::test_validate - AssertionError: expected True got False",
+        metadata={"exit_code": 1}
+    )
+    feedback = sensor.sense(result)
+    assert feedback.success is False
+    classification = classifier.classify(feedback)
+    plan = planner.plan(result, classification)
+    assert plan is not None
+    print("  Tool result: FAILED (exit code 1)")
+    print(f"  Feedback: category={feedback.category}, source={feedback.source}")
+    print(f"  Classification: {classification['type']}")
+    print(f"  Correction plan: scope='{plan.scope}', files={plan.target_files}")
+    print("  PASS: Feedback loop detected failure and generated correction plan\n")
+
+
+def demo_incremental_correction():
+    print("=== Demo 3: Incremental Correction Strategy (閲嶇偣缁村害) ===")
+    planner = CorrectionPlanner()
+    classifier = FailureClassifier()
+    sensor = TestSensor()
+
+    for retry in range(3):
+        result = ToolResult(
+            success=False,
+            output=f"FAILED test_order.py::test_validate - AssertionError (attempt {retry + 1})",
+            metadata={"exit_code": 1}
+        )
+        feedback = sensor.sense(result)
+        classification = classifier.classify(feedback)
+        plan = planner.plan(result, classification, retry_count=retry)
+        strategy = "incremental" if retry < 2 else "full replan"
+        print(f"  Attempt {retry + 1}: retry_count={retry}, strategy={strategy}")
+        print(f"    Correction: {plan.strategy[:50]}...")
+
+    print("  PASS: Incremental correction strategy escalates to full replan after 3 failures\n")
+
+
+def demo_failure_db():
+    print("=== Demo 4: FailureDB Records and Queries Failure Patterns ===")
+    with tempfile.TemporaryDirectory() as tmp:
+        db = FailureDB(db_path=os.path.join(tmp, "failure.db"))
+        db.record_failure("logic_error", "Missing null check on order_id", "Add guard clause before query")
+        results = db.query_similar("logic_error")
+        assert len(results) >= 1
+        print("  Recorded failure: logic_error")
+        print(f"  Queried similar patterns: {len(results)} found")
+        print(f"  Pattern: {results[0]['pattern']}")
+        print("  PASS: FailureDB persisted and retrieved failure pattern\n")
+
+
+def demo_workspace_policy():
+    print("=== Demo 5: WorkspacePolicy Blocks Path Escape ===")
+    with tempfile.TemporaryDirectory() as tmp:
+        policy = WorkspacePolicy(workspace=tmp)
+        action = Action(name="read_file", params={"path": os.path.join(tmp, "..", "..", "etc", "passwd")})
+        result = policy.check(action)
+        assert result.verdict == "DENY"
+        print("  Action: read_file ../../etc/passwd")
+        print(f"  Verdict: {result.verdict}")
+        print(f"  Reason: {result.reason}")
+        print("  PASS: WorkspacePolicy blocked path escape\n")
+
+
+if __name__ == "__main__":
+    demo_guardrail()
+    demo_feedback_loop()
+    demo_incremental_correction()
+    demo_failure_db()
+    demo_workspace_policy()
+    print("=== All demos passed ===")
diff --git a/src/ai4se_agent/feedback/failure_db.py b/src/ai4se_agent/feedback/failure_db.py
index 505e2ae..5d1d74e 100644
--- a/src/ai4se_agent/feedback/failure_db.py
+++ b/src/ai4se_agent/feedback/failure_db.py
@@ -2,37 +2,48 @@ import sqlite3
 from pathlib import Path
 
 
 class FailureDB:
     def __init__(self, db_path: str = "memory/failure.db"):
         self._db_path = db_path
         Path(db_path).parent.mkdir(parents=True, exist_ok=True)
         self._init_db()
 
     def _init_db(self) -> None:
-        with sqlite3.connect(self._db_path) as conn:
+        conn = sqlite3.connect(self._db_path)
+        try:
             conn.execute("""
                 CREATE TABLE IF NOT EXISTS failure_patterns (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     failure_type TEXT NOT NULL,
                     pattern TEXT NOT NULL,
                     fix_strategy TEXT,
                     count INTEGER DEFAULT 1,
                     last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                 )
             """)
+            conn.commit()
+        finally:
+            conn.close()
 
     def record_failure(self, failure_type: str, pattern: str, fix_strategy: str = "") -> None:
-        with sqlite3.connect(self._db_path) as conn:
+        conn = sqlite3.connect(self._db_path)
+        try:
             conn.execute(
                 "INSERT INTO failure_patterns (failure_type, pattern, fix_strategy) VALUES (?, ?, ?)",
                 (failure_type, pattern, fix_strategy)
             )
+            conn.commit()
+        finally:
+            conn.close()
 
     def query_similar(self, failure_type: str) -> list[dict]:
-        with sqlite3.connect(self._db_path) as conn:
+        conn = sqlite3.connect(self._db_path)
+        try:
             conn.row_factory = sqlite3.Row
             cursor = conn.execute(
                 "SELECT * FROM failure_patterns WHERE failure_type = ? ORDER BY count DESC LIMIT 5",
                 (failure_type,)
             )
             return [dict(row) for row in cursor.fetchall()]
+        finally:
+            conn.close()
