from typing import Any, Optional
from openai import OpenAI
from ai4se_agent.llm.base import LLMAdapter


class OpenAIAdapter(LLMAdapter):
    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def generate(self, messages: list[dict]) -> str:
        response = self.client.chat.completions.create(
            model=self.model, messages=messages  # type: ignore[arg-type]
        )
        content: Any = response.choices[0].message.content
        return content if content is not None else ""
