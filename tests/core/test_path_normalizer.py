from pathlib import Path
from ai4se_agent.core.sanitizer.path import PathNormalizer


def test_normalize_relative_path():
    n = PathNormalizer(workspace_root="/home/user/project")
    result = n.normalize("src/main.py")
    assert str(result).replace("\\", "/").endswith("src/main.py")


def test_normalize_forward_slash_path():
    n = PathNormalizer(workspace_root="/tmp/work")
    result = n.normalize("subdir/file.txt")
    assert result.name == "file.txt"


def test_normalize_backslash_path():
    """Backslashes from Windows paths are normalized to forward slashes."""
    n = PathNormalizer(workspace_root="/tmp/work")
    result = n.normalize("subdir\\file.txt")
    assert result.name == "file.txt"


def test_normalize_windows_drive_path():
    """Backslash path is normalized regardless of platform."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        n = PathNormalizer(workspace_root=tmp)
        result = n.normalize("subdir\\nested\\data.txt")
        assert result.name == "data.txt"


def test_normalize_path_escape_rejected():
    """Path escaping workspace via .. is rejected."""
    import tempfile
    import os
    with tempfile.TemporaryDirectory() as tmp:
        n = PathNormalizer(workspace_root=tmp)
        try:
            n.normalize("../outside.txt")
            assert False, "should have raised ValueError"
        except ValueError as e:
            assert "escapes workspace" in str(e)


def test_normalize_root_property():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        n = PathNormalizer(workspace_root=tmp)
        assert n.root == Path(tmp).resolve()


def test_normalize_absolute_path_inside_workspace():
    import tempfile
    import os
    with tempfile.TemporaryDirectory() as tmp:
        n = PathNormalizer(workspace_root=tmp)
        abs_path = os.path.join(tmp, "subdir", "file.txt")
        result = n.normalize(abs_path)
        assert result.name == "file.txt"
