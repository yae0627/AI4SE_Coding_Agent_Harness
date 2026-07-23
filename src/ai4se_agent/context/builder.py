from ai4se_agent.context.prompt_context import PromptContext
from ai4se_agent.context.prompt_composer import PromptComposer
from ai4se_agent.context.sections import (
    SystemRoleSection, ToolSection, FormatSection,
    ExampleSection, WorkspaceSection, RulesSection,
)
from ai4se_agent.context.workspace import WorkspaceCollector
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.tools.registry import ToolRegistry


class ContextBuilder:
    def __init__(self, tool_registry: ToolRegistry, workspace_root: str = "."):
        self._schemas = tool_registry.list_schemas()
        self._collector = WorkspaceCollector(workspace_root)
        self._composer = PromptComposer([
            SystemRoleSection(),
            ToolSection(),
            FormatSection(),
            ExampleSection(),
            WorkspaceSection(),
            RulesSection(),
        ])

    def build(self, state: AgentState) -> list[dict]:
        workspace = self._collector.collect()
        ctx = PromptContext(
            tools=self._schemas,
            goal=state.goal,
            workspace=workspace,
            rules=[],
            feedback=state.feedback,
        )
        system_prompt = self._composer.compose(ctx)

        messages: list[dict] = []
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": state.goal})
        messages.extend(state.history)
        messages.extend(state.feedback)
        return messages
