class OutputBuffer:
    """Stores all output lines for the terminal UI conversation area."""

    def __init__(self):
        self._lines: list[str] = []

    def append(self, line: str) -> None:
        self._lines.append(line)

    def extend(self, lines: list[str]) -> None:
        self._lines.extend(lines)

    def get_all(self) -> list[str]:
        return list(self._lines)

    def clear(self) -> None:
        self._lines.clear()

    def __len__(self) -> int:
        return len(self._lines)
