from dataclasses import dataclass


@dataclass(frozen=True)
class WorkspaceSnapshot:
    os: str = ""
    cwd: str = ""
    git_branch: str = ""
    files: list[str] | None = None
    timestamp: str = ""
