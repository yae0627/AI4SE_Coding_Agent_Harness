# src/ai4se_agent/types.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional


class StopReason(Enum):
    SUCCESS = "success"
    MAX_ITERATION = "max_iteration"
    REPEATED_FAILURE = "repeated_failure"
    LLM_ERROR = "llm_error"
    USER_CANCEL = "user_cancel"
    APPROVAL_TIMEOUT = "approval_timeout"


@dataclass
class Action:
    name: str
    parameters: dict


@dataclass
class ParseResult:
    success: bool
    action: Optional["Action"] = None
    message: str | None = None
    error: str | None = None


@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Feedback:
    success: bool
    category: str
    message: str
    details: dict = field(default_factory=dict)
    severity: int = 0
    source: str = ""


@dataclass
class GuardrailResult:
    verdict: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"]
    reason: str
    policy: str
    severity: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class CorrectionPlan:
    scope: str
    target_files: list
    strategy: str
    retry_count: int = 0


@dataclass
class PlanStep:
    description: str
    status: str = "pending"  # pending | in_progress | done | failed

    def is_active(self) -> bool:
        return self.status in ("pending", "in_progress")

    def is_done(self) -> bool:
        return self.status == "done"


@dataclass
class Plan:
    steps: list  # list[PlanStep]

    @staticmethod
    def from_strings(descriptions: list[str]) -> "Plan":
        return Plan(steps=[PlanStep(description=d) for d in descriptions])

    def current_step(self) -> PlanStep | None:
        for s in self.steps:
            if s.status == "in_progress":
                return s
        for s in self.steps:
            if s.status == "pending":
                return s
        return None

    def completed(self) -> bool:
        return all(s.status == "done" for s in self.steps)

    def pending_count(self) -> int:
        return sum(1 for s in self.steps if s.status == "pending")

    def done_count(self) -> int:
        return sum(1 for s in self.steps if s.status == "done")
