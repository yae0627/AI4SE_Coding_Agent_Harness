from ai4se_agent.config.loader import ConfigLoader

def test_config_returns_defaults():
    loader = ConfigLoader()
    assert loader.get("provider", "openai") == "openai"

def test_config_accepts_env_override(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    loader = ConfigLoader()
    assert loader.get("api_key") == "test-key-123"
