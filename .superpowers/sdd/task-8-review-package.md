diff --git a/src/ai4se_agent/config/loader.py b/src/ai4se_agent/config/loader.py
new file mode 100644
index 0000000..ac580a3
--- /dev/null
+++ b/src/ai4se_agent/config/loader.py
@@ -0,0 +1,30 @@
+import os
+from pathlib import Path
+
+
+class ConfigLoader:
+    def __init__(self, env_file: str = ".env"):
+        self._env_file = Path(env_file)
+        self._load_env_file()
+
+    def _load_env_file(self) -> None:
+        if self._env_file.exists():
+            for line in self._env_file.read_text(encoding="utf-8").splitlines():
+                line = line.strip()
+                if line and not line.startswith("#") and "=" in line:
+                    key, _, value = line.partition("=")
+                    os.environ.setdefault(key.strip(), value.strip())
+
+    def get(self, key: str, default: str | None = None) -> str | None:
+        env_map = {
+            "api_key": "OPENAI_API_KEY",
+            "base_url": "OPENAI_BASE_URL",
+            "provider": "LLM_PROVIDER",
+            "local_model_url": "LOCAL_MODEL_URL",
+            "local_model_name": "LOCAL_MODEL_NAME",
+        }
+        env_key = env_map.get(key, key.upper())
+        return os.environ.get(env_key, default)
+
+    def get_provider(self) -> str:
+        return self.get("provider", "openai")
diff --git a/tests/config/__init__.py b/tests/config/__init__.py
new file mode 100644
index 0000000..e69de29
diff --git a/tests/config/test_loader.py b/tests/config/test_loader.py
new file mode 100644
index 0000000..8a95343
--- /dev/null
+++ b/tests/config/test_loader.py
@@ -0,0 +1,10 @@
+from ai4se_agent.config.loader import ConfigLoader
+
+def test_config_returns_defaults():
+    loader = ConfigLoader()
+    assert loader.get("provider", "openai") == "openai"
+
+def test_config_accepts_env_override(monkeypatch):
+    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
+    loader = ConfigLoader()
+    assert loader.get("api_key") == "test-key-123"
