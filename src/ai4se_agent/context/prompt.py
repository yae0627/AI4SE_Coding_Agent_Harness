def build_tool_descriptions(schemas: list[dict]) -> str:
    lines = []
    for s in schemas:
        name = s["name"]
        desc = s.get("description", "")
        params = s["parameters"]["properties"]
        required = set(s["parameters"].get("required", []))
        param_strs = []
        for pname, pinfo in params.items():
            ptype = pinfo.get("type", "string")
            req = " (required)" if pname in required else " (optional)"
            param_strs.append(f"      {pname}: {ptype}{req}")
        param_block = "\n".join(param_strs) if param_strs else "      (none)"
        lines.append(f"  - {name}: {desc}\n{param_block}")
    return "\n".join(lines)


FINISH_SCHEMA = {
    "name": "finish",
    "description": "Signal that the task is complete",
    "parameters": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Brief summary of what was accomplished"
            }
        },
        "required": []
    }
}


def build_system_prompt(schemas: list[dict]) -> str:
    all_schemas = list(schemas) + [FINISH_SCHEMA]
    tool_descriptions = build_tool_descriptions(all_schemas)

    return (
        "You are a coding agent. You can use the following tools:\n\n"
        f"{tool_descriptions}\n\n"
        "Respond with a JSON object in exactly this format:\n"
        '{"action": "<tool_name>", "parameters": {"key": "value"}}\n\n'
        "For multi-line content, use \\n for newlines inside the JSON string:\n"
        '{"action": "write_file", "parameters": {"path": "main.cpp", "content": "#include <iostream>\\nint main() {}\\n"}}\n\n'
        "To finish the task, use the finish action:\n"
        '{"action": "finish", "parameters": {"summary": "Task completed"}}\n\n'
        "Example:\n"
        '{"action": "write_file", "parameters": {"path": "main.cpp", "content": "#include <iostream>\\nint main() { std::cout << \\"hello\\"; }\\n"}}\n'
        '{"action": "shell", "parameters": {"command": "g++ -o main main.cpp"}}\n'
        '{"action": "shell", "parameters": {"command": "main.exe"}}\n'
        '{"action": "finish", "parameters": {"summary": "Compiled and ran successfully"}}'
    )
