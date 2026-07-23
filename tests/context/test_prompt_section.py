import pytest

from ai4se_agent.context.prompt_context import PromptContext
from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.workspace import WorkspaceSnapshot


class _TestSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        return f"Tools: {len(ctx.tools)}, Goal: {ctx.goal}"


def test_prompt_context_defaults():
    ctx = PromptContext(tools=[], goal="test")
    assert ctx.tools == []
    assert ctx.goal == "test"
    assert ctx.workspace is None
    assert ctx.rules == []
    assert ctx.feedback == []


def test_prompt_context_with_all_fields():
    ws = WorkspaceSnapshot(
        os="win32", cwd="/tmp", git_branch="main",
        files=["a.py", "b.py"], timestamp="2026-07-23T00:00:00"
    )
    ctx = PromptContext(
        tools=[{"name": "shell"}],
        goal="build",
        workspace=ws,
        rules=["no rm -rf"],
        feedback=[{"role": "user", "content": "fix bug"}]
    )
    assert ctx.workspace.os == "win32"
    assert ctx.rules == ["no rm -rf"]
    assert len(ctx.feedback) == 1


def test_section_protocol():
    section = _TestSection()
    ctx = PromptContext(tools=[{"name": "x"}], goal="hi")
    result = section.build(ctx)
    assert "Tools: 1" in result
    assert "Goal: hi" in result


def test_sections_do_not_mutate_context():
    ctx = PromptContext(tools=[{"name": "x"}], goal="test")
    original_tools = list(ctx.tools)
    _TestSection().build(ctx)
    assert ctx.tools == original_tools


def test_prompt_section_cannot_instantiate():
    with pytest.raises(TypeError):
        PromptSection()  # type: ignore[abstract]


from ai4se_agent.context.prompt_composer import PromptComposer
from ai4se_agent.context.sections.system_role import SystemRoleSection
from ai4se_agent.context.sections.tool_section import ToolSection
from ai4se_agent.context.sections.format_section import FormatSection
from ai4se_agent.context.sections.example_section import ExampleSection
from ai4se_agent.context.sections.workspace_section import WorkspaceSection
from ai4se_agent.context.sections.rules_section import RulesSection


def test_system_role_section():
    section = SystemRoleSection()
    result = section.build(PromptContext(tools=[], goal=""))
    assert "coding agent" in result.lower()


def test_tool_section_lists_all_tools():
    section = ToolSection()
    ctx = PromptContext(tools=[
        {"name": "read_file", "description": "Read a file",
         "parameters": {"type": "object", "properties": {}, "required": []}}
    ], goal="")
    result = section.build(ctx)
    assert "read_file" in result


def test_format_section_includes_json_escaping():
    section = FormatSection()
    result = section.build(PromptContext(tools=[], goal=""))
    assert '{"action"' in result
    assert '\\"' in result


def test_example_section_has_finish():
    section = ExampleSection()
    result = section.build(PromptContext(tools=[], goal=""))
    assert "finish" in result


def test_workspace_section_shows_os():
    section = WorkspaceSection()
    ws = WorkspaceSnapshot(
        os="linux", cwd="/home/user/project",
        git_branch="main", files=["README.md", "src/main.py"],
        timestamp="2026-07-23T12:00:00"
    )
    ctx = PromptContext(tools=[], goal="", workspace=ws)
    result = section.build(ctx)
    assert "linux" in result
    assert "/home/user/project" in result
    assert "main" in result
    assert "README.md" in result


def test_workspace_section_none_workspace():
    section = WorkspaceSection()
    ctx = PromptContext(tools=[], goal="", workspace=None)
    result = section.build(ctx)
    assert result == ""


def test_rules_section_with_rules():
    section = RulesSection()
    ctx = PromptContext(tools=[], goal="", rules=["no rm -rf", "use pathlib"])
    result = section.build(ctx)
    assert "no rm -rf" in result
    assert "use pathlib" in result


def test_rules_section_empty():
    section = RulesSection()
    ctx = PromptContext(tools=[], goal="", rules=[])
    result = section.build(ctx)
    assert result == ""


def test_prompt_composer_joins_sections():
    composer = PromptComposer([
        SystemRoleSection(), ToolSection(), FormatSection()
    ])
    ctx = PromptContext(tools=[
        {"name": "shell", "description": "Run command",
         "parameters": {"type": "object", "properties": {}, "required": []}}
    ], goal="")
    result = composer.compose(ctx)
    assert len(result) > 0
    assert "shell" in result
    assert "coding agent" in result.lower()


def test_prompt_composer_skips_empty_sections():
    composer = PromptComposer([
        SystemRoleSection(), RulesSection()
    ])
    ctx = PromptContext(tools=[], goal="")
    result = composer.compose(ctx)
    assert "coding agent" in result.lower()
    assert "Rules" not in result


def test_composed_prompt_no_workflow_text():
    """B.2: No workflow text in composed prompt."""
    composer = PromptComposer([
        SystemRoleSection(), ToolSection(), FormatSection(),
        ExampleSection(), RulesSection()
    ])
    ctx = PromptContext(tools=[], goal="")
    result = composer.compose(ctx)
    assert "Workflow" not in result
    assert "To complete a task, use tools to" not in result
