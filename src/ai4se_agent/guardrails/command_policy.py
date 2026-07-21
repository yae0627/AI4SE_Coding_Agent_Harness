import re
from ai4se_agent.guardrails.base import Policy
from ai4se_agent.types import Action, GuardrailResult


DANGEROUS_PATTERNS = [
    r'\brm\s+-rf\s+/', r'\bdd\b', r'\bwget\b', r'\bcurl\b.*[-][-]output',
    r'\bmkfs', r'\bformat', r'\b> /dev/sda', r'\| sh', r'> /dev/',
]


class CommandPolicy(Policy):
    def check(self, action: Action) -> GuardrailResult | None:
        if action.name != "shell":
            return None
        command = action.params.get("command", "")
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return GuardrailResult(
                    verdict="DENY", reason=f"Dangerous command matched: {pattern}",
                    policy="CommandPolicy", severity=5, metadata={"command": command}
                )
        return GuardrailResult(verdict="ALLOW", reason="Safe command", policy="CommandPolicy")
