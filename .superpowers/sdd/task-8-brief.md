# Task 8: Configuration

**Files:**
- Create: `src/ai4se_agent/config/loader.py`
- Create: `tests/config/test_loader.py`

**Interfaces:**
- Consumes: Nothing from this project
- Produces: `ConfigLoader` consumed by CLI entry point

## Step 1: Write the failing test

```python
# tests/config/test_loader.py
from ai4se_agent.config.loader import ConfigLoader

def test_config_returns_defaults():
    loader = ConfigLoader()
    assert loader.get("provider", "openai") == "openai"

def test_config_accepts_env_override(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    loader = ConfigLoader()
    assert loader.get("api_key") == "test-key-123"
```

## Step 2: Run test

Run: `pytest tests/config/test_loader.py -v`
Expected: FAIL

## Step 3: Write minimal implementation

```python
# src/ai4se_agent/config/loader.py
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
            "provider": "LLM_PROVIDER",
            "local_model_url": "LOCAL_MODEL_URL",
            "local_model_name": "LOCAL_MODEL_NAME",
        }
        env_key = env_map.get(key, key.upper())
        return os.environ.get(env_key, default)

    def get_provider(self) -> str:
        return self.get("provider", "openai")
```

## Step 4: Run tests

Run: `pytest tests/config/test_loader.py -v`
Expected: PASS

## Step 5: Commit

```bash
git add src/ai4se_agent/config/ tests/config/
git commit -m "feat: add ConfigLoader with .env support"
```

## Global Constraints

- Python >=3.10
- All API keys via .env file, never hardcoded
- All core mechanisms must be testable with mock LLM (no network, no real LLM)
- No use of agent orchestration frameworks
- Tests in `tests/` mirroring `src/` structure
- No comments in code unless specified
