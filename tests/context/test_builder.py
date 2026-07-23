from ai4se_agent.context.builder import ContextBuilder
from ai4se_agent.context.prompt import build_system_prompt
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.tools.read_file import ReadFileTool
from ai4se_agent.tools.shell import ShellTool
from ai4se_agent.types import Action


def test_build_initial_context():
    tools = [ReadFileTool(), ShellTool()]
    builder = ContextBuilder(tools=tools)
    state = AgentState(goal="list files")
    messages = builder.build(state)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "read_file" in messages[0]["content"]
    assert "shell" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "list files"


def test_build_with_history():
    tools = [ShellTool()]
    builder = ContextBuilder(tools=tools)
    state = AgentState(goal="list files")
    action = Action(name="shell", parameters={"command": "dir"})
    state.record_turn(action, "file1.txt\nfile2.txt")
    messages = builder.build(state)
    assert len(messages) == 4
    assert messages[2]["role"] == "assistant"
    assert messages[3]["role"] == "tool"
    assert "file1.txt" in messages[3]["content"]


def test_build_with_feedback():
    tools = [ShellTool()]
    builder = ContextBuilder(tools=tools)
    state = AgentState(goal="fix bug")
    state.record_feedback("pytest failed: AssertionError on line 42")
    messages = builder.build(state)
    assert len(messages) == 3
    assert messages[2]["role"] == "user"
    assert "AssertionError" in messages[2]["content"]


def test_system_prompt_includes_all_tools():
    tools = [ReadFileTool(), ShellTool()]
    prompt = build_system_prompt(tools)
    assert "read_file" in prompt
    assert "shell" in prompt
    assert "action:" in prompt
