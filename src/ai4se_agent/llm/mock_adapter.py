from collections.abc import Iterator

from ai4se_agent.llm.base import LLMAdapter


class MockAdapter(LLMAdapter):
    def __init__(self, responses: list[str]):
        self.responses = responses
        self._index = 0

    def generate(self, messages: list[dict]) -> str:
        response = self.responses[self._index % len(self.responses)]
        self._index += 1
        return response

    def generate_stream(self, messages: list[dict]) -> Iterator[str]:
        response = self.generate(messages)
        for ch in response:
            yield ch
