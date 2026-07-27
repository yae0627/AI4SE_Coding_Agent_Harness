from ai4se_agent.context.prompt_context import PromptContext
from ai4se_agent.context.prompt_section import PromptSection


class WorkspaceSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        ws = ctx.workspace
        if ws is None:
            return ""
        os_hint = {
            "win32": "Windows (use cmd.exe or PowerShell, NOT bash/Unix commands)",
            "linux": "Linux (use bash/sh commands)",
            "darwin": "macOS (use bash/zsh commands)",
        }.get(ws.os, ws.os)

        lines = [
            "## Environment",
            f"  OS: {os_hint}",
            f"  Working directory: {ws.cwd}",
            f"  Git branch: {ws.git_branch}",
            f"  Time: {ws.timestamp}",
        ]
        if ws.files:
            lines.append("  Visible files:")
            for f in ws.files:
                lines.append(f"    - {f}")
        return "\n".join(lines)
