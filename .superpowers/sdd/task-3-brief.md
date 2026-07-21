# Task 3: LLMAdapter Abstraction

**Files:**
- Create: `src/ai4se_agent/llm/__init__.py`
- Create: `src/ai4se_agent/llm/base.py`
- Create: `src/ai4se_agent/llm/openai_adapter.py`
- Create: `src/ai4se_agent/llm/mock_adapter.py`
- Create: `tests/llm/__init__.py`
- Create: `tests/llm/test_adapters.py`

**Interfaces:**
- Consumes: Nothing from this project
- Produces: `LLMAdapter` ABC, `OpenAIAdapter`, `MockAdapter` consumed by state machine

## Step 1: Write the failing test

```python
# tests/llm/test_adapters.py
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
```

## Step 2: Run test to verify it fails

Run: `pytest tests/llm/test_adapters.py -v`
Expected: FAIL

## Step 3: Write minimal implementation

```python
# src/ai4se_agent/llm/base.py
from abc import ABC, abstractmethod


class LLMAdapter(ABC):
    @abstractmethod
    def generate(self, messages: list[dict]) -> str:
        pass
```

```python
# src/ai4se_agent/llm/openai_adapter.py
from openai import OpenAI
from ai4se_agent.llm.base import LLMAdapter


class OpenAIAdapter(LLMAdapter):
    def __init__(self, api_key: str, base_url: str = None, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def generate(self, messages: list[dict]) -> str:
        response = self.client.chat.completions.create(
            model=self.model, messages=messages
        )
        return response.choices[0].message.content
```

```python
# src/ai4se_agent/llm/mock_adapter.py
from ai4se_agent.llm.base import LLMAdapter


class MockAdapter(LLMAdapter):
    def __init__(self, responses: list[str]):
        self.responses = responses
        self._index = 0

    def generate(self, messages: list[dict]) -> str:
        response = self.responses[self._index % len(self.responses)]
        self._index += 1
        return response
```

## Step 4: Run tests

Run: `pytest tests/llm/test_adapters.py -v`
Expected: PASS

## Step 5: Commit

```bash
git add src/ai4se_agent/llm/ tests/llm/
git commit -m "feat: add LLMAdapter abstraction with OpenAI and Mock adapters"
```

## Global Constraints

- Python >=3.10
- openai >=1.0.0 (direct dependency, used via LLMAdapter)
- All core mechanisms must be testable with mock LLM (no network, no real LLM)
- No use of agent orchestration frameworks
- Tests in `tests/` mirroring `src/` structure
- No comments in code unless specified
