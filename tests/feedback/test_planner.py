from ai4se_agent.feedback.planner import CorrectionPlanner
from ai4se_agent.types import ToolResult

def test_planner_generates_plan():
    planner = CorrectionPlanner()
    result = ToolResult(success=False, output="FAILED test_order.py::test_validate - AssertionError",
                        metadata={"exit_code": 1})
    plan = planner.plan(result, {"type": "logic_error", "category": "test_failure"})
    assert plan.scope is not None
    assert len(plan.target_files) > 0
    assert plan.retry_count == 0
