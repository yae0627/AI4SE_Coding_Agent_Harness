from openai import OpenAI
from ai4se_agent.llm.base import LLMAdapter


class OpenAIAdapter(LLMAdapter):
    def __init__(self, api_key: str, base_url: str = None, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def generate(self, messages: list[dict]) -> str:
        response = self.client.chat.completions.create(
            model=self.model, messages=messages
        )
        return response.choices[0].message.content
