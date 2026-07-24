from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.prompt_context import PromptContext


class ToolSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        if not ctx.tools:
            return ""

        tools = [s for s in ctx.tools if s.get("_category") != "control"]
        controls = [s for s in ctx.tools if s.get("_category") == "control"]
        lines: list[str] = []

        if tools:
            lines.append("### Tools")
            lines.append("Execute external operations: read/write files, run shell commands and tests.")
            lines.append("")
            self._render_schemas(lines, tools)

        if controls:
            lines.append("### Conversation")
            lines.append("Communicate with the user or control task flow.")
            lines.append("")
            self._render_schemas(lines, controls)

        return "\n".join(lines).rstrip()

    @staticmethod
    def _render_schemas(lines: list[str], schemas: list[dict]) -> None:
        for s in schemas:
            name = s.get("name", "unknown")
            desc = s.get("description", "")
            params = s.get("parameters", {}).get("properties", {})
            required = set(s.get("parameters", {}).get("required", []))
            param_parts = []
            for pname, pinfo in params.items():
                ptype = pinfo.get("type", "string")
                req = " (required)" if pname in required else ""
                param_parts.append(f"    {pname}: {ptype}{req}")
            param_block = "\n".join(param_parts) if param_parts else "    (none)"
            lines.append(f"  {name}: {desc}")
            lines.append(param_block)
            lines.append("")
