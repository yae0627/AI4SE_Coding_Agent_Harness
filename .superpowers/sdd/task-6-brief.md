# Task 6: Guardrail System

**Files:**
- Create: `src/ai4se_agent/guardrails/base.py`
- Create: `src/ai4se_agent/guardrails/engine.py`
- Create: `src/ai4se_agent/guardrails/command_policy.py`
- Create: `src/ai4se_agent/guardrails/file_policy.py`
- Create: `src/ai4se_agent/guardrails/workspace_policy.py`
- Create: `src/ai4se_agent/guardrails/git_policy.py`
- Create: `tests/guardrails/test_engine.py`
- Create: `tests/guardrails/test_command_policy.py`
- Create: `tests/guardrails/test_file_policy.py`
- Create: `tests/guardrails/test_workspace_policy.py`
- Create: `tests/guardrails/test_git_policy.py`

**Interfaces:**
- Consumes: `Action`, `GuardrailResult` from Task 1
- Produces: `GuardrailEngine.check(action) -> GuardrailResult` consumed by state machine

## Step 1: Write the failing tests

```python
# tests/guardrails/test_command_policy.py
from ai4se_agent.guardrails.command_policy import CommandPolicy
from ai4se_agent.types import Action

def test_block_rm_rf():
    policy = CommandPolicy()
    action = Action(name="shell", params={"command": "rm -rf /"})
    result = policy.check(action)
    assert result.verdict == "DENY"

def test_allow_safe_command():
    policy = CommandPolicy()
    action = Action(name="shell", params={"command": "echo hello"})
    result = policy.check(action)
    assert result.verdict == "ALLOW"
```

```python
# tests/guardrails/test_file_policy.py
from ai4se_agent.guardrails.file_policy import FilePolicy
from ai4se_agent.types import Action

def test_block_git_write():
    policy = FilePolicy()
    action = Action(name="write_file", params={"path": "/workspace/.git/config", "content": ""})
    result = policy.check(action)
    assert result.verdict == "DENY"
```

```python
# tests/guardrails/test_workspace_policy.py
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
```

```python
# tests/guardrails/test_git_policy.py
from ai4se_agent.guardrails.git_policy import GitPolicy
from ai4se_agent.types import Action

def test_block_push():
    policy = GitPolicy()
    action = Action(name="shell", params={"command": "git push origin main"})
    result = policy.check(action)
    assert result.verdict == "REQUIRE_APPROVAL"

def test_allow_status():
    policy = GitPolicy()
    action = Action(name="shell", params={"command": "git status"})
    result = policy.check(action)
    assert result.verdict == "ALLOW"
```

```python
# tests/guardrails/test_engine.py
from ai4se_agent.guardrails.engine import GuardrailEngine
from ai4se_agent.guardrails.command_policy import CommandPolicy
from ai4se_agent.types import Action

def test_engine_block_dangerous():
    engine = GuardrailEngine()
    engine.add_policy(CommandPolicy())
    action = Action(name="shell", params={"command": "rm -rf /"})
    result = engine.check(action)
    assert result.verdict == "DENY"
```

## Step 2: Run tests to verify they fail

Run: `pytest tests/guardrails/ -v`
Expected: FAIL

## Step 3: Write minimal implementations

```python
# src/ai4se_agent/guardrails/base.py
from abc import ABC, abstractmethod
from ai4se_agent.types import Action, GuardrailResult


class Policy(ABC):
    @abstractmethod
    def check(self, action: Action) -> GuardrailResult | None:
        pass
```

```python
# src/ai4se_agent/guardrails/engine.py
from ai4se_agent.guardrails.base import Policy
from ai4se_agent.types import Action, GuardrailResult


class GuardrailEngine:
    def __init__(self):
        self._policies: list[Policy] = []

    def add_policy(self, policy: Policy) -> None:
        self._policies.append(policy)

    def check(self, action: Action) -> GuardrailResult:
        results = []
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
```

```python
# src/ai4se_agent/guardrails/command_policy.py
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
```

```python
# src/ai4se_agent/guardrails/file_policy.py
from ai4se_agent.guardrails.base import Policy
from ai4se_agent.types import Action, GuardrailResult


PROTECTED_PATTERNS = ['.git/', 'node_modules/']


class FilePolicy(Policy):
    def check(self, action: Action) -> GuardrailResult | None:
        if action.name not in ("write_file", "edit_file", "read_file"):
            return None
        path = action.params.get("path", "")
        for pattern in PROTECTED_PATTERNS:
            if pattern in path:
                return GuardrailResult(
                    verdict="DENY", reason=f"Protected path: {pattern}",
                    policy="FilePolicy", severity=4, metadata={"path": path}
                )
        return GuardrailResult(verdict="ALLOW", reason="Safe path", policy="FilePolicy")
```

```python
# src/ai4se_agent/guardrails/workspace_policy.py
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
```

```python
# src/ai4se_agent/guardrails/git_policy.py
import re
from ai4se_agent.guardrails.base import Policy
from ai4se_agent.types import Action, GuardrailResult


HIGH_RISK_GIT = [r'git\s+push', r'git\s+reset\s+--hard', r'git\s+merge', r'git\s+rebase']


class GitPolicy(Policy):
    def check(self, action: Action) -> GuardrailResult | None:
        if action.name != "shell":
            return None
        command = action.params.get("command", "")
        for pattern in HIGH_RISK_GIT:
            if re.search(pattern, command):
                return GuardrailResult(
                    verdict="REQUIRE_APPROVAL", reason=f"High-risk git operation: {pattern}",
                    policy="GitPolicy", severity=3, metadata={"command": command}
                )
        return GuardrailResult(verdict="ALLOW", reason="Safe git command", policy="GitPolicy")
```

## Step 4: Run tests

Run: `pytest tests/guardrails/ -v`
Expected: PASS

## Step 5: Commit

```bash
git add src/ai4se_agent/guardrails/ tests/guardrails/
git commit -m "feat: add Guardrail system with Command, File, Workspace, Git policies"
```

## Global Constraints

- Python >=3.10
- All core mechanisms must be testable with mock LLM (no network, no real LLM)
- No use of agent orchestration frameworks
- Tests in `tests/` mirroring `src/` structure
- No comments in code unless specified
