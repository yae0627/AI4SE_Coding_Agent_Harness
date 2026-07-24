from collections import deque


class ConversationMemory:
    """Unified conversation history — single source of truth for cross-turn context.

    Owned by Session. Survives across send() calls. Replaces the old
    MessageHistory (lossy summaries) and SessionMemory (dead code).
    """

    def __init__(self, max_messages: int = 50):
        self._messages: deque = deque(maxlen=max_messages)

    @property
    def max_messages(self) -> int:
        return self._messages.maxlen

    def append(self, role: str, content: str, metadata: dict | None = None) -> None:
        msg: dict = {"role": role, "content": content}
        if metadata:
            msg["metadata"] = metadata
        self._messages.append(msg)

    def extend(self, messages: list[dict]) -> None:
        for msg in messages:
            self._messages.append(dict(msg))

    def get_recent(self, n: int | None = None) -> list[dict]:
        count = n if n is not None else self._messages.maxlen
        items = list(self._messages)
        return items[-count:] if count < len(items) else items

    def get_all(self) -> list[dict]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()
