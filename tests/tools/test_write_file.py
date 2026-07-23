from ai4se_agent.tools.write_file import WriteFileTool
from ai4se_agent.types import Action

def test_write_file(tmp_path):
    tool = WriteFileTool()
    target = tmp_path / "out.txt"
    action = Action(name="write_file", parameters={"path": str(target), "content": "new content"})
    result = tool.execute(action.parameters)
    assert result.success is True
    assert target.read_text() == "new content"
