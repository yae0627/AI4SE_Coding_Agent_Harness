from pathlib import Path
from ai4se_agent.tools.base import Tool
from ai4se_agent.types import ToolResult


class ReadFileTool(Tool):
    name = "read_file"

    @property
    def schema(self) -> dict:
        return {
            "name": "read_file",
            "description": "Read a file from disk",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                },
                "required": ["path"],
            },
        }

    def execute(self, params: dict) -> ToolResult:
        path = Path(params["path"])
        try:
            content = path.read_text(encoding="utf-8")
            return ToolResult(success=True, output=content)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
