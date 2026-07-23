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
