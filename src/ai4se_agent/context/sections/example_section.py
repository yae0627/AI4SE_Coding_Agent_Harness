from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.prompt_context import PromptContext


class ExampleSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        return (
            "## Example Session\n\n"
            '{"action": "write_file", "parameters": {"path": "main.cpp", "content": "#include <iostream>\\nint main() { std::cout << \\"hello\\"; }\\n"}}\n'
            '{"action": "shell", "parameters": {"command": "g++ -o main main.cpp"}}\n'
            '{"action": "shell", "parameters": {"command": "./main"}}\n'
            '{"action": "finish", "parameters": {"summary": "Compiled and ran successfully"}}'
        )
