from collections.abc import Callable
from typing import Any

# ── Command registry ──────────────────────────────────────────
# Each entry: (name, description, handler)
# Handler signature: (parts: list[str], session: Any) -> bool (True = keep session)
CommandEntry = tuple[str, str, Callable[..., bool]]

def _cmd_status(parts: list[str], session: Any) -> bool:
    if session.state is not None:
        print(f"State: {session.state.current_state}")
        print(f"Iteration: {session.state.iteration}")
    else:
        print("No active session")
    return True

def _cmd_reset(parts: list[str], session: Any) -> bool:
    session.state = None
    print("Session reset")
    return True

def _cmd_verbose(parts: list[str], session: Any) -> bool:
    if hasattr(session, "_renderer") and hasattr(session._renderer, "_verbose"):
        session._renderer._verbose = not session._renderer._verbose
        print(f"Verbose mode: {'on' if session._renderer._verbose else 'off'}")
    return True

def _cmd_config(parts: list[str], session: Any) -> bool:
    if len(parts) >= 4 and parts[1] == "set":
        section = parts[2]
        key = parts[3]
        value = " ".join(parts[4:]) if len(parts) > 4 else ""
        value = value.strip().strip('"').strip("'")
        session._config.set(section, key, value)
        session._config.save()
        print(f"Set {section}.{key} = {value}")
        print("Restart harness or next task will use new config.")
        return True
    cfg = session._config.load()
    print(f"Provider: {cfg.provider.name}")
    print(f"  Base URL: {cfg.provider.base_url}")
    print(f"  API Key:  {'***' + cfg.provider.api_key[-4:] if cfg.provider.api_key else '(not set)'}")
    print(f"Model: {cfg.model.active or '(not set)'}")
    print(f"Max Iterations: {cfg.agent.max_iterations}")
    print()
    print("Change settings: /config set <section> <key> <value>")
    print("  Sections: provider, model, agent")
    print('  Examples:')
    print('    /config set model active gpt-4o')
    print('    /config set provider base_url https://api.openai.com/v1')
    return True

def _cmd_models(parts: list[str], session: Any) -> bool:
    cfg = session._config.load()
    if not cfg.provider.api_key or not cfg.provider.base_url:
        print("No API configured. Run setup first.")
        return True
    try:
        from openai import OpenAI
        client = OpenAI(api_key=cfg.provider.api_key, base_url=cfg.provider.base_url)
        models = client.models.list()
        model_ids = [m.id for m in models]
        chat_models = [m for m in model_ids if not m.startswith(("embedding", "dall-e", "tts", "whisper", "moderation"))]
        if not chat_models:
            chat_models = model_ids
        current = cfg.model.active
        print("Available models:")
        for m in chat_models[:30]:
            marker = " *" if m == current else "  "
            print(f"  {marker} {m}")
        print()
        print(f"Current: {current}")
        print("Switch: /config set model active <name>")
    except Exception as e:
        print(f"Failed to list models: {e}")
    return True

def _cmd_help(parts: list[str], session: Any) -> bool:
    print("Commands:")
    for name, desc, _ in COMMANDS:
        print(f"  {name:<12s} {desc}")
    return True

COMMANDS: list[CommandEntry] = [
    ("/help",    "show this help",               _cmd_help),
    ("exit",     "quit the session (no / needed)", lambda p, s: False),
    ("/status",  "show agent state and iteration", _cmd_status),
    ("/reset",   "clear current session",        _cmd_reset),
    ("/verbose", "toggle detailed output mode",  _cmd_verbose),
    ("/config",  "view or change settings",      _cmd_config),
    ("/models",  "list available API models",    _cmd_models),
]


def handle_command(line: str, session: Any) -> bool:
    """Dispatch a slash command. Returns True to keep session, False to exit."""
    parts = line.strip().split()
    name = parts[0].lower() if parts else ""

    if name in ("exit", "quit"):
        return False

    for cmd_name, _desc, handler in COMMANDS:
        if cmd_name == name:
            return handler(parts, session)

    print(f"Unknown command: {line}")
    return True


def matching_commands(prefix: str) -> list[tuple[str, str]]:
    """Return (name, description) for commands whose name starts with prefix."""
    if not prefix.startswith("/"):
        return []
    return [(name, desc) for name, desc, _ in COMMANDS if name.startswith(prefix)]
