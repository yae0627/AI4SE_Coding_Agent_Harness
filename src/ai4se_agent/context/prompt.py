from ai4se_agent.tools.base import Tool


def build_system_prompt(tools: list[Tool]) -> str:
    tool_lines = []
    for tool in tools:
        tool_lines.append(f"- {tool.name}")
    tools_section = "\n".join(tool_lines) if tool_lines else "- (no tools registered)"

    return (
        "You are a coding agent. You can use the following tools:\n"
        f"{tools_section}\n\n"
        "Respond with exactly one line in this format:\n"
        "action: <tool_name> key=value key=value\n"
        "When the task is complete, respond with: [DONE]"
    )
