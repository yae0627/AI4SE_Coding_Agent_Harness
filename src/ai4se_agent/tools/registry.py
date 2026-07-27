from ai4se_agent.core.sanitizer.path import PathNormalizer
from ai4se_agent.tools.base import Tool
from ai4se_agent.types import Action, ToolResult


class ToolRegistry:
    def __init__(self, path_normalizer: PathNormalizer | None = None):
        self._tools: dict[str, Tool] = {}
        self._normalizer = path_normalizer

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def execute(self, action: Action) -> ToolResult:
        tool = self._tools.get(action.name)
        if not tool:
            return ToolResult(success=False, output="", error=f"Unknown tool: {action.name}")

        # Normalize path parameters before tool execution
        params = dict(action.parameters)
        schema = tool.schema
        for key, prop in schema.get("parameters", {}).get("properties", {}).items():
            if prop.get("format") == "path" and key in params:
                if self._normalizer is not None:
                    try:
                        params[key] = str(self._normalizer.normalize(params[key]))
                    except ValueError as e:
                        return ToolResult(success=False, output="", error=str(e))
                else:
                    # Basic fallback: always convert backslashes
                    params[key] = params[key].replace("\\", "/")

        try:
            return tool.execute(params)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    def list_schemas(self) -> list[dict]:
        return [tool.schema for tool in self._tools.values()]
