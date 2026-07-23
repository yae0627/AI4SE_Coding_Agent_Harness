from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.prompt_context import PromptContext


class WorkspaceSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        ws = ctx.workspace
        if ws is None:
            return ""
        lines = [
            "## Environment",
            f"  OS: {ws.os}",
            f"  Working directory: {ws.cwd}",
            f"  Git branch: {ws.git_branch}",
            f"  Time: {ws.timestamp}",
        ]
        if ws.files:
            lines.append("  Visible files:")
            for f in ws.files:
                lines.append(f"    - {f}")
        return "\n".join(lines)
