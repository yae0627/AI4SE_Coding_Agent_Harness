from ai4se_agent.llm.base import LLMAdapter
from ai4se_agent.llm.mock_adapter import MockAdapter

def test_mock_adapter_returns_preset():
    adapter = MockAdapter(responses=["action: write_file path=test.txt"])
    result = adapter.generate([{"role": "user", "content": "hello"}])
    assert result == "action: write_file path=test.txt"

def test_mock_adapter_cycles():
    adapter = MockAdapter(responses=["first", "second"])
    assert adapter.generate([]) == "first"
    assert adapter.generate([]) == "second"

def test_adapter_is_abstract():
    import inspect
    assert inspect.isabstract(LLMAdapter)


def test_mock_stream_yields_characters():
    adapter = MockAdapter(responses=['{"action": "finish"}'])
    tokens = list(adapter.generate_stream([{"role": "user", "content": "hi"}]))
    assert len(tokens) > 1
    assert "".join(tokens) == '{"action": "finish"}'


def test_mock_stream_cycles():
    adapter = MockAdapter(responses=["AB", "CD"])
    first = "".join(adapter.generate_stream([]))
    second = "".join(adapter.generate_stream([]))
    assert first == "AB"
    assert second == "CD"


def test_default_stream_returns_entire_response():
    """LLMAdapter default generate_stream yields entire response."""
    adapter = MockAdapter(responses=["hello"])
    result = list(adapter.generate_stream([]))
    assert result == list("hello")
