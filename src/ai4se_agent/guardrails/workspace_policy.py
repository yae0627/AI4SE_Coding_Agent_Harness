import os
from ai4se_agent.guardrails.base import Policy
from ai4se_agent.types import Action, GuardrailResult


class WorkspacePolicy(Policy):
    def __init__(self, workspace: str):
        self.workspace = os.path.realpath(workspace)

    def check(self, action: Action) -> GuardrailResult | None:
        if action.name not in ("read_file", "write_file", "edit_file"):
            return None
        path = action.params.get("path", "")
        real_path = os.path.realpath(path)
        if not real_path.startswith(self.workspace):
            return GuardrailResult(
                verdict="DENY", reason=f"Path escapes workspace: {real_path}",
                policy="WorkspacePolicy", severity=5, metadata={"path": path, "real_path": real_path}
            )
        return GuardrailResult(verdict="ALLOW", reason="Path within workspace", policy="WorkspacePolicy")
