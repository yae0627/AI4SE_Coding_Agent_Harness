from ai4se_agent.tools.base import Tool
from ai4se_agent.types import Action, ToolResult


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def execute(self, action: Action) -> ToolResult:
        tool = self._tools.get(action.name)
        if not tool:
            return ToolResult(success=False, output="", error=f"Unknown tool: {action.name}")
        try:
            return tool.execute(action.parameters)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    def list_schemas(self) -> list[dict]:
        return [tool.schema for tool in self._tools.values()]
