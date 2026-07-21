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
