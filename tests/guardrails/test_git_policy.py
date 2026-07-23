from ai4se_agent.guardrails.git_policy import GitPolicy
from ai4se_agent.types import Action

def test_block_push():
    policy = GitPolicy()
    action = Action(name="shell", parameters={"command": "git push origin main"})
    result = policy.check(action)
    assert result.verdict == "REQUIRE_APPROVAL"

def test_allow_status():
    policy = GitPolicy()
    action = Action(name="shell", parameters={"command": "git status"})
    result = policy.check(action)
    assert result.verdict == "ALLOW"
