from ai4se_agent.cli.renderer import NullRenderer, Renderer, TerminalRenderer
from ai4se_agent.types import StopReason


def test_null_renderer_does_nothing():
    r = NullRenderer()
    r.on_state_change("IDLE", "CONTEXT_ORG", 1)
    r.on_stop(StopReason.SUCCESS, 3)


def test_renderer_is_abstract():
    import inspect

    assert inspect.isabstract(Renderer)


def test_terminal_renderer_creates(capsys):
    r = TerminalRenderer()
    r.on_state_change("IDLE", "CONTEXT_ORG", 1)
    captured = capsys.readouterr()
    assert "[CONTEXT_ORG]" in captured.out
    assert "Iteration 1" in captured.out
