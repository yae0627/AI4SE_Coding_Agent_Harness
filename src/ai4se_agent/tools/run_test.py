import subprocess
from ai4se_agent.tools.base import Tool
from ai4se_agent.types import ToolResult


class RunTestTool(Tool):
    name = "run_test"

    @property
    def schema(self) -> dict:
        return {
            "name": "run_test",
            "description": "Run a pytest test suite",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_path": {"type": "string", "description": "Path to test file or directory"},
                    "args": {"type": "string", "description": "Additional pytest arguments"},
                },
                "required": [],
            },
        }

    def execute(self, params: dict) -> ToolResult:
        test_path = params.get("test_path", "")
        args = params.get("args", "")
        try:
            cmd = f"python -m pytest {test_path} {args} -v"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
            output = result.stdout + result.stderr
            return ToolResult(
                success=result.returncode == 0,
                output=output.strip(),
                metadata={"exit_code": result.returncode}
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="Test timed out")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
