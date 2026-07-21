from abc import ABC, abstractmethod
from ai4se_agent.types import ToolResult, Feedback


class Sensor(ABC):
    @abstractmethod
    def sense(self, result: ToolResult) -> Feedback | None:
        pass


class TestSensor(Sensor):
    def sense(self, result: ToolResult) -> Feedback | None:
        if result.metadata.get("exit_code") == 0:
            return Feedback(success=True, category="test_success", message="All tests passed",
                            source="pytest")
        return Feedback(
            success=False, category="test_failure", message=result.output,
            source="pytest", severity=3, details={"exit_code": result.metadata.get("exit_code", 1)}
        )


class LintSensor(Sensor):
    def sense(self, result: ToolResult) -> Feedback | None:
        if result.success:
            return Feedback(success=True, category="lint_success", message="Clean lint",
                            source="ruff")
        return Feedback(
            success=False, category="lint_error", message=result.output,
            source="ruff", severity=2
        )


class TypeSensor(Sensor):
    def sense(self, result: ToolResult) -> Feedback | None:
        if result.success:
            return Feedback(success=True, category="type_success", message="Clean types",
                            source="mypy")
        return Feedback(
            success=False, category="type_error", message=result.output,
            source="mypy", severity=2
        )
