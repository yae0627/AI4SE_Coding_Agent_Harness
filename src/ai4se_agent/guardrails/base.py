from abc import ABC, abstractmethod
from ai4se_agent.types import Action, GuardrailResult


class Policy(ABC):
    @abstractmethod
    def check(self, action: Action) -> GuardrailResult | None:
        pass
