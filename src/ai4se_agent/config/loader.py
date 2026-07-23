import os
import sys
from pathlib import Path

from ai4se_agent.config.schema import AppConfig

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]


def _user_config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", str(Path.home()))
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(base) / "ai4se"


def _serialize_toml(config: AppConfig) -> str:
    """Write a minimal TOML representation of AppConfig."""
    d = config.to_dict()
    lines: list[str] = []

    provider = d["provider"]
    lines.append("[provider]")
    lines.append(f'name = "{provider["name"]}"')
    lines.append(f'api_key = "{provider["api_key"]}"')
    lines.append(f'base_url = "{provider["base_url"]}"')
    lines.append("")

    model = d["model"]
    lines.append("[model]")
    lines.append(f'active = "{model["active"]}"')
    lines.append("")

    agent = d["agent"]
    lines.append("[agent]")
    lines.append(f"max_iterations = {agent['max_iterations']}")
    lines.append("")

    return "\n".join(lines)


def _parse_toml(path: Path) -> dict | None:
    if tomllib is None:
        return None
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return None


class ConfigLoader:
    def __init__(self) -> None:
        self._user_dir = _user_config_dir()
        self._user_config_path = self._user_dir / "config.toml"
        self._config: AppConfig = AppConfig()
        self._loaded = False

    def load(self) -> AppConfig:
        if self._loaded:
            return self._config

        merged = AppConfig()

        # Layer 1: Package defaults (lowest priority)
        pkg_config = self._load_package_config()
        merged = self._merge(merged, pkg_config)

        # Layer 2: User config (~/.config/ai4se/config.toml)
        user_config = self._load_user_config()
        merged = self._merge(merged, user_config)

        # Layer 3: Project config (./ai4se.toml)
        project_config = self._load_project_config()
        merged = self._merge(merged, project_config)

        # Layer 4: Environment variables (highest priority)
        self._apply_env_overrides(merged)

        self._config = merged
        self._loaded = True
        return self._config

    def save(self) -> None:
        self._user_dir.mkdir(parents=True, exist_ok=True)
        content = _serialize_toml(self._config)
        self._user_config_path.write_text(content, encoding="utf-8")

    def set(self, section: str, key: str, value: str | int) -> None:
        self.load()
        if section == "provider":
            if key == "name":
                self._config.provider.name = str(value)
            elif key == "api_key":
                self._config.provider.api_key = str(value)
            elif key == "base_url":
                self._config.provider.base_url = str(value)
        elif section == "model":
            if key == "active":
                self._config.model.active = str(value)
        elif section == "agent":
            if key == "max_iterations":
                self._config.agent.max_iterations = int(value)

    def get(self, section: str, key: str) -> str | int:
        self.load()
        if section == "provider":
            obj = self._config.provider
        elif section == "model":
            obj = self._config.model
        elif section == "agent":
            obj = self._config.agent
        else:
            return ""
        return getattr(obj, key, "")

    def reload(self) -> AppConfig:
        self._loaded = False
        return self.load()

    @property
    def user_dir(self) -> Path:
        return self._user_dir

    def _load_package_config(self) -> AppConfig:
        pkg_path = Path(__file__).resolve().parent.parent.parent / "config.toml"
        data = _parse_toml(pkg_path)
        return AppConfig.from_dict(data) if data else AppConfig()

    def _load_user_config(self) -> AppConfig:
        data = _parse_toml(self._user_config_path)
        return AppConfig.from_dict(data) if data else AppConfig()

    def _load_project_config(self) -> AppConfig:
        project_path = Path.cwd() / "ai4se.toml"
        data = _parse_toml(project_path)
        return AppConfig.from_dict(data) if data else AppConfig()

    @staticmethod
    def _apply_env_overrides(config: AppConfig) -> None:
        for env_key, attr in [
            ("LLM_PROVIDER", "name"),
            ("OPENAI_API_KEY", "api_key"),
            ("OPENAI_BASE_URL", "base_url"),
        ]:
            val = os.environ.get(env_key)
            if val:
                setattr(config.provider, attr, val)
        val = os.environ.get("OPENAI_MODEL")
        if val:
            config.model.active = val

    @staticmethod
    def _merge(base: AppConfig, overlay: AppConfig) -> AppConfig:
        """Merge overlay into base, keeping non-empty values from overlay."""
        if overlay.provider.name:
            base.provider.name = overlay.provider.name
        if overlay.provider.api_key:
            base.provider.api_key = overlay.provider.api_key
        if overlay.provider.base_url:
            base.provider.base_url = overlay.provider.base_url
        if overlay.model.active:
            base.model.active = overlay.model.active
        if overlay.agent.max_iterations != 20:
            base.agent.max_iterations = overlay.agent.max_iterations
        return base
