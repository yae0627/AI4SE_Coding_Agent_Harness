from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.tools.read_file import ReadFileTool
from ai4se_agent.types import Action

def test_register_and_execute(tmp_path):
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")
    action = Action(name="read_file", parameters={"path": str(test_file)})
    result = registry.execute(action)
    assert result.success is True
    assert result.output == "hello"
