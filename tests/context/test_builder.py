from ai4se_agent.context.builder import ContextBuilder
from ai4se_agent.context.prompt import build_system_prompt
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.tools.read_file import ReadFileTool
from ai4se_agent.tools.write_file import WriteFileTool
from ai4se_agent.tools.shell import ShellTool
from ai4se_agent.types import Action


def test_system_prompt_includes_all_tools():
    prompt = build_system_prompt([ReadFileTool().schema, WriteFileTool().schema])
    assert "read_file" in prompt
    assert "write_file" in prompt
    assert "finish" in prompt  # finish is always included
    assert "json" in prompt.lower()  # mentions JSON format
    assert "[DONE]" not in prompt  # no longer uses [DONE]


def test_build_initial_context():
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    builder = ContextBuilder(registry)
    state = AgentState(goal="test task")
    messages = builder.build(state)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "test task"


def test_build_with_history():
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    builder = ContextBuilder(registry)
    state = AgentState(goal="test")
    action = Action(name="shell", parameters={"command": "dir"})
    state.record_turn(action, "file1.txt\nfile2.txt")
    messages = builder.build(state)
    assert len(messages) == 4
    assert messages[2]["role"] == "assistant"
    assert messages[3]["role"] == "tool"
    assert "file1.txt" in messages[3]["content"]


def test_build_with_feedback():
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    builder = ContextBuilder(registry)
    state = AgentState(goal="fix bug")
    state.record_feedback("pytest failed: AssertionError on line 42")
    messages = builder.build(state)
    assert len(messages) == 3
    assert messages[2]["role"] == "user"
    assert "AssertionError" in messages[2]["content"]
