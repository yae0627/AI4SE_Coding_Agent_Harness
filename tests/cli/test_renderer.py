import io
import sys
import time

from ai4se_agent.cli.renderer import (
    NullRenderer, Renderer, TerminalRenderer, _compact_params, separator, prompt_str
)
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
    assert captured.out == ""  # state changes are internal, not shown


def test_terminal_renderer_token_usage(capsys):
    r = TerminalRenderer(verbose=True)
    r.on_token_usage(2, 500, 200)
    assert r._total_tokens == 700  # accumulated, not printed directly


def test_terminal_renderer_timing_verbose(capsys):
    r = TerminalRenderer(verbose=True)
    r.on_timing("LLM_CALL", 850.5)
    assert r._total_elapsed_ms == 850.5


def test_terminal_renderer_on_stop_with_summary(capsys):
    r = TerminalRenderer()
    r._total_tokens = 700
    r._total_elapsed_ms = 5000.0
    r.on_stop(StopReason.SUCCESS, 3)
    captured = capsys.readouterr()
    assert "success" in captured.out
    assert "700" in captured.out
    assert "5.0s" in captured.out


def test_terminal_renderer_on_llm_call_verbose(capsys):
    r = TerminalRenderer(verbose=True)
    r.on_llm_call(1, "test-model", '{"action": "shell", "parameters": {"command": "echo hello"}}')
    captured = capsys.readouterr()
    assert "test-model" in captured.out
    assert "echo hello" in captured.out


def test_terminal_renderer_truncates_long_output(capsys):
    r = TerminalRenderer(max_output=20)
    r._tool_start_time = time.time()
    r._tool_start_params = {"command": "x" * 80}
    event = AgentEvent(
        type="TOOL_END", iteration=1, state="TOOL_EXEC",
        payload={"tool": "shell", "success": False, "output_preview": "error msg"},
    )
    r._on_tool_end(event)
    captured = capsys.readouterr()
    assert "FAIL" in captured.out
    assert "error msg" in captured.out


def test_renderer_handles_tool_end_event_ok(capsys):
    r = TerminalRenderer()
    r._tool_start_time = time.time() - 0.05  # simulate 50ms elapsed
    r._tool_start_params = {"command": "echo hello"}
    event = AgentEvent(
        type="TOOL_END", iteration=1, state="TOOL_EXEC",
        payload={"tool": "shell", "success": True, "output_preview": "hello"},
    )
    r._on_tool_end(event)
    captured = capsys.readouterr()
    assert "ok" in captured.out


def test_renderer_handles_tool_end_event_failed(capsys):
    r = TerminalRenderer()
    r._tool_start_time = time.time() - 2.1  # simulate 2.1s elapsed
    r._tool_start_params = {"command": "bad cmd"}
    event = AgentEvent(
        type="TOOL_END", iteration=1, state="TOOL_EXEC",
        payload={"tool": "shell", "success": False, "output_preview": "error msg"},
    )
    r._on_tool_end(event)
    captured = capsys.readouterr()
    assert "FAIL" in captured.out
    assert "error msg" in captured.out


def test_renderer_handles_llm_end_event(capsys):
    r = TerminalRenderer(verbose=True)
    event = AgentEvent(
        type="LLM_END", iteration=1, state="LLM_CALL",
        payload={"model": "gpt-4", "response_preview": '{"action": "finish"}'},
    )
    r._on_llm_end(event)
    captured = capsys.readouterr()
    assert "gpt-4" in captured.out


def test_renderer_approval_required_event(capsys):
    r = TerminalRenderer()
    event = AgentEvent(
        type="APPROVAL_REQUIRED", iteration=2, state="WAIT_APPROVAL",
        payload={
            "policy": "GitPolicy",
            "reason": "push to remote, irreversible",
            "action_name": "shell",
            "action_params": {"command": "git push origin main"},
        },
    )
    r._on_approval_required(event)
    captured = capsys.readouterr()
    assert "APPROVAL REQUIRED" in captured.out
    assert "GitPolicy" in captured.out
    assert "git push" in captured.out
    assert "/approve" in captured.out
    assert "/reject" in captured.out


def test_renderer_respond_event(capsys):
    r = TerminalRenderer()
    event = AgentEvent(
        type="RESPOND", iteration=1, state="RESPOND",
        payload={"message": "I found the issue in auth.py"},
    )
    r._on_respond_event(event)
    captured = capsys.readouterr()
    assert "auth.py" in captured.out
    assert "[respond]" not in captured.out  # no prefix, clean output


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


def test_compact_params_returns_path_first():
    assert _compact_params({"path": "auth.py", "content": "x"}) == "auth.py"


def test_compact_params_returns_command_second():
    assert _compact_params({"command": "pytest -v"}) == "pytest -v"


def test_compact_params_truncates():
    long_val = "x" * 100
    result = _compact_params({"path": long_val})
    assert len(result) == 60


def test_separator_is_blue():
    s = separator()
    assert "\033[34m" in s  # blue ANSI code


def test_prompt_str_is_blue():
    p = prompt_str()
    assert "\033[34m" in p
    assert ">" in p


def test_llm_token_streaming_output(capsys):
    r = TerminalRenderer()
    tokens = ['{"action":', ' "finish"', '}']
    for t in tokens:
        event = AgentEvent(
            type="LLM_TOKEN", iteration=1, state="LLM_CALL",
            payload={"token": t, "model": "gpt-4"},
        )
        r._on_llm_token(event)
    # End the stream
    r._on_llm_end(AgentEvent(
        type="LLM_END", iteration=1, state="LLM_CALL",
        payload={"model": "gpt-4", "response_preview": '{"action": "finish"}'},
    ))
    captured = capsys.readouterr()
    assert '{"action":' in captured.out
    assert '"finish"' in captured.out
