from abc import ABC, abstractmethod
from ai4se_agent.types import ToolResult


class Tool(ABC):
    name: str

    @property
    @abstractmethod
    def schema(self) -> dict:
        pass

    @abstractmethod
    def execute(self, params: dict) -> ToolResult:
        pass
