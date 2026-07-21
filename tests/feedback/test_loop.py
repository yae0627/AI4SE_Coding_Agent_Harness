from ai4se_agent.feedback.loop import FeedbackLoop
from ai4se_agent.feedback.sensor import TestSensor
from ai4se_agent.feedback.classifier import FailureClassifier
from ai4se_agent.feedback.planner import CorrectionPlanner
from ai4se_agent.types import ToolResult

def test_feedback_loop_produces_correction():
    loop = FeedbackLoop(
        sensors=[TestSensor()],
        classifier=FailureClassifier(),
        planner=CorrectionPlanner()
    )
    result = ToolResult(success=False, output="FAILED - AssertionError", metadata={"exit_code": 1})
    plan = loop.run(result)
    assert plan is not None
    assert plan.retry_count == 0
