from ai4se_agent.context.builder import ContextBuilder
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.tools.read_file import ReadFileTool
from ai4se_agent.tools.write_file import WriteFileTool
from ai4se_agent.tools.shell import ShellTool
from ai4se_agent.types import Action


def test_build_initial_context(tmp_path):
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    builder = ContextBuilder(tool_registry=registry, workspace_root=str(tmp_path))
    state = AgentState(goal="test task")
    messages = builder.build(state)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "test task"


def test_system_prompt_includes_tools():
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(ShellTool())
    builder = ContextBuilder(tool_registry=registry, workspace_root=".")
    state = AgentState(goal="test")
    messages = builder.build(state)
    prompt = messages[0]["content"]
    assert "read_file" in prompt
    assert "shell" in prompt
    assert "finish" in prompt


def test_system_prompt_includes_workspace(tmp_path):
    (tmp_path / "main.py").write_text("x")
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    builder = ContextBuilder(tool_registry=registry, workspace_root=str(tmp_path))
    state = AgentState(goal="test")
    messages = builder.build(state)
    prompt = messages[0]["content"]
    assert "Environment" in prompt or "main.py" in prompt


def test_system_prompt_no_workflow_text():
    """B.2: composed prompt must not contain workflow instructions."""
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    builder = ContextBuilder(tool_registry=registry, workspace_root=".")
    state = AgentState(goal="test")
    messages = builder.build(state)
    prompt = messages[0]["content"]
    assert "Workflow" not in prompt


def test_system_prompt_includes_json_format():
    registry = ToolRegistry()
    builder = ContextBuilder(tool_registry=registry, workspace_root=".")
    state = AgentState(goal="test")
    messages = builder.build(state)
    prompt = messages[0]["content"]
    assert "json" in prompt.lower() or '{"action"' in prompt


def test_build_with_history(tmp_path):
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    builder = ContextBuilder(tool_registry=registry, workspace_root=str(tmp_path))
    state = AgentState(goal="test")
    action = Action(name="shell", parameters={"command": "dir"})
    state.record_turn(action, "file1.txt\nfile2.txt")
    messages = builder.build(state)
    assert len(messages) == 4
    assert messages[2]["role"] == "assistant"
    assert messages[3]["role"] == "tool"


def test_build_with_feedback(tmp_path):
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    builder = ContextBuilder(tool_registry=registry, workspace_root=str(tmp_path))
    state = AgentState(goal="fix bug")
    state.record_feedback("pytest failed")
    messages = builder.build(state)
    assert len(messages) == 3
    assert messages[2]["role"] == "user"


def test_build_includes_project_rules(tmp_path):
    from ai4se_agent.memory.persistent import PersistentMemory
    pers = PersistentMemory(base_dir=str(tmp_path))
    pers.save_rule("testing", "always use pytest")
    pers.save_rule("style", "use snake_case")

    registry = ToolRegistry()
    registry.register(ReadFileTool())
    builder = ContextBuilder(
        tool_registry=registry,
        workspace_root=str(tmp_path),
        persistent_memory=pers,
    )
    state = AgentState(goal="test")
    messages = builder.build(state)
    prompt = messages[0]["content"]
    assert "always use pytest" in prompt
    assert "use snake_case" in prompt


def test_build_without_persistent_memory_no_rules_section(tmp_path):
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    builder = ContextBuilder(tool_registry=registry, workspace_root=str(tmp_path))
    state = AgentState(goal="test")
    messages = builder.build(state)
    prompt = messages[0]["content"]
    assert "Project Rules" not in prompt
