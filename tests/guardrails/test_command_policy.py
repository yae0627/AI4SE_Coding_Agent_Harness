from ai4se_agent.guardrails.command_policy import CommandPolicy
from ai4se_agent.types import Action

def test_block_rm_rf():
    policy = CommandPolicy()
    action = Action(name="shell", parameters={"command": "rm -rf /"})
    result = policy.check(action)
    assert result.verdict == "DENY"

def test_allow_safe_command():
    policy = CommandPolicy()
    action = Action(name="shell", parameters={"command": "echo hello"})
    result = policy.check(action)
    assert result.verdict == "ALLOW"
