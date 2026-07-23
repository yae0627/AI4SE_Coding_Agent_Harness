class MessageHistory:
    def __init__(self, max_messages: int = 50):
        self._messages: list[dict] = []
        self._max_messages = max_messages

    def add_user(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})
        self._trim()

    def add_assistant(self, content: str) -> None:
        self._messages.append({"role": "assistant", "content": content})
        self._trim()

    def add_tool_result(self, action_name: str, output: str) -> None:
        self._messages.append({"role": "tool", "content": output, "name": action_name})
        self._trim()

    def add_system(self, content: str) -> None:
        self._messages.append({"role": "system", "content": content})
        self._trim()

    def add_turn(self, user_message: str, result: dict) -> None:
        self.add_user(user_message)
        self.add_assistant(f"Task completed: {result['status']} ({result['reason']})")

    def get_recent(self, n: int | None = None) -> list[dict]:
        count = n if n is not None else self._max_messages
        return self._messages[-count:] if count < len(self._messages) else list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def _trim(self) -> None:
        while len(self._messages) > self._max_messages:
            self._messages.pop(0)
