from ai4se_agent.context.prompt_context import PromptContext
from ai4se_agent.context.prompt_section import PromptSection


class PromptComposer:
    def __init__(self, sections: list[PromptSection]):
        self._sections = sections

    def compose(self, ctx: PromptContext) -> str:
        parts = []
        for section in self._sections:
            text = section.build(ctx)
            if text:
                parts.append(text)
        return "\n\n".join(parts)
