import io
import sys

from ai4se_agent.cli.renderer import NullRenderer, Renderer, TerminalRenderer
from ai4se_agent.core.events import AgentEvent
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


def test_renderer_handles_tool_start_event(capsys):
    r = TerminalRenderer()
    event = AgentEvent(
        type="TOOL_START", iteration=1, state="TOOL_EXEC",
        payload={"tool": "shell", "parameters": {"command": "echo hello"}},
    )
    r._on_tool_start(event)
    # _on_tool_start is currently a no-op (action shown by _on_action_created)


def test_renderer_handles_tool_end_event_ok(capsys):
    r = TerminalRenderer()
    event = AgentEvent(
        type="TOOL_END", iteration=1, state="TOOL_EXEC",
        payload={"tool": "shell", "success": True, "output_preview": "hello"},
    )
    r._on_tool_end(event)
    captured = capsys.readouterr()
    assert "OK" in captured.out


def test_renderer_handles_tool_end_event_failed(capsys):
    r = TerminalRenderer()
    event = AgentEvent(
        type="TOOL_END", iteration=1, state="TOOL_EXEC",
        payload={"tool": "shell", "success": False, "output_preview": "error msg"},
    )
    r._on_tool_end(event)
    captured = capsys.readouterr()
    assert "FAILED" in captured.out


def test_renderer_handles_llm_end_event(capsys):
    r = TerminalRenderer(verbose=True)
    event = AgentEvent(
        type="LLM_END", iteration=1, state="LLM_CALL",
        payload={"model": "gpt-4", "response_preview": '{"action": "finish"}'},
    )
    r._on_llm_end(event)
    captured = capsys.readouterr()
    assert "gpt-4" in captured.out


def test_renderer_subscribe_registers_handlers():
    from ai4se_agent.core.event_bus import EventBus
    bus = EventBus()
    TerminalRenderer(event_bus=bus)
    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        bus.publish(AgentEvent(
            type="AGENT_STOP", iteration=3, state="STOP",
            payload={"reason": "success", "iterations": 3}
        ))
        output = captured.getvalue()
        assert "success" in output
    finally:
        sys.stdout = old_stdout
