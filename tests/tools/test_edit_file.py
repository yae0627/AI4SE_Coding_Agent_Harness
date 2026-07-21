from ai4se_agent.tools.edit_file import EditFileTool
from ai4se_agent.types import Action

def test_edit_file(tmp_path):
    tool = EditFileTool()
    target = tmp_path / "test.txt"
    target.write_text("hello world\nfoo bar")
    action = Action(name="edit_file", params={"path": str(target), "old_string": "foo bar", "new_string": "baz qux"})
    result = tool.execute(action.params)
    assert result.success is True
    assert target.read_text() == "hello world\nbaz qux"

def test_edit_file_no_match(tmp_path):
    tool = EditFileTool()
    target = tmp_path / "test.txt"
    target.write_text("hello")
    action = Action(name="edit_file", params={"path": str(target), "old_string": "nonexistent", "new_string": "replacement"})
    result = tool.execute(action.params)
    assert result.success is False
