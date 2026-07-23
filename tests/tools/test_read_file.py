from ai4se_agent.tools.read_file import ReadFileTool
from ai4se_agent.types import Action

def test_read_existing_file(tmp_path):
    tool = ReadFileTool()
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2")
    action = Action(name="read_file", parameters={"path": str(test_file)})
    result = tool.execute(action.parameters)
    assert result.success is True
    assert "line1" in result.output

def test_read_nonexistent_file():
    tool = ReadFileTool()
    action = Action(name="read_file", parameters={"path": "/nonexistent/file.txt"})
    result = tool.execute(action.parameters)
    assert result.success is False
    assert result.error is not None
