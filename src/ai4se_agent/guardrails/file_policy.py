from ai4se_agent.guardrails.base import Policy
from ai4se_agent.types import Action, GuardrailResult


PROTECTED_PATTERNS = ['.git/', 'node_modules/']


class FilePolicy(Policy):
    def check(self, action: Action) -> GuardrailResult | None:
        if action.name not in ("write_file", "edit_file", "read_file"):
            return None
        path = action.parameters.get("path", "")
        for pattern in PROTECTED_PATTERNS:
            if pattern in path:
                return GuardrailResult(
                    verdict="DENY", reason=f"Protected path: {pattern}",
                    policy="FilePolicy", severity=4, metadata={"path": path}
                )
        return GuardrailResult(verdict="ALLOW", reason="Safe path", policy="FilePolicy")
