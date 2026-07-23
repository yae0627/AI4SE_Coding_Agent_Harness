from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.prompt_context import PromptContext


class SystemRoleSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        return "You are a coding agent. You can use tools to read, write, edit files, run shell commands, and execute tests."
