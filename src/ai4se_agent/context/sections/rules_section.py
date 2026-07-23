from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.prompt_context import PromptContext


class RulesSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        if not ctx.rules:
            return ""
        lines = ["## Project Rules"]
        for r in ctx.rules:
            lines.append(f"  - {r}")
        return "\n".join(lines)
