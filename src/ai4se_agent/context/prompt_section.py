from abc import ABC, abstractmethod
from ai4se_agent.context.prompt_context import PromptContext


class PromptSection(ABC):
    """A composable prompt section that builds its portion from PromptContext."""

    @abstractmethod
    def build(self, ctx: PromptContext) -> str:
        pass
