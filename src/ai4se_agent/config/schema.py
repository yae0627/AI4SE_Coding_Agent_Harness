from dataclasses import dataclass, field


@dataclass
class ProviderConfig:
    name: str = "openai"
    api_key: str = ""
    base_url: str = ""


@dataclass
class ModelConfig:
    active: str = ""


@dataclass
class AgentConfig:
    max_iterations: int = 20


@dataclass
class AppConfig:
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)

    def to_dict(self) -> dict:
        return {
            "provider": {
                "name": self.provider.name,
                "api_key": self.provider.api_key,
                "base_url": self.provider.base_url,
            },
            "model": {
                "active": self.model.active,
            },
            "agent": {
                "max_iterations": self.agent.max_iterations,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        provider = data.get("provider", {})
        model = data.get("model", {})
        agent = data.get("agent", {})
        return cls(
            provider=ProviderConfig(
                name=provider.get("name", "openai"),
                api_key=provider.get("api_key", ""),
                base_url=provider.get("base_url", ""),
            ),
            model=ModelConfig(
                active=model.get("active", ""),
            ),
            agent=AgentConfig(
                max_iterations=agent.get("max_iterations", 20),
            ),
        )
