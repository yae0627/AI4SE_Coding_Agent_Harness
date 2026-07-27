from dataclasses import dataclass, field
from typing import Optional

from ai4se_agent.types import Action, Plan


@dataclass
class AgentState:
    goal: str
    current_state: str = "IDLE"
    iteration: int = 0
    step_iteration: int = 0
    history: list = field(default_factory=list)
    feedback: list = field(default_factory=list)
    last_action: Optional[Action] = None
    last_observation: Optional[str] = None
    error_count: int = 0
    retry_count: int = 0
    plan: Optional[Plan] = None

    def record_turn(self, action: Action, observation: str) -> None:
        self.history.append({"role": "assistant", "content": f"action: {action.name} {action.parameters}"})
        self.history.append({"role": "tool", "content": observation})
        self.last_action = action
        self.last_observation = observation

    def record_feedback(self, feedback_msg: str) -> None:
        self.feedback.append({"role": "user", "content": feedback_msg})

    def increment_iteration(self) -> None:
        self.iteration += 1
        self.step_iteration += 1

    def reset_step_iteration(self) -> None:
        self.step_iteration = 0
