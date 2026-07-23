import datetime
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    ".venv",
    "venv",
    ".mypy_cache",
    ".idea",
}
SKIP_PATTERNS = ("*.pyc", "*.pyo", ".DS_Store")


@dataclass(frozen=True)
class WorkspaceSnapshot:
    os: str
    cwd: str
    git_branch: str
    files: list[str]
    timestamp: str


class WorkspaceCollector:
    """Collects workspace metadata into a frozen WorkspaceSnapshot.

    Results are cached with a configurable TTL. Call ``invalidate()`` or
    pass ``force=True`` to ``collect()`` to bypass the cache.
    """

    def __init__(self, workspace_root: str, max_files: int = 50) -> None:
        self._root = Path(workspace_root).resolve()
        self._max_files = max_files
        self._cache: WorkspaceSnapshot | None = None
        self._cache_ttl: float = 5.0
        self._last_collect: float = 0.0

    def collect(self, force: bool = False) -> WorkspaceSnapshot:
        now = time.time()
        if not force and self._cache is not None and (now - self._last_collect) < self._cache_ttl:
            return self._cache

        snapshot = WorkspaceSnapshot(
            os=sys.platform,
            cwd=str(self._root),
            git_branch=self._get_git_branch(),
            files=self._summarize_files(),
            timestamp=datetime.datetime.now().isoformat(),
        )
        self._cache = snapshot
        self._last_collect = now
        return snapshot

    def invalidate(self) -> None:
        self._cache = None
        self._last_collect = 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_git_branch(self) -> str:
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(self._root),
            )
            branch = result.stdout.strip()
            return branch if branch else "unknown"
        except Exception:
            return "unknown"

    def _summarize_files(self) -> list[str]:
        entries: list[str] = []
        try:
            for item in sorted(self._root.iterdir()):
                name = item.name
                if name in SKIP_DIRS:
                    continue
                if any(item.match(p) for p in SKIP_PATTERNS):
                    continue
                if item.is_dir():
                    entries.append(f"{name}/")
                else:
                    entries.append(name)

                if len(entries) >= self._max_files:
                    remaining = sum(1 for _ in self._root.iterdir()) - len(entries)
                    if remaining > 0:
                        entries.append(f"... and {remaining} more files")
                    break
        except PermissionError:
            pass
        return entries
