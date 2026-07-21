from ai4se_agent.tools.shell import ShellTool

def test_shell_success():
    tool = ShellTool()
    result = tool.execute({"command": "echo hello", "timeout": 5})
    assert result.success is True
    assert "hello" in result.output

def test_shell_failure():
    tool = ShellTool()
    result = tool.execute({"command": "exit 1", "timeout": 5})
    assert result.success is False
