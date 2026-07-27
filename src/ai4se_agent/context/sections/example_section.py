from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.prompt_context import PromptContext


class ExampleSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        return (
            "## Example Session\n\n"
            "User: create a hello world program\n\n"
            '  {"message": "I will create a hello.cpp file, compile it, and run it.", '
            '"action": {"name": "write_file", "parameters": {"path": "main.cpp", '
            '"content": "#include <iostream>\\nint main() { std::cout << \\"hello\\"; }\\n"}}}\n\n'
            '  {"message": "File written, now compiling.", '
            '"action": {"name": "shell", "parameters": {"command": "g++ -o main main.cpp"}}}\n\n'
            '  {"action": {"name": "shell", "parameters": {"command": "./main"}}}\n\n'
            '  {"message": "Compiled and ran successfully. Output: hello", '
            '"action": {"name": "finish", "parameters": {}}}'
        )
