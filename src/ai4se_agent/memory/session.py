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
