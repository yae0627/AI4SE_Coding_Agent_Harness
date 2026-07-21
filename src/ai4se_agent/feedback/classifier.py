from ai4se_agent.types import Feedback


class FailureClassifier:
    def classify(self, feedback: Feedback) -> dict:
        if feedback.category == "lint_error":
            return {"type": "syntax_error", "category": feedback.category, "message": feedback.message}
        if feedback.category == "type_error":
            return {"type": "type_error", "category": feedback.category, "message": feedback.message}
        if "AssertionError" in feedback.message:
            return {"type": "logic_error", "category": feedback.category, "message": feedback.message}
        if "ImportError" in feedback.message or "ModuleNotFoundError" in feedback.message:
            return {"type": "missing_dependency", "category": feedback.category, "message": feedback.message}
        if "timeout" in feedback.message.lower():
            return {"type": "timeout", "category": feedback.category, "message": feedback.message}
        return {"type": "unknown", "category": feedback.category, "message": feedback.message}
