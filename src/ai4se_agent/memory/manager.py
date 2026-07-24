import json
import uuid
import datetime
from pathlib import Path
from ai4se_agent.session.history import ConversationMemory
from ai4se_agent.memory.persistent import PersistentMemory


class MemoryManager:
    """Aggregation layer for agent memory subsystems.

    Owns:
      - ConversationMemory: cross-turn session history
      - PersistentMemory: project rules and session summaries
      - FailureLog: simple JSON failure records (no auto-learning)
    """

    def __init__(
        self,
        session: ConversationMemory | None = None,
        persistent: PersistentMemory | None = None,
        failure_log_dir: str | None = None,
    ):
        self.session = session or ConversationMemory()
        self.persistent = persistent or PersistentMemory()
        self._failure_dir = Path(failure_log_dir) if failure_log_dir else None

    def get_rules(self) -> list[str]:
        rule_names = sorted(self.persistent.list_rules())
        rules = []
        for name in rule_names:
            content = self.persistent.load_rule(name)
            if content:
                rules.append(content.strip())
        return rules

    def log_failure(self, entry: dict) -> str | None:
        if self._failure_dir is None:
            return None
        self._failure_dir.mkdir(parents=True, exist_ok=True)
        entry.setdefault("timestamp", datetime.datetime.now().isoformat())
        entry.setdefault("id", uuid.uuid4().hex[:8])
        path = self._failure_dir / f"failure_{entry['id']}.json"
        path.write_text(json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8")
        return entry["id"]

    def list_failures(self) -> list[dict]:
        if self._failure_dir is None or not self._failure_dir.exists():
            return []
        entries = []
        for path in sorted(self._failure_dir.glob("failure_*.json")):
            try:
                entries.append(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                pass
        return entries
