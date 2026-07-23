from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.prompt_context import PromptContext


class ToolSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        if not ctx.tools:
            return ""
        lines = ["## Tools"]
        for s in ctx.tools:
            name = s.get("name", "unknown")
            desc = s.get("description", "")
            params = s.get("parameters", {}).get("properties", {})
            required = set(s.get("parameters", {}).get("required", []))
            param_strs = []
            for pname, pinfo in params.items():
                ptype = pinfo.get("type", "string")
                req = " (required)" if pname in required else ""
                param_strs.append(f"    {pname}: {ptype}{req}")
            param_block = "\n".join(param_strs) if param_strs else "    (none)"
            lines.append(f"  {name}: {desc}\n{param_block}")
        return "\n".join(lines)
