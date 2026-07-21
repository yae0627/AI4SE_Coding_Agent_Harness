from ai4se_agent.feedback.classifier import FailureClassifier
from ai4se_agent.types import Feedback

def test_classify_assertion_error():
    classifier = FailureClassifier()
    fb = Feedback(success=False, category="test_failure", message="AssertionError: expected 5 got 3",
                  details={"line": 42}, severity=3, source="pytest")
    result = classifier.classify(fb)
    assert result["type"] == "logic_error"

def test_classify_lint_error():
    classifier = FailureClassifier()
    fb = Feedback(success=False, category="lint_error", message="F401 imported but unused",
                  details={}, severity=2, source="ruff")
    result = classifier.classify(fb)
    assert result["type"] == "syntax_error"
