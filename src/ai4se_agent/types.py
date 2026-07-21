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
    params: dict


@dataclass
class ToolResult:
    success: bool
    output: str
    error: Optional[str] = None
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
