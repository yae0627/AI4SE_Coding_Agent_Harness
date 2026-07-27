from ai4se_agent.context.prompt_context import PromptContext
from ai4se_agent.context.prompt_section import PromptSection


class FormatSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        return (
            "## Response Format\n\n"
            "Respond with exactly one JSON object per turn:\n\n"
            '  {\n'
            '    "message": "<optional: text to show the user>",\n'
            '    "action": {\n'
            '      "name": "<action_name>",\n'
            '      "parameters": {"key": "value"}\n'
            '    }\n'
            '  }\n\n'
            "The 'message' field is optional -- include it when you want to explain "
            "your reasoning, report progress, or summarize results. "
            "Omit it for routine tool executions.\n\n"
            "The 'action' field is optional -- omit it when you only want to send a message. "
            "When both are present, the message is shown to the user before the action executes.\n\n"
            "Available action names are listed in Tools and Conversation sections above.\n\n"
            "Important rules:\n"
            "- Each response must contain at least one of 'message' or 'action'.\n"
            "- For all file paths, always use forward slashes (/) as the directory separator.\n"
            "- For multi-line content, use \\n for newlines inside JSON strings.\n"
            "- All double quotes inside string values MUST be escaped with backslash: \\\"\n"
            "- Example of properly escaped code string:\n"
            '  {"message": "Writing the C++ file", "action": {"name": "write_file", "parameters": {"path": "x.cpp", "content": "#include <iostream>\\\nint main() { std::cout << \\\"hi\\\"; }\\\n"}}}\n\n'
            "- To communicate with the user without executing a tool, send only a message:\n"
            '  {"message": "I found 3 potential issues in the codebase..."}\n\n'
            "- To finish the task, use the finish action:\n"
            '  {"message": "Task completed: all tests pass.", "action": {"name": "finish", "parameters": {}}}\n\n'
            "- For complex multi-step tasks, use plan_create first:\n"
            '  {"message": "Breaking into steps", "action": {"name": "plan_create", "parameters": {"steps": ["Step 1: ...", "Step 2: ..."]}}}\n'
            "- After plan_create, immediately start executing the first step with tool calls.\n"
            "- Use plan_update to mark progress: in_progress when starting, done when finished.\n"
            "- To ask the user a question (and wait for their response), use the ask action:\n"
            '  {"action": {"name": "ask", "parameters": {"question": "Which file should I modify?"}}}'
        )
