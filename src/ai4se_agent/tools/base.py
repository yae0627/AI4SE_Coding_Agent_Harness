from abc import ABC, abstractmethod
from ai4se_agent.types import ToolResult


class Tool(ABC):
    name: str

    @abstractmethod
    def execute(self, params: dict) -> ToolResult:
        pass
