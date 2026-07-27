import tempfile
import os
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.tools.read_file import ReadFileTool
from ai4se_agent.tools.write_file import WriteFileTool
from ai4se_agent.core.sanitizer.path import PathNormalizer
from ai4se_agent.types import Action


def test_registry_normalizes_path_params():
    with tempfile.TemporaryDirectory() as tmp:
        normalizer = PathNormalizer(workspace_root=tmp)
        registry = ToolRegistry(path_normalizer=normalizer)
        registry.register(WriteFileTool())

        # Create a subdirectory so the path resolves
        sub = os.path.join(tmp, "subdir")
        os.makedirs(sub, exist_ok=True)

        # Use forward-slash path — should be normalized to absolute
        action = Action(name="write_file", parameters={
            "path": "subdir/test.txt",
            "content": "hello"
        })
        result = registry.execute(action)
        assert result.success is True
        # Verify file was created in the right place
        assert os.path.exists(os.path.join(tmp, "subdir", "test.txt"))


def test_registry_normalizes_backslash_path():
    with tempfile.TemporaryDirectory() as tmp:
        normalizer = PathNormalizer(workspace_root=tmp)
        registry = ToolRegistry(path_normalizer=normalizer)
        registry.register(WriteFileTool())

        sub = os.path.join(tmp, "output")
        os.makedirs(sub, exist_ok=True)

        # Backslash path from Windows
        action = Action(name="write_file", parameters={
            "path": "output\\result.txt",
            "content": "data"
        })
        result = registry.execute(action)
        assert result.success is True
        assert os.path.exists(os.path.join(tmp, "output", "result.txt"))


def test_registry_rejects_path_escape():
    normalizer = PathNormalizer(workspace_root="/safe/workspace")
    registry = ToolRegistry(path_normalizer=normalizer)
    registry.register(ReadFileTool())

    action = Action(name="read_file", parameters={
        "path": "../../etc/passwd"
    })
    result = registry.execute(action)
    assert result.success is False
    assert "escapes workspace" in result.error


def test_registry_without_normalizer_still_works():
    """Backward compat: ToolRegistry without PathNormalizer still functions."""
    with tempfile.TemporaryDirectory() as tmp:
        registry = ToolRegistry()
        registry.register(WriteFileTool())

        action = Action(name="write_file", parameters={
            "path": os.path.join(tmp, "legacy.txt").replace("\\", "/"),
            "content": "old"
        })
        result = registry.execute(action)
        assert result.success is True
