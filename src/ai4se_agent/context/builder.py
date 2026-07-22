from ai4se_agent.context.prompt import build_system_prompt
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.tools.base import Tool


class ContextBuilder:
    def __init__(self, tools: list[Tool]):
        self._tools = tools

    def build(self, state: AgentState) -> list[dict]:
        messages: list[dict] = []

        messages.append({"role": "system", "content": build_system_prompt(self._tools)})
        messages.append({"role": "user", "content": state.goal})
        messages.extend(state.history)
        messages.extend(state.feedback)

        return messages
