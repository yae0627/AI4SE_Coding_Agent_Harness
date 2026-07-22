from ai4se_agent.cli.commands import handle_command
from ai4se_agent.cli.renderer import NullRenderer, TerminalRenderer
from ai4se_agent.cli.session import SessionManager
from ai4se_agent.observability.tracer import NullTracer


def test_session_start_returns_none():
    session = SessionManager(renderer=NullRenderer(), tracer=NullTracer())
    result = session.start()
    assert result is None


def test_session_submit_task(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    session = SessionManager(renderer=NullRenderer(), tracer=NullTracer())
    result = session.submit("echo hello")
    assert result is not None
    assert "status" in result


def test_handle_command_exit_returns_false():
    session = SessionManager(renderer=NullRenderer(), tracer=NullTracer())
    assert handle_command("exit", session) is False


def test_handle_command_quit_returns_false():
    session = SessionManager(renderer=NullRenderer(), tracer=NullTracer())
    assert handle_command("quit", session) is False


def test_handle_command_status_with_state(capsys):
    session = SessionManager(renderer=NullRenderer(), tracer=NullTracer())
    session.state = type(session.state or object())()  # placeholder
    from ai4se_agent.core.agent_state import AgentState

    session.state = AgentState(goal="demo")
    handle_command("/status", session)
    captured = capsys.readouterr()
    assert "State:" in captured.out
    assert "Iteration:" in captured.out


def test_handle_command_verbose_toggles(capsys):
    session = SessionManager(renderer=TerminalRenderer(verbose=False), tracer=NullTracer())
    handle_command("/verbose", session)
    captured = capsys.readouterr()
    assert "Verbose mode: on" in captured.out
    handle_command("/verbose", session)
    captured = capsys.readouterr()
    assert "Verbose mode: off" in captured.out
