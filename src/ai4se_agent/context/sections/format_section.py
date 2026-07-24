from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.prompt_context import PromptContext


class FormatSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        return (
            "## Response Format\n\n"
            "Respond with exactly one JSON object per turn:\n\n"
            '  {"action": "<action_name>", "parameters": {"key": "value"}}\n\n'
            "Available actions are listed above in Tools and Conversation sections.\n\n"
            "Important rules:\n"
            "- Each response must contain exactly one JSON action.\n"
            "- For multi-line content, use \\n for newlines inside JSON strings.\n"
            "- All double quotes inside string values MUST be escaped with backslash: \\\"\n"
            "- Example of properly escaped code string:\n"
            '  {"action": "write_file", "parameters": {"path": "x.cpp", "content": "#include <iostream>\\nint main() { std::cout << \\"hi\\"; }\\n"}}\n\n'
            "- To communicate with the user, use the respond action:\n"
            '  {"action": "respond", "parameters": {"message": "I will now analyze the code structure..."}}\n\n'
            "- To finish the task, use the finish action:\n"
            '  {"action": "finish", "parameters": {"summary": "Task completed"}}'
        )
