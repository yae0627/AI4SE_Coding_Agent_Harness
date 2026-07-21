from ai4se_agent.types import ToolResult, CorrectionPlan


class CorrectionPlanner:
    def plan(self, result: ToolResult, classification: dict, retry_count: int = 0) -> CorrectionPlan:
        if classification["type"] == "logic_error":
            return CorrectionPlan(
                scope="Fix assertion failure in test output",
                target_files=self._extract_files(result.output),
                strategy="Analyze the test failure and fix the logic in the relevant code",
                retry_count=retry_count
            )
        elif classification["type"] == "syntax_error":
            return CorrectionPlan(
                scope="Fix lint/type errors",
                target_files=self._extract_files(result.output),
                strategy="Fix the reported syntax or type issues",
                retry_count=retry_count
            )
        else:
            return CorrectionPlan(
                scope="General fix",
                target_files=self._extract_files(result.output),
                strategy="Review the error and fix the issue",
                retry_count=retry_count
            )

    def _extract_files(self, output: str) -> list:
        import re
        files = re.findall(r'(\S+\.py):', output)
        return list(set(files)) if files else ["unknown"]
