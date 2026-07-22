from ai4se_agent.cli.renderer import NullRenderer
from ai4se_agent.cli.session import SessionManager
from ai4se_agent.observability.tracer import NullTracer


def test_session_submit_with_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    session = SessionManager(renderer=NullRenderer(), tracer=NullTracer())
    result = session.submit("test task")
    assert result is not None
    assert "status" in result
