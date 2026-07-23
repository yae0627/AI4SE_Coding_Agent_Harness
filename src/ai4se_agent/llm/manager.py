from ai4se_agent.config.loader import ConfigLoader
from ai4se_agent.llm.base import LLMAdapter
from ai4se_agent.llm.mock_adapter import MockAdapter
from ai4se_agent.llm.openai_adapter import OpenAIAdapter


class LLMManager:
    def __init__(self, config: ConfigLoader):
        self._config = config
        self._adapter: LLMAdapter | None = None

    def get_adapter(self) -> LLMAdapter:
        if self._adapter is None:
            self._adapter = self._build()
        return self._adapter

    def switch_model(self, model: str) -> None:
        self._config.set("model", "active", model)
        self._config.save()
        self._adapter = self._build()

    def reload(self) -> LLMAdapter:
        self._config.reload()
        self._adapter = self._build()
        return self._adapter

    def _build(self) -> LLMAdapter:
        cfg = self._config.load()
        provider = cfg.provider.name
        if provider == "mock":
            return MockAdapter(
                responses=[
                    '{"action": "shell", "parameters": {"command": "echo hello"}}',
                    '{"action": "finish", "parameters": {}}',
                ]
            )
        return OpenAIAdapter(
            api_key=cfg.provider.api_key,
            base_url=cfg.provider.base_url or None,
            model=cfg.model.active,
        )
