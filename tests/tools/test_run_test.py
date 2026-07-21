from ai4se_agent.tools.run_test import RunTestTool

def test_run_test_nonexistent_path():
    tool = RunTestTool()
    result = tool.execute({"test_path": "/nonexistent"})
    assert result.success is False
