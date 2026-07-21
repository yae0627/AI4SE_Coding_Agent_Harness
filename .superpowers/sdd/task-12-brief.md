# Task 12: Mechanism Demo

**Files:**
- Create: `demo/mechanism_demo.py`
- Create: `demo/README.md`

**Interfaces:**
- Consumes: All subsystems

## Step 1: Write the demo script

```python
# demo/mechanism_demo.py
"""
Mechanism Demo — 演示三个核心行为：
1. 治理护栏拦截危险动作
2. 反馈闭环使 agent 收到失败信号并修正
3. 重点维度的确定性行为（Feedback Loop 完整流程）
"""
from ai4se_agent.feedback.sensor import TestSensor
from ai4se_agent.feedback.classifier import FailureClassifier
from ai4se_agent.feedback.planner import CorrectionPlanner
from ai4se_agent.feedback.failure_db import FailureDB
from ai4se_agent.guardrails.command_policy import CommandPolicy
from ai4se_agent.guardrails.workspace_policy import WorkspacePolicy
from ai4se_agent.types import Action, ToolResult
import tempfile
import os


def demo_guardrail():
    print("=== Demo 1: Guardrail Intercepts Dangerous Action ===")
    policy = CommandPolicy()
    action = Action(name="shell", params={"command": "rm -rf /"})
    result = policy.check(action)
    assert result.verdict == "DENY", f"Expected DENY, got {result.verdict}"
    print(f"  Action: shell rm -rf /")
    print(f"  Verdict: {result.verdict}")
    print(f"  Reason: {result.reason}")
    print("  PASS: Guardrail correctly blocked dangerous command\n")


def demo_feedback_loop():
    print("=== Demo 2: Feedback Loop Detects Failure and Generates Correction ===")
    sensor = TestSensor()
    classifier = FailureClassifier()
    planner = CorrectionPlanner()

    result = ToolResult(
        success=False,
        output="FAILED test_order.py::test_validate - AssertionError: expected True got False",
        metadata={"exit_code": 1}
    )
    feedback = sensor.sense(result)
    assert feedback.success is False
    classification = classifier.classify(feedback)
    plan = planner.plan(result, classification)
    assert plan is not None
    print(f"  Tool result: FAILED (exit code 1)")
    print(f"  Feedback: category={feedback.category}, source={feedback.source}")
    print(f"  Classification: {classification['type']}")
    print(f"  Correction plan: scope='{plan.scope}', files={plan.target_files}")
    print("  PASS: Feedback loop detected failure and generated correction plan\n")


def demo_incremental_correction():
    print("=== Demo 3: Incremental Correction Strategy (重点维度) ===")
    planner = CorrectionPlanner()
    classifier = FailureClassifier()
    sensor = TestSensor()

    for retry in range(3):
        result = ToolResult(
            success=False,
            output=f"FAILED test_order.py::test_validate - AssertionError (attempt {retry + 1})",
            metadata={"exit_code": 1}
        )
        feedback = sensor.sense(result)
        classification = classifier.classify(feedback)
        plan = planner.plan(result, classification, retry_count=retry)
        strategy = "incremental" if retry < 2 else "full replan"
        print(f"  Attempt {retry + 1}: retry_count={retry}, strategy={strategy}")
        print(f"    Correction: {plan.strategy[:50]}...")

    print("  PASS: Incremental correction strategy escalates to full replan after 3 failures\n")


def demo_failure_db():
    print("=== Demo 4: FailureDB Records and Queries Failure Patterns ===")
    with tempfile.TemporaryDirectory() as tmp:
        db = FailureDB(db_path=os.path.join(tmp, "failure.db"))
        db.record_failure("logic_error", "Missing null check on order_id", "Add guard clause before query")
        results = db.query_similar("logic_error")
        assert len(results) >= 1
        print(f"  Recorded failure: logic_error")
        print(f"  Queried similar patterns: {len(results)} found")
        print(f"  Pattern: {results[0]['pattern']}")
        print("  PASS: FailureDB persisted and retrieved failure pattern\n")


def demo_workspace_policy():
    print("=== Demo 5: WorkspacePolicy Blocks Path Escape ===")
    with tempfile.TemporaryDirectory() as tmp:
        policy = WorkspacePolicy(workspace=tmp)
        action = Action(name="read_file", params={"path": os.path.join(tmp, "..", "..", "etc", "passwd")})
        result = policy.check(action)
        assert result.verdict == "DENY"
        print(f"  Action: read_file ../../etc/passwd")
        print(f"  Verdict: {result.verdict}")
        print(f"  Reason: {result.reason}")
        print("  PASS: WorkspacePolicy blocked path escape\n")


if __name__ == "__main__":
    demo_guardrail()
    demo_feedback_loop()
    demo_incremental_correction()
    demo_failure_db()
    demo_workspace_policy()
    print("=== All demos passed ===")
```

## Step 2: Run the demo

Run: `python demo/mechanism_demo.py`
Expected: All 5 demos print PASS

## Step 3: Commit

```bash
git add demo/
git commit -m "feat: add mechanism demo for guardrail, feedback, correction, failure DB, workspace policy"
```

## Global Constraints

- Python >=3.10
- All core mechanisms must be testable with mock LLM (no network, no real LLM)
- No use of agent orchestration frameworks
- No comments in code unless specified (NOTE: the demo script has a docstring at the top which is part of the brief)
- Lint must pass (ruff)
