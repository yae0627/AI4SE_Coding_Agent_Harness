import subprocess
from ai4se_agent.tools.base import Tool
from ai4se_agent.types import ToolResult


class ShellTool(Tool):
    name = "shell"

    @property
    def schema(self) -> dict:
        return {
            "name": "shell",
            "description": "Execute a shell command",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds"},
                    "workdir": {"type": "string", "description": "Working directory"},
                },
                "required": ["command"],
            },
        }

    def execute(self, params: dict) -> ToolResult:
        command = params["command"]
        timeout = params.get("timeout", 30)
        workdir = params.get("workdir")
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=workdir
            )
            output = result.stdout + result.stderr
            return ToolResult(
                success=result.returncode == 0,
                output=output.strip(),
                metadata={"exit_code": result.returncode}
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="Command timed out")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
