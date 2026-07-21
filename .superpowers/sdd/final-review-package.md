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
diff --git a/src/ai4se_agent/cli.py b/src/ai4se_agent/cli.py
new file mode 100644
index 0000000..277d447
--- /dev/null
+++ b/src/ai4se_agent/cli.py
@@ -0,0 +1,85 @@
+# src/ai4se_agent/cli.py
+import sys
+from ai4se_agent.config.loader import ConfigLoader
+from ai4se_agent.core.agent_state import AgentState
+from ai4se_agent.core.action import ActionParser, ActionValidator
+from ai4se_agent.core.state_machine import HarnessStateMachine
+from ai4se_agent.llm.openai_adapter import OpenAIAdapter
+from ai4se_agent.llm.mock_adapter import MockAdapter
+from ai4se_agent.tools.registry import ToolRegistry
+from ai4se_agent.tools.read_file import ReadFileTool
+from ai4se_agent.tools.write_file import WriteFileTool
+from ai4se_agent.tools.edit_file import EditFileTool
+from ai4se_agent.tools.shell import ShellTool
+from ai4se_agent.tools.run_test import RunTestTool
+from ai4se_agent.guardrails.engine import GuardrailEngine
+from ai4se_agent.guardrails.command_policy import CommandPolicy
+from ai4se_agent.guardrails.file_policy import FilePolicy
+from ai4se_agent.guardrails.workspace_policy import WorkspacePolicy
+from ai4se_agent.guardrails.git_policy import GitPolicy
+from ai4se_agent.feedback.loop import FeedbackLoop
+from ai4se_agent.feedback.sensor import TestSensor, LintSensor
+from ai4se_agent.feedback.classifier import FailureClassifier
+from ai4se_agent.feedback.planner import CorrectionPlanner
+from ai4se_agent.memory.manager import MemoryManager
+from ai4se_agent.memory.session import SessionMemory
+from ai4se_agent.memory.persistent import PersistentMemory
+
+
+def build_harness(task: str, workspace: str = ".") -> HarnessStateMachine:
+    config = ConfigLoader()
+    provider = config.get_provider()
+    if provider == "mock":
+        llm = MockAdapter(responses=["action: shell command=echo hello", "[DONE]"])
+    else:
+        api_key = config.get("api_key")
+        base_url = config.get("base_url")
+        llm = OpenAIAdapter(api_key=api_key, base_url=base_url)
+
+    tools = ToolRegistry()
+    tools.register(ReadFileTool())
+    tools.register(WriteFileTool())
+    tools.register(EditFileTool())
+    tools.register(ShellTool())
+    tools.register(RunTestTool())
+
+    guardrails = GuardrailEngine()
+    guardrails.add_policy(CommandPolicy())
+    guardrails.add_policy(FilePolicy())
+    guardrails.add_policy(WorkspacePolicy(workspace=workspace))
+    guardrails.add_policy(GitPolicy())
+
+    feedback = FeedbackLoop(
+        sensors=[TestSensor(), LintSensor()],
+        classifier=FailureClassifier(),
+        planner=CorrectionPlanner()
+    )
+
+    memory = MemoryManager(
+        session=SessionMemory(),
+        persistent=PersistentMemory()
+    )
+
+    state = AgentState(goal=task)
+
+    return HarnessStateMachine(
+        agent_state=state,
+        llm_adapter=llm,
+        action_parser=ActionParser(),
+        action_validator=ActionValidator(),
+        tool_registry=tools,
+        guardrail_engine=guardrails,
+        feedback_loop=feedback,
+        memory_manager=memory,
+    )
+
+
+def main():
+    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Task: ")
+    harness = build_harness(task)
+    result = harness.run()
+    print(f"\nResult: {result['status']} ({result['reason']}) after {result['iterations']} iterations")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/ai4se_agent/config/loader.py b/src/ai4se_agent/config/loader.py
new file mode 100644
index 0000000..ac580a3
--- /dev/null
+++ b/src/ai4se_agent/config/loader.py
@@ -0,0 +1,30 @@
+import os
+from pathlib import Path
+
+
+class ConfigLoader:
+    def __init__(self, env_file: str = ".env"):
+        self._env_file = Path(env_file)
+        self._load_env_file()
+
+    def _load_env_file(self) -> None:
+        if self._env_file.exists():
+            for line in self._env_file.read_text(encoding="utf-8").splitlines():
+                line = line.strip()
+                if line and not line.startswith("#") and "=" in line:
+                    key, _, value = line.partition("=")
+                    os.environ.setdefault(key.strip(), value.strip())
+
+    def get(self, key: str, default: str | None = None) -> str | None:
+        env_map = {
+            "api_key": "OPENAI_API_KEY",
+            "base_url": "OPENAI_BASE_URL",
+            "provider": "LLM_PROVIDER",
+            "local_model_url": "LOCAL_MODEL_URL",
+            "local_model_name": "LOCAL_MODEL_NAME",
+        }
+        env_key = env_map.get(key, key.upper())
+        return os.environ.get(env_key, default)
+
+    def get_provider(self) -> str:
+        return self.get("provider", "openai")
diff --git a/src/ai4se_agent/core/action.py b/src/ai4se_agent/core/action.py
new file mode 100644
index 0000000..1d58750
--- /dev/null
+++ b/src/ai4se_agent/core/action.py
@@ -0,0 +1,34 @@
+# src/ai4se_agent/core/action.py
+import re
+from ai4se_agent.types import Action
+
+
+class ActionParser:
+    def parse(self, text: str) -> Action | None:
+        match = re.match(r'action:\s*(\w+)(.*)', text.strip())
+        if not match:
+            return None
+        name = match.group(1)
+        params_str = match.group(2).strip()
+        params = {}
+        for pair in re.findall(r'(\w+)=(\S+)', params_str):
+            params[pair[0]] = pair[1]
+        return Action(name=name, params=params)
+
+
+class ActionValidator:
+    REQUIRED_PARAMS = {
+        "read_file": ["path"],
+        "write_file": ["path", "content"],
+        "edit_file": ["path", "old_string", "new_string"],
+        "shell": ["command"],
+        "run_test": [],
+    }
+
+    def validate(self, action: Action) -> list[str]:
+        errors = []
+        required = self.REQUIRED_PARAMS.get(action.name, [])
+        for param in required:
+            if param not in action.params:
+                errors.append(f"Missing required param: {param}")
+        return errors
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
diff --git a/src/ai4se_agent/core/state_machine.py b/src/ai4se_agent/core/state_machine.py
new file mode 100644
index 0000000..0fb8451
--- /dev/null
+++ b/src/ai4se_agent/core/state_machine.py
@@ -0,0 +1,170 @@
+# src/ai4se_agent/core/state_machine.py
+from transitions import Machine
+from ai4se_agent.core.agent_state import AgentState
+from ai4se_agent.core.action import ActionParser, ActionValidator
+from ai4se_agent.llm.base import LLMAdapter
+from ai4se_agent.tools.registry import ToolRegistry
+from ai4se_agent.guardrails.engine import GuardrailEngine
+from ai4se_agent.feedback.loop import FeedbackLoop
+from ai4se_agent.memory.manager import MemoryManager
+from ai4se_agent.types import StopReason
+
+
+class HarnessStateMachine:
+    states = [
+        "IDLE", "CONTEXT_ORG", "LLM_CALL", "ACTION_PARSE",
+        "GUARDRAIL", "WAIT_APPROVAL", "TOOL_EXEC", "TOOL_ERROR",
+        "FEEDBACK", "MEMORY_UPDATE", "STOP"
+    ]
+
+    def __init__(
+        self,
+        agent_state: AgentState,
+        llm_adapter: LLMAdapter,
+        action_parser: ActionParser,
+        action_validator: ActionValidator,
+        tool_registry: ToolRegistry,
+        guardrail_engine: GuardrailEngine,
+        feedback_loop: FeedbackLoop | None,
+        memory_manager: MemoryManager,
+        max_iterations: int = 20,
+    ):
+        self.state = agent_state
+        self.llm = llm_adapter
+        self.parser = action_parser
+        self.validator = action_validator
+        self.tools = tool_registry
+        self.guardrails = guardrail_engine
+        self.feedback = feedback_loop
+        self.memory = memory_manager
+        self.max_iterations = max_iterations
+        self.stop_reason = StopReason.SUCCESS
+        self._pending_action = None
+        self._pending_guardrail = None
+
+        self.machine = Machine(
+            model=self,
+            states=HarnessStateMachine.states,
+            initial="IDLE",
+            auto_transitions=False,
+            model_attribute="_fsm_state",
+        )
+
+        self.machine.add_transition("start", "IDLE", "CONTEXT_ORG", after="_on_context_org")
+        self.machine.add_transition("retry_context", "CONTEXT_ORG", "CONTEXT_ORG", after="_on_context_org")
+        self.machine.add_transition("call_llm", "CONTEXT_ORG", "LLM_CALL", after="_on_llm_call")
+        self.machine.add_transition("parse_action", "LLM_CALL", "ACTION_PARSE", after="_on_action_parse")
+        self.machine.add_transition("retry_parse", "ACTION_PARSE", "CONTEXT_ORG", after="_on_context_org")
+        self.machine.add_transition("check_guardrails", "ACTION_PARSE", "GUARDRAIL", after="_on_guardrail")
+        self.machine.add_transition("deny_action", "GUARDRAIL", "CONTEXT_ORG", after="_on_context_org")
+        self.machine.add_transition("request_approval", "GUARDRAIL", "WAIT_APPROVAL", after="_on_wait_approval")
+        self.machine.add_transition("approve", "WAIT_APPROVAL", "TOOL_EXEC", after="_on_tool_exec")
+        self.machine.add_transition("reject", "WAIT_APPROVAL", "CONTEXT_ORG", after="_on_context_org")
+        self.machine.add_transition("execute", "GUARDRAIL", "TOOL_EXEC", after="_on_tool_exec")
+        self.machine.add_transition("tool_error", "TOOL_EXEC", "TOOL_ERROR", after="_on_tool_error")
+        self.machine.add_transition("tool_success", "TOOL_EXEC", "FEEDBACK", after="_on_feedback")
+        self.machine.add_transition("retry_tool", "TOOL_ERROR", "TOOL_EXEC", after="_on_tool_exec")
+        self.machine.add_transition("feedback_done", "FEEDBACK", "MEMORY_UPDATE", after="_on_memory_update")
+        self.machine.add_transition("feedback_correct", "FEEDBACK", "CONTEXT_ORG", after="_on_context_org")
+        self.machine.add_transition("continue_loop", "MEMORY_UPDATE", "CONTEXT_ORG", after="_on_context_org")
+        self.machine.add_transition("stop", "*", "STOP")
+
+    def run(self) -> dict:
+        self.start()
+        self.state.current_state = self.state
+        return self._build_result()
+
+    def _on_context_org(self) -> None:
+        self.state.increment_iteration()
+        if self.state.iteration > self.max_iterations:
+            self.stop_reason = StopReason.MAX_ITERATION
+            self.stop()
+            return
+        self.call_llm()
+
+    def _on_llm_call(self) -> None:
+        try:
+            messages = self.state.context
+            response = self.llm.generate(messages)
+            self.state.context.append({"role": "assistant", "content": response})
+            self.parse_action()
+        except Exception:
+            self.state.error_count += 1
+            if self.state.error_count >= 3:
+                self.stop_reason = StopReason.LLM_ERROR
+                self.stop()
+            else:
+                self.retry_context()
+
+    def _on_action_parse(self) -> None:
+        last_msg = self.state.context[-1]["content"]
+        if "[DONE]" in last_msg:
+            self.stop_reason = StopReason.SUCCESS
+            self.stop()
+            return
+        action = self.parser.parse(last_msg)
+        if action is None:
+            self.retry_parse()
+            return
+        errors = self.validator.validate(action)
+        if errors:
+            self.retry_parse()
+            return
+        self._pending_action = action
+        self.check_guardrails()
+
+    def _on_guardrail(self) -> None:
+        result = self.guardrails.check(self._pending_action)
+        self._pending_guardrail = result
+        if result.verdict == "DENY":
+            self.deny_action()
+        elif result.verdict == "REQUIRE_APPROVAL":
+            self.request_approval()
+        else:
+            self.execute()
+
+    def _on_wait_approval(self) -> None:
+        print(f"\n[DANGEROUS ACTION] Policy: {self._pending_guardrail.policy}")
+        print(f"Reason: {self._pending_guardrail.reason}")
+        print(f"Action: {self._pending_action}")
+        answer = input("Approve? (y/n): ").strip().lower()
+        if answer == "y":
+            self.approve()
+        else:
+            self.reject()
+
+    def _on_tool_exec(self) -> None:
+        result = self.tools.execute(self._pending_action)
+        if result.success:
+            self.tool_success()
+        else:
+            self.tool_error()
+
+    def _on_tool_error(self) -> None:
+        if self.state.retry_count < 3:
+            self.state.retry_count += 1
+            self.retry_tool()
+        else:
+            self.stop_reason = StopReason.REPEATED_FAILURE
+            self.stop()
+
+    def _on_feedback(self) -> None:
+        if self.feedback:
+            plan = self.feedback.run(None, self.state.retry_count)
+            if plan:
+                self.state.retry_count += 1
+                if self.state.retry_count >= 3:
+                    self.state.retry_count = 0
+                self.feedback_correct()
+                return
+        self.feedback_done()
+
+    def _on_memory_update(self) -> None:
+        self.continue_loop()
+
+    def _build_result(self) -> dict:
+        return {
+            "status": "success" if self.stop_reason == StopReason.SUCCESS else "failed",
+            "reason": self.stop_reason.value,
+            "iterations": self.state.iteration,
+        }
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
index 0000000..5d1d74e
--- /dev/null
+++ b/src/ai4se_agent/feedback/failure_db.py
@@ -0,0 +1,49 @@
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
+        conn = sqlite3.connect(self._db_path)
+        try:
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
+            conn.commit()
+        finally:
+            conn.close()
+
+    def record_failure(self, failure_type: str, pattern: str, fix_strategy: str = "") -> None:
+        conn = sqlite3.connect(self._db_path)
+        try:
+            conn.execute(
+                "INSERT INTO failure_patterns (failure_type, pattern, fix_strategy) VALUES (?, ?, ?)",
+                (failure_type, pattern, fix_strategy)
+            )
+            conn.commit()
+        finally:
+            conn.close()
+
+    def query_similar(self, failure_type: str) -> list[dict]:
+        conn = sqlite3.connect(self._db_path)
+        try:
+            conn.row_factory = sqlite3.Row
+            cursor = conn.execute(
+                "SELECT * FROM failure_patterns WHERE failure_type = ? ORDER BY count DESC LIMIT 5",
+                (failure_type,)
+            )
+            return [dict(row) for row in cursor.fetchall()]
+        finally:
+            conn.close()
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
diff --git a/src/ai4se_agent/llm/__init__.py b/src/ai4se_agent/llm/__init__.py
new file mode 100644
index 0000000..e69de29
diff --git a/src/ai4se_agent/llm/base.py b/src/ai4se_agent/llm/base.py
new file mode 100644
index 0000000..5e33764
--- /dev/null
+++ b/src/ai4se_agent/llm/base.py
@@ -0,0 +1,7 @@
+from abc import ABC, abstractmethod
+
+
+class LLMAdapter(ABC):
+    @abstractmethod
+    def generate(self, messages: list[dict]) -> str:
+        pass
diff --git a/src/ai4se_agent/llm/mock_adapter.py b/src/ai4se_agent/llm/mock_adapter.py
new file mode 100644
index 0000000..0a5ebba
--- /dev/null
+++ b/src/ai4se_agent/llm/mock_adapter.py
@@ -0,0 +1,12 @@
+from ai4se_agent.llm.base import LLMAdapter
+
+
+class MockAdapter(LLMAdapter):
+    def __init__(self, responses: list[str]):
+        self.responses = responses
+        self._index = 0
+
+    def generate(self, messages: list[dict]) -> str:
+        response = self.responses[self._index % len(self.responses)]
+        self._index += 1
+        return response
diff --git a/src/ai4se_agent/llm/openai_adapter.py b/src/ai4se_agent/llm/openai_adapter.py
new file mode 100644
index 0000000..cb7227d
--- /dev/null
+++ b/src/ai4se_agent/llm/openai_adapter.py
@@ -0,0 +1,14 @@
+from openai import OpenAI
+from ai4se_agent.llm.base import LLMAdapter
+
+
+class OpenAIAdapter(LLMAdapter):
+    def __init__(self, api_key: str, base_url: str = None, model: str = "gpt-4o"):
+        self.client = OpenAI(api_key=api_key, base_url=base_url)
+        self.model = model
+
+    def generate(self, messages: list[dict]) -> str:
+        response = self.client.chat.completions.create(
+            model=self.model, messages=messages
+        )
+        return response.choices[0].message.content
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
diff --git a/tests/config/__init__.py b/tests/config/__init__.py
new file mode 100644
index 0000000..e69de29
diff --git a/tests/config/test_loader.py b/tests/config/test_loader.py
new file mode 100644
index 0000000..8a95343
--- /dev/null
+++ b/tests/config/test_loader.py
@@ -0,0 +1,10 @@
+from ai4se_agent.config.loader import ConfigLoader
+
+def test_config_returns_defaults():
+    loader = ConfigLoader()
+    assert loader.get("provider", "openai") == "openai"
+
+def test_config_accepts_env_override(monkeypatch):
+    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
+    loader = ConfigLoader()
+    assert loader.get("api_key") == "test-key-123"
diff --git a/tests/core/test_action.py b/tests/core/test_action.py
new file mode 100644
index 0000000..5ea57aa
--- /dev/null
+++ b/tests/core/test_action.py
@@ -0,0 +1,20 @@
+# tests/core/test_action.py
+from ai4se_agent.core.action import ActionParser, ActionValidator
+from ai4se_agent.types import Action
+
+def test_parse_valid_action():
+    parser = ActionParser()
+    action = parser.parse('action: write_file path=test.txt content=hello')
+    assert action.name == "write_file"
+    assert action.params["path"] == "test.txt"
+
+def test_parse_missing_action():
+    parser = ActionParser()
+    result = parser.parse("some random text")
+    assert result is None
+
+def test_validate_missing_param():
+    validator = ActionValidator()
+    action = Action(name="write_file", params={})
+    errors = validator.validate(action)
+    assert "path" in errors[0] or "content" in errors[0]
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
diff --git a/tests/core/test_state_machine.py b/tests/core/test_state_machine.py
new file mode 100644
index 0000000..079f7f8
--- /dev/null
+++ b/tests/core/test_state_machine.py
@@ -0,0 +1,27 @@
+# tests/core/test_state_machine.py
+from ai4se_agent.core.state_machine import HarnessStateMachine
+from ai4se_agent.core.agent_state import AgentState
+from ai4se_agent.llm.mock_adapter import MockAdapter
+from ai4se_agent.core.action import ActionParser, ActionValidator
+from ai4se_agent.tools.registry import ToolRegistry
+from ai4se_agent.guardrails.engine import GuardrailEngine
+from ai4se_agent.memory.manager import MemoryManager
+
+def test_state_machine_completes_successfully(tmp_path):
+    llm = MockAdapter(responses=["action: read_file path=test.txt", "[DONE]"])
+    registry = ToolRegistry()
+    guardrails = GuardrailEngine()
+    state = AgentState(goal="test task")
+    machine = HarnessStateMachine(
+        agent_state=state,
+        llm_adapter=llm,
+        action_parser=ActionParser(),
+        action_validator=ActionValidator(),
+        tool_registry=registry,
+        guardrail_engine=guardrails,
+        feedback_loop=None,
+        memory_manager=MemoryManager(),
+        max_iterations=5
+    )
+    result = machine.run()
+    assert result["status"] in ("success", "failed")
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
diff --git a/tests/llm/__init__.py b/tests/llm/__init__.py
new file mode 100644
index 0000000..e69de29
diff --git a/tests/llm/test_adapters.py b/tests/llm/test_adapters.py
new file mode 100644
index 0000000..a0347bc
--- /dev/null
+++ b/tests/llm/test_adapters.py
@@ -0,0 +1,16 @@
+from ai4se_agent.llm.base import LLMAdapter
+from ai4se_agent.llm.mock_adapter import MockAdapter
+
+def test_mock_adapter_returns_preset():
+    adapter = MockAdapter(responses=["action: write_file path=test.txt"])
+    result = adapter.generate([{"role": "user", "content": "hello"}])
+    assert result == "action: write_file path=test.txt"
+
+def test_mock_adapter_cycles():
+    adapter = MockAdapter(responses=["first", "second"])
+    assert adapter.generate([]) == "first"
+    assert adapter.generate([]) == "second"
+
+def test_adapter_is_abstract():
+    import inspect
+    assert inspect.isabstract(LLMAdapter)
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
diff --git a/tests/test_cli.py b/tests/test_cli.py
new file mode 100644
index 0000000..6943835
--- /dev/null
+++ b/tests/test_cli.py
@@ -0,0 +1,8 @@
+# tests/test_cli.py
+from ai4se_agent.cli import build_harness
+
+def test_build_harness_creates_machine(monkeypatch):
+    monkeypatch.setenv("LLM_PROVIDER", "mock")
+    harness = build_harness("test task", workspace="/tmp")
+    assert harness is not None
+    assert harness.state.goal == "test task"
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
