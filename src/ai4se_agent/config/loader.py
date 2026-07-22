import os
from pathlib import Path


class ConfigLoader:
    def __init__(self, env_file: str = ".env"):
        self._env_file = Path(env_file)
        self._load_env_file()

    def _load_env_file(self) -> None:
        if self._env_file.exists():
            for line in self._env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())

    def get(self, key: str, default: str | None = None) -> str | None:
        env_map = {
            "api_key": "OPENAI_API_KEY",
            "base_url": "OPENAI_BASE_URL",
            "model": "OPENAI_MODEL",
            "provider": "LLM_PROVIDER",
            "local_model_url": "LOCAL_MODEL_URL",
            "local_model_name": "LOCAL_MODEL_NAME",
        }
        env_key = env_map.get(key, key.upper())
        return os.environ.get(env_key, default)

    def get_provider(self) -> str:
        return self.get("provider") or "openai"
