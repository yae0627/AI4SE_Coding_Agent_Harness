from ai4se_agent.context.prompt import build_system_prompt
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.tools.registry import ToolRegistry


class ContextBuilder:
    def __init__(self, tool_registry: ToolRegistry):
        self._schemas = tool_registry.list_schemas()

    def build(self, state: AgentState) -> list[dict]:
        messages: list[dict] = []
        messages.append({"role": "system", "content": build_system_prompt(self._schemas)})
        messages.append({"role": "user", "content": state.goal})
        messages.extend(state.history)
        messages.extend(state.feedback)
        return messages
