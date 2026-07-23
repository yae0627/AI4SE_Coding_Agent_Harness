from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.prompt_context import PromptContext


class ToolSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        lines = ["## Tools"]
        for s in ctx.tools:
            name = s["name"]
            desc = s.get("description", "")
            params = s["parameters"]["properties"]
            required = set(s["parameters"].get("required", []))
            param_strs = []
            for pname, pinfo in params.items():
                ptype = pinfo.get("type", "string")
                req = " (required)" if pname in required else ""
                param_strs.append(f"    {pname}: {ptype}{req}")
            param_block = "\n".join(param_strs) if param_strs else "    (none)"
            lines.append(f"  {name}: {desc}\n{param_block}")
        return "\n".join(lines)
