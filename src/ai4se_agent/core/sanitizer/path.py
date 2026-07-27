from pathlib import Path, PureWindowsPath


class PathNormalizer:
    """Normalize LLM-generated paths before tool execution.

    Responsibilities:
      1. Separator normalization (backslash → forward slash)
      2. Relative → absolute (resolve against workspace root)
      3. Workspace sandbox boundary check
    """

    def __init__(self, workspace_root: str = "."):
        self._root = Path(workspace_root).resolve()

    @property
    def root(self) -> Path:
        return self._root

    def normalize(self, raw: str) -> Path:
        # Normalize Windows backslash separators to forward slash.
        # Must happen first so pathlib sees a clean path on all platforms.
        raw = raw.replace("\\", "/")

        p = Path(raw)
        if not p.is_absolute():
            p = self._root / p

        resolved = p.resolve()

        # Security: reject paths that escape the workspace sandbox
        try:
            resolved.relative_to(self._root)
        except ValueError:
            raise ValueError(
                f"Path escapes workspace: {raw} → {resolved}"
            )

        return resolved
