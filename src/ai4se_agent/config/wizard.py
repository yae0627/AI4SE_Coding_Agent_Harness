from ai4se_agent.config.loader import ConfigLoader


def _input_default(prompt: str, default: str = "") -> str:
    if default:
        result = input(f"{prompt} [{default}]: ").strip()
        return result if result else default
    return input(f"{prompt}: ").strip()


def run_setup_wizard(config: ConfigLoader) -> None:
    print("AI4SE Agent — First Time Setup")
    print("=" * 40)
    print()

    # Provider
    print("Provider configuration:")
    name = _input_default("  Provider name", "openai")
    base_url = _input_default("  Base URL", "https://api.openai.com/v1")
    api_key = _input_default("  API Key", "")
    print()

    if not api_key:
        print("Warning: No API key provided. Use mock provider or set key later with:")
        print('  /config set provider api_key "sk-..."')
        print()

    # Test connection + discover models
    model = ""
    if api_key and base_url:
        model = _discover_models(base_url, api_key)

    if not model:
        model = _input_default("Default model", "gpt-4o")

    config.set("provider", "name", name)
    config.set("provider", "base_url", base_url)
    config.set("provider", "api_key", api_key)
    config.set("model", "active", model)
    config.save()

    print()
    print(f"Configuration saved to: {config._user_config_path}")
    print(f"Model: {model}")
    print("You can change settings anytime with /config set <section> <key> <value>")
    print()


def _discover_models(base_url: str, api_key: str) -> str:
    print("Testing connection...")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        models = client.models.list()
        model_ids = [m.id for m in models]
        # Filter to chat-capable models
        chat_models = [m for m in model_ids if not m.startswith(("embedding", "dall-e", "tts", "whisper", "moderation"))]
        if not chat_models:
            chat_models = model_ids

        print("✓ API reachable")
        print()
        print("Available models:")
        for i, m in enumerate(chat_models[:20], 1):
            print(f"  {i:2d}. {m}")

        print()
        choice = _input_default("Select default model (number or name)", chat_models[0])
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(chat_models):
                return chat_models[idx]
        except ValueError:
            if choice in chat_models:
                return choice
        return chat_models[0]
    except Exception as e:
        print(f"✗ Could not reach API: {e}")
        print()
        return ""
