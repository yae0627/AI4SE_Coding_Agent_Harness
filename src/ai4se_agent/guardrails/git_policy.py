import re
from ai4se_agent.guardrails.base import Policy
from ai4se_agent.types import Action, GuardrailResult


HIGH_RISK_GIT = [r'git\s+push', r'git\s+reset\s+--hard', r'git\s+merge', r'git\s+rebase']


class GitPolicy(Policy):
    def check(self, action: Action) -> GuardrailResult | None:
        if action.name != "shell":
            return None
        command = action.parameters.get("command", "")
        for pattern in HIGH_RISK_GIT:
            if re.search(pattern, command):
                return GuardrailResult(
                    verdict="REQUIRE_APPROVAL", reason=f"High-risk git operation: {pattern}",
                    policy="GitPolicy", severity=3, metadata={"command": command}
                )
        return GuardrailResult(verdict="ALLOW", reason="Safe git command", policy="GitPolicy")
