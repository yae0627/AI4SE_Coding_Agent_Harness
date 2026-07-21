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
