from typing import Any
from openai import OpenAI
from ai4se_agent.llm.base import LLMAdapter


class LocalAdapter(LLMAdapter):
    def __init__(self, base_url: str, model: str = "local-model"):
        self.client = OpenAI(api_key="not-needed", base_url=base_url)
        self.model = model

    def generate(self, messages: list[dict]) -> str:
        response = self.client.chat.completions.create(
            model=self.model, messages=messages  # type: ignore[arg-type]
        )
        content: Any = response.choices[0].message.content
        return content if content is not None else ""