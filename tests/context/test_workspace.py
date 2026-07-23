import time

from ai4se_agent.context.workspace import WorkspaceCollector, WorkspaceSnapshot


def test_snapshot_is_immutable():
    ws = WorkspaceSnapshot(
        os="win32", cwd="/tmp", git_branch="main",
        files=["a.py"], timestamp="2026-07-23T00:00:00"
    )
    try:
        ws.os = "linux"  # type: ignore[misc]
    except Exception:
        pass
    assert ws.os == "win32"


def test_collector_returns_snapshot(tmp_path):
    (tmp_path / "README.md").write_text("# Project")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hi')")
    (tmp_path / ".git").mkdir()

    collector = WorkspaceCollector(str(tmp_path), max_files=50)
    snapshot = collector.collect()
    assert isinstance(snapshot, WorkspaceSnapshot)
    assert len(snapshot.os) > 0
    assert snapshot.cwd == str(tmp_path.resolve())
    files_str = " ".join(snapshot.files)
    assert "README.md" in files_str
    assert ".git" not in files_str


def test_collector_skips_hidden_and_cache(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "main.py").write_text("x")
    collector = WorkspaceCollector(str(tmp_path), max_files=50)
    snapshot = collector.collect()
    files_str = " ".join(snapshot.files)
    assert "main.py" in files_str
    assert ".git" not in files_str
    assert "__pycache__" not in files_str


def test_collector_file_limit(tmp_path):
    for i in range(10):
        (tmp_path / f"file_{i:02d}.py").write_text("x")
    collector = WorkspaceCollector(str(tmp_path), max_files=5)
    snapshot = collector.collect()
    assert len(snapshot.files) <= 7  # 5 + summary line
    assert any("more" in f.lower() for f in snapshot.files[-1:])


def test_collector_cache(tmp_path):
    collector = WorkspaceCollector(str(tmp_path), max_files=50)
    s1 = collector.collect()
    s2 = collector.collect()
    assert s1 is s2


def test_collector_cache_expiry(tmp_path):
    collector = WorkspaceCollector(str(tmp_path), max_files=50)
    collector._cache_ttl = 0.01
    s1 = collector.collect()
    time.sleep(0.02)
    s2 = collector.collect()
    assert s1 is not s2


def test_collector_invalidate(tmp_path):
    collector = WorkspaceCollector(str(tmp_path), max_files=50)
    s1 = collector.collect()
    collector.invalidate()
    s2 = collector.collect()
    assert s1 is not s2


def test_collector_force_refresh(tmp_path):
    collector = WorkspaceCollector(str(tmp_path), max_files=50)
    collector.collect()
    s2 = collector.collect(force=True)
    assert s2 is not None
