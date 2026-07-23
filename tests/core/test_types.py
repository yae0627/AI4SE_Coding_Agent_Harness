# tests/core/test_types.py
from ai4se_agent.types import Action, ToolResult, Feedback, GuardrailResult, CorrectionPlan, StopReason

def test_action_creation():
    action = Action(name="read_file", parameters={"path": "test.txt"})
    assert action.name == "read_file"
    assert action.parameters == {"path": "test.txt"}

def test_tool_result_defaults():
    result = ToolResult(success=True, output="file content", error=None)
    assert result.success is True
    assert result.metadata == {}

def test_feedback_with_source():
    fb = Feedback(success=False, category="test_failure", message="AssertionError",
                  details={"line": 42}, severity=3, source="pytest")
    assert fb.source == "pytest"
    assert fb.severity == 3

def test_guardrail_result_verdict():
    gr = GuardrailResult(verdict="DENY", reason="dangerous command", policy="CommandPolicy",
                         severity=5, metadata={"command": "rm -rf /"})
    assert gr.verdict == "DENY"

def test_correction_plan():
    plan = CorrectionPlan(scope="validate()", target_files=["order.py"], strategy="Add null check", retry_count=0)
    assert plan.retry_count == 0

def test_stop_reason_values():
    assert StopReason.SUCCESS.value == "success"
    assert StopReason.MAX_ITERATION.value == "max_iteration"
