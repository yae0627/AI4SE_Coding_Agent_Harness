from ai4se_agent.cli.renderer import NullRenderer, Renderer, TerminalRenderer
from ai4se_agent.types import StopReason, ToolResult


def test_null_renderer_does_nothing():
    r = NullRenderer()
    r.on_state_change("IDLE", "CONTEXT_ORG", 1)
    r.on_token_usage(1, 100, 50)
    r.on_timing("LLM_CALL", 123.4)
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


def test_terminal_renderer_token_usage(capsys):
    r = TerminalRenderer(verbose=True)
    r.on_token_usage(2, 500, 200)
    captured = capsys.readouterr()
    assert "500" in captured.out
    assert "200" in captured.out


def test_terminal_renderer_timing_verbose(capsys):
    r = TerminalRenderer(verbose=True)
    r.on_timing("LLM_CALL", 850.5)
    captured = capsys.readouterr()
    assert "LLM_CALL" in captured.out
    assert "850" in captured.out


def test_terminal_renderer_timing_non_verbose(capsys):
    r = TerminalRenderer(verbose=False)
    r.on_timing("LLM_CALL", 850.5)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_terminal_renderer_on_stop_with_summary(capsys):
    r = TerminalRenderer()
    r._total_tokens = 700
    r._total_elapsed_ms = 5000.0
    r.on_stop(StopReason.SUCCESS, 3)
    captured = capsys.readouterr()
    assert "success" in captured.out
    assert "700" in captured.out


def test_terminal_renderer_on_llm_call_verbose(capsys):
    r = TerminalRenderer(verbose=True)
    r.on_llm_call(1, "test-model", '{"action": "shell", "parameters": {"command": "echo hello"}}')
    captured = capsys.readouterr()
    assert "test-model" in captured.out
    assert "echo hello" in captured.out


def test_terminal_renderer_truncates_long_output(capsys):
    r = TerminalRenderer(max_output=20)
    result = ToolResult(success=False, output="a" * 100, error="err")
    r.on_tool_exec(1, "shell", result)
    captured = capsys.readouterr()
    last_line = captured.out.splitlines()[-1] if captured.out.splitlines() else ""
    assert len(last_line) <= 60
