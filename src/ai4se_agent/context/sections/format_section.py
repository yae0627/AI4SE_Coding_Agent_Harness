from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.prompt_context import PromptContext


class FormatSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        return (
            "## Response Format\n\n"
            "Respond with exactly one JSON object per turn:\n\n"
            '  {"action": "<tool_name>", "parameters": {"key": "value"}}\n\n'
            "Important rules:\n"
            "- Each response must contain exactly one JSON action.\n"
            "- For multi-line content, use \\n for newlines inside JSON strings.\n"
            "- All double quotes inside string values MUST be escaped with backslash: \\\"\n"
            "- Example of properly escaped code string:\n"
            '  {"action": "write_file", "parameters": {"path": "x.cpp", "content": "#include <iostream>\\nint main() { std::cout << \\"hi\\"; }\\n"}}\n\n'
            "- To finish the task, use the finish action:\n"
            '  {"action": "finish", "parameters": {"summary": "Task completed"}}'
        )
