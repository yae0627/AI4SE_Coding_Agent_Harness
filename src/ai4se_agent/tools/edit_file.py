from pathlib import Path
from ai4se_agent.tools.base import Tool
from ai4se_agent.types import ToolResult


class EditFileTool(Tool):
    name = "edit_file"

    @property
    def schema(self) -> dict:
        return {
            "name": "edit_file",
            "description": "Edit a file by replacing text",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "old_string": {"type": "string", "description": "Text to replace"},
                    "new_string": {"type": "string", "description": "Replacement text"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        }

    def execute(self, params: dict) -> ToolResult:
        path = Path(params["path"])
        old = params["old_string"]
        new = params["new_string"]
        try:
            content = path.read_text(encoding="utf-8")
            if old not in content:
                return ToolResult(success=False, output="", error=f"String not found: {old[:50]}")
            new_content = content.replace(old, new, 1)
            path.write_text(new_content, encoding="utf-8")
            return ToolResult(success=True, output="Edit applied")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
