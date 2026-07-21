from ai4se_agent.feedback.sensor import Sensor
from ai4se_agent.feedback.classifier import FailureClassifier
from ai4se_agent.feedback.planner import CorrectionPlanner
from ai4se_agent.types import ToolResult, CorrectionPlan


class FeedbackLoop:
    def __init__(self, sensors: list[Sensor], classifier: FailureClassifier, planner: CorrectionPlanner):
        self._sensors = sensors
        self._classifier = classifier
        self._planner = planner

    def run(self, result: ToolResult, retry_count: int = 0) -> CorrectionPlan | None:
        if result.success:
            return None
        for sensor in self._sensors:
            feedback = sensor.sense(result)
            if feedback and not feedback.success:
                classification = self._classifier.classify(feedback)
                plan = self._planner.plan(result, classification, retry_count)
                return plan
        return None
