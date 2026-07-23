# src/ai4se_agent/observability/events.py
from dataclasses import dataclass, field
from enum import Enum


class EventType(Enum):
    STATE_CHANGED = "state_changed"
    LLM_CALLED = "llm_called"
    ACTION_PARSED = "action_parsed"
    GUARDRAIL_CHECKED = "guardrail_checked"
    TOOL_EXECUTED = "tool_executed"
    FEEDBACK_RECEIVED = "feedback_received"


@dataclass
class Event:
    type: EventType
    iteration: int
    timestamp: str = ""
    elapsed_ms: float = 0.0
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "iteration": self.iteration,
            "timestamp": self.timestamp,
            "elapsed_ms": self.elapsed_ms,
            **self.data,
        }


@dataclass
class StateEvent(Event):
    old_state: str = ""
    new_state: str = ""

    def __init__(self, iteration: int, old_state: str, new_state: str):
        super().__init__(type=EventType.STATE_CHANGED, iteration=iteration,
                         data={"old_state": old_state, "new_state": new_state})
        self.old_state = old_state
        self.new_state = new_state


@dataclass
class LLMEvent(Event):
    model: str = ""
    messages: list = field(default_factory=list)
    response: str = ""

    def __init__(self, iteration: int, model: str, messages: list, response: str):
        super().__init__(type=EventType.LLM_CALLED, iteration=iteration,
                         data={"model": model, "response": response})
        self.model = model
        self.messages = messages
        self.response = response


@dataclass
class ActionEvent(Event):
    action_name: str = ""
    action_params: dict = field(default_factory=dict)

    def __init__(self, iteration: int, action_name: str, action_params: dict):
        super().__init__(type=EventType.ACTION_PARSED, iteration=iteration,
                         data={"action_name": action_name, "action_params": action_params})
        self.action_name = action_name
        self.action_params = action_params


@dataclass
class ToolEvent(Event):
    tool: str = ""
    success: bool = True
    output: str = ""

    def __init__(self, iteration: int, tool: str, success: bool, output: str = ""):
        super().__init__(type=EventType.TOOL_EXECUTED, iteration=iteration,
                         data={"tool": tool, "success": success, "output": output[:200]})
        self.tool = tool
        self.success = success
        self.output = output


@dataclass
class FeedbackEvent(Event):
    plan_scope: str = ""
    has_plan: bool = False

    def __init__(self, iteration: int, plan_scope: str = "", has_plan: bool = False):
        super().__init__(type=EventType.FEEDBACK_RECEIVED, iteration=iteration,
                         data={"plan_scope": plan_scope, "has_plan": has_plan})
        self.plan_scope = plan_scope
        self.has_plan = has_plan


@dataclass
class GuardrailEvent(Event):
    verdict: str = ""
    policy: str = ""
    reason: str = ""

    def __init__(self, iteration: int, verdict: str, policy: str, reason: str):
        super().__init__(type=EventType.GUARDRAIL_CHECKED, iteration=iteration,
                         data={"verdict": verdict, "policy": policy, "reason": reason})
        self.verdict = verdict
        self.policy = policy
        self.reason = reason
