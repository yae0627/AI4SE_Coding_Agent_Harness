from abc import ABC, abstractmethod
from collections.abc import Iterator


class LLMAdapter(ABC):
    @abstractmethod
    def generate(self, messages: list[dict]) -> str:
        pass

    def generate_stream(self, messages: list[dict]) -> Iterator[str]:
        """Stream response token by token. Default: yield entire response at once."""
        yield self.generate(messages)
