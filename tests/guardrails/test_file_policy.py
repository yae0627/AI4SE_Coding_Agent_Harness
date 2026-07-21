from ai4se_agent.guardrails.file_policy import FilePolicy
from ai4se_agent.types import Action

def test_block_git_write():
    policy = FilePolicy()
    action = Action(name="write_file", params={"path": "/workspace/.git/config", "content": ""})
    result = policy.check(action)
    assert result.verdict == "DENY"
