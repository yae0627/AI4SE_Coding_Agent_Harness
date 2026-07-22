import importlib.util
from pathlib import Path

from ai4se_agent.cli.renderer import NullRenderer, Renderer, TerminalRenderer

__all__ = [
    "Renderer",
    "NullRenderer",
    "TerminalRenderer",
    "build_harness",
    "main",
]

_legacy_path = Path(__file__).resolve().parent.parent / "cli.py"
if _legacy_path.exists():
    _spec = importlib.util.spec_from_file_location(
        "_ai4se_agent_legacy_cli", _legacy_path
    )
    if _spec is not None and _spec.loader is not None:
        _legacy = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_legacy)
        build_harness = _legacy.build_harness
        main = _legacy.main
