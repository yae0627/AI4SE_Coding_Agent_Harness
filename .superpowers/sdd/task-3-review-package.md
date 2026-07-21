diff --git a/src/ai4se_agent/llm/__init__.py b/src/ai4se_agent/llm/__init__.py
new file mode 100644
index 0000000..e69de29
diff --git a/src/ai4se_agent/llm/base.py b/src/ai4se_agent/llm/base.py
new file mode 100644
index 0000000..5e33764
--- /dev/null
+++ b/src/ai4se_agent/llm/base.py
@@ -0,0 +1,7 @@
+from abc import ABC, abstractmethod
+
+
+class LLMAdapter(ABC):
+    @abstractmethod
+    def generate(self, messages: list[dict]) -> str:
+        pass
diff --git a/src/ai4se_agent/llm/mock_adapter.py b/src/ai4se_agent/llm/mock_adapter.py
new file mode 100644
index 0000000..0a5ebba
--- /dev/null
+++ b/src/ai4se_agent/llm/mock_adapter.py
@@ -0,0 +1,12 @@
+from ai4se_agent.llm.base import LLMAdapter
+
+
+class MockAdapter(LLMAdapter):
+    def __init__(self, responses: list[str]):
+        self.responses = responses
+        self._index = 0
+
+    def generate(self, messages: list[dict]) -> str:
+        response = self.responses[self._index % len(self.responses)]
+        self._index += 1
+        return response
diff --git a/src/ai4se_agent/llm/openai_adapter.py b/src/ai4se_agent/llm/openai_adapter.py
new file mode 100644
index 0000000..cb7227d
--- /dev/null
+++ b/src/ai4se_agent/llm/openai_adapter.py
@@ -0,0 +1,14 @@
+from openai import OpenAI
+from ai4se_agent.llm.base import LLMAdapter
+
+
+class OpenAIAdapter(LLMAdapter):
+    def __init__(self, api_key: str, base_url: str = None, model: str = "gpt-4o"):
+        self.client = OpenAI(api_key=api_key, base_url=base_url)
+        self.model = model
+
+    def generate(self, messages: list[dict]) -> str:
+        response = self.client.chat.completions.create(
+            model=self.model, messages=messages
+        )
+        return response.choices[0].message.content
diff --git a/tests/llm/__init__.py b/tests/llm/__init__.py
new file mode 100644
index 0000000..e69de29
diff --git a/tests/llm/test_adapters.py b/tests/llm/test_adapters.py
new file mode 100644
index 0000000..a0347bc
--- /dev/null
+++ b/tests/llm/test_adapters.py
@@ -0,0 +1,16 @@
+from ai4se_agent.llm.base import LLMAdapter
+from ai4se_agent.llm.mock_adapter import MockAdapter
+
+def test_mock_adapter_returns_preset():
+    adapter = MockAdapter(responses=["action: write_file path=test.txt"])
+    result = adapter.generate([{"role": "user", "content": "hello"}])
+    assert result == "action: write_file path=test.txt"
+
+def test_mock_adapter_cycles():
+    adapter = MockAdapter(responses=["first", "second"])
+    assert adapter.generate([]) == "first"
+    assert adapter.generate([]) == "second"
+
+def test_adapter_is_abstract():
+    import inspect
+    assert inspect.isabstract(LLMAdapter)
