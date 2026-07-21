from pathlib import Path
from ai4se_agent.tools.base import Tool
from ai4se_agent.types import ToolResult


class WriteFileTool(Tool):
    name = "write_file"

    def execute(self, params: dict) -> ToolResult:
        path = Path(params["path"])
        content = params["content"]
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return ToolResult(success=True, output=f"Written {len(content)} bytes")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
