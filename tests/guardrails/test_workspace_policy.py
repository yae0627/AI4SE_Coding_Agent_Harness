from ai4se_agent.guardrails.workspace_policy import WorkspacePolicy
from ai4se_agent.types import Action

def test_block_path_escape(tmp_path):
    policy = WorkspacePolicy(workspace=str(tmp_path))
    action = Action(name="read_file", params={"path": str(tmp_path / "../../etc/passwd")})
    result = policy.check(action)
    assert result.verdict == "DENY"

def test_allow_inside_workspace(tmp_path):
    policy = WorkspacePolicy(workspace=str(tmp_path))
    inner = tmp_path / "subdir" / "file.txt"
    inner.parent.mkdir()
    inner.write_text("")
    action = Action(name="read_file", params={"path": str(inner)})
    result = policy.check(action)
    assert result.verdict == "ALLOW"
