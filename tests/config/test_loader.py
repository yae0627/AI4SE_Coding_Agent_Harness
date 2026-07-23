from ai4se_agent.config.loader import ConfigLoader


def test_config_returns_defaults():
    loader = ConfigLoader()
    cfg = loader.load()
    assert cfg.provider.name == "openai"


def test_config_env_override(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    loader = ConfigLoader()
    cfg = loader.load()
    assert cfg.provider.api_key == "test-key-123"
    assert cfg.model.active == "gpt-4o"


def test_config_set_and_get():
    loader = ConfigLoader()
    loader.set("model", "active", "deepseek-v4")
    assert loader.get("model", "active") == "deepseek-v4"


def test_config_provider_env_override(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    loader = ConfigLoader()
    cfg = loader.load()
    assert cfg.provider.name == "mock"


def test_config_merge_priority(monkeypatch):
    """Env vars should take priority over defaults."""
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    loader = ConfigLoader()
    cfg = loader.load()
    assert cfg.provider.api_key == "env-key"
