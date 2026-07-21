# Task 7: Memory System

**Files:**
- Create: `src/ai4se_agent/memory/manager.py`
- Create: `src/ai4se_agent/memory/session.py`
- Create: `src/ai4se_agent/memory/persistent.py`
- Create: `tests/memory/test_manager.py`
- Create: `tests/memory/test_session.py`
- Create: `tests/memory/test_persistent.py`

**Interfaces:**
- Consumes: Nothing from this project
- Produces: `MemoryManager` consumed by state machine

## Step 1: Write the failing tests

```python
# tests/memory/test_session.py
from ai4se_agent.memory.session import SessionMemory

def test_session_add_and_get():
    mem = SessionMemory(max_turns=5)
    mem.add("user", "hello")
    mem.add("assistant", "hi")
    turns = mem.get_recent(2)
    assert len(turns) == 2
    assert turns[0]["role"] == "user"

def test_session_lru_eviction():
    mem = SessionMemory(max_turns=3)
    for i in range(5):
        mem.add("user", f"msg{i}")
    turns = mem.get_recent(10)
    assert len(turns) == 3
    assert turns[0]["content"] == "msg2"
```

```python
# tests/memory/test_persistent.py
from ai4se_agent.memory.persistent import PersistentMemory

def test_save_and_load_rule(tmp_path):
    mem = PersistentMemory(base_dir=str(tmp_path))
    mem.save_rule("branch_naming", "Use feat/ prefix")
    loaded = mem.load_rule("branch_naming")
    assert loaded == "Use feat/ prefix"

def test_save_summary(tmp_path):
    mem = PersistentMemory(base_dir=str(tmp_path))
    mem.save_summary("session-1", "Fixed bug in validator")
    summaries = mem.list_summaries()
    assert len(summaries) >= 1
```

```python
# tests/memory/test_manager.py
from ai4se_agent.memory.manager import MemoryManager
from ai4se_agent.memory.session import SessionMemory
from ai4se_agent.memory.persistent import PersistentMemory

def test_manager_adds_to_session(tmp_path):
    mgr = MemoryManager(session=SessionMemory(), persistent=PersistentMemory(base_dir=str(tmp_path)))
    mgr.add_to_session("user", "test")
    assert len(mgr.get_session_history()) == 1
```

## Step 2: Run tests

Run: `pytest tests/memory/ -v`
Expected: FAIL

## Step 3: Write minimal implementations

```python
# src/ai4se_agent/memory/session.py
from collections import deque


class SessionMemory:
    def __init__(self, max_turns: int = 50):
        self._turns = deque(maxlen=max_turns)

    def add(self, role: str, content: str) -> None:
        self._turns.append({"role": role, "content": content})

    def get_recent(self, n: int) -> list:
        return list(self._turns)[-n:]

    def get_all(self) -> list:
        return list(self._turns)

    def clear(self) -> None:
        self._turns.clear()
```

```python
# src/ai4se_agent/memory/persistent.py
from pathlib import Path


class PersistentMemory:
    def __init__(self, base_dir: str = "memory"):
        self._rules_dir = Path(base_dir) / "project_rules"
        self._summaries_dir = Path(base_dir) / "session_summaries"
        self._rules_dir.mkdir(parents=True, exist_ok=True)
        self._summaries_dir.mkdir(parents=True, exist_ok=True)

    def save_rule(self, name: str, content: str) -> None:
        (self._rules_dir / f"{name}.md").write_text(content, encoding="utf-8")

    def load_rule(self, name: str) -> str | None:
        path = self._rules_dir / f"{name}.md"
        return path.read_text(encoding="utf-8") if path.exists() else None

    def list_rules(self) -> list[str]:
        return [p.stem for p in self._rules_dir.glob("*.md")]

    def save_summary(self, session_id: str, summary: str) -> None:
        (self._summaries_dir / f"{session_id}.md").write_text(summary, encoding="utf-8")

    def list_summaries(self) -> list[str]:
        return [p.stem for p in self._summaries_dir.glob("*.md")]
```

```python
# src/ai4se_agent/memory/manager.py
from ai4se_agent.memory.session import SessionMemory
from ai4se_agent.memory.persistent import PersistentMemory


class MemoryManager:
    def __init__(self, session: SessionMemory | None = None, persistent: PersistentMemory | None = None):
        self.session = session or SessionMemory()
        self.persistent = persistent or PersistentMemory()

    def add_to_session(self, role: str, content: str) -> None:
        self.session.add(role, content)

    def get_session_history(self) -> list:
        return self.session.get_all()
```

## Step 4: Run tests

Run: `pytest tests/memory/ -v`
Expected: PASS

## Step 5: Commit

```bash
git add src/ai4se_agent/memory/ tests/memory/
git commit -m "feat: add Memory system with session and persistent storage"
```

## Global Constraints

- Python >=3.10
- All core mechanisms must be testable with mock LLM (no network, no real LLM)
- No use of agent orchestration frameworks
- Tests in `tests/` mirroring `src/` structure
- No comments in code unless specified
