import subprocess
import sys
from ai4se_agent.tools.base import Tool
from ai4se_agent.types import ToolResult

_OS_HINT = {
    "win32": "Execute a shell command via cmd.exe. Use Windows syntax (dir, del, type, findstr), NOT bash commands (ls, rm, cat, grep, head).",
    "linux": "Execute a shell command via bash. Use standard Unix/Linux syntax.",
    "darwin": "Execute a shell command via zsh/bash. Use standard macOS/Unix syntax.",
}.get(sys.platform, "Execute a shell command.")


class ShellTool(Tool):
    name = "shell"

    @property
    def schema(self) -> dict:
        return {
            "name": "shell",
            "description": _OS_HINT,
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds"},
                    "workdir": {"type": "string", "description": "Working directory (use / not \\)", "format": "path"},
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
