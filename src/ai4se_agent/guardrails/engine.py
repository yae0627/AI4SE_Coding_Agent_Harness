from ai4se_agent.guardrails.base import Policy
from ai4se_agent.types import Action, GuardrailResult


class GuardrailEngine:
    def __init__(self) -> None:
        self._policies: list[Policy] = []

    def add_policy(self, policy: Policy) -> None:
        self._policies.append(policy)

    def check(self, action: Action) -> GuardrailResult:
        results: list[GuardrailResult] = []
        for policy in self._policies:
            result = policy.check(action)
            if result is not None:
                results.append(result)
        for r in results:
            if r.verdict == "DENY":
                return r
        for r in results:
            if r.verdict == "REQUIRE_APPROVAL":
                return r
        return GuardrailResult(verdict="ALLOW", reason="All policies passed", policy="all")
