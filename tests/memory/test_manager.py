from ai4se_agent.memory.manager import MemoryManager
from ai4se_agent.memory.persistent import PersistentMemory


def test_manager_get_rules_empty_when_no_rules(tmp_path):
    persistent = PersistentMemory(base_dir=str(tmp_path))
    manager = MemoryManager(persistent=persistent)
    assert manager.get_rules() == []


def test_manager_get_rules_sorted(tmp_path):
    persistent = PersistentMemory(base_dir=str(tmp_path))
    persistent.save_rule("b_rule", "second")
    persistent.save_rule("a_rule", "first")
    manager = MemoryManager(persistent=persistent)
    rules = manager.get_rules()
    assert rules == ["first", "second"]


def test_manager_log_failure():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        manager = MemoryManager(failure_log_dir=d)
        entry = {"type": "test", "message": "oops"}
        fid = manager.log_failure(entry)
        assert fid is not None
        failures = manager.list_failures()
        assert len(failures) >= 1


def test_manager_no_failure_dir_no_op():
    manager = MemoryManager()
    fid = manager.log_failure({"msg": "test"})
    assert fid is None
    assert manager.list_failures() == []


def test_manager_persistent_stored(tmp_path):
    persistent = PersistentMemory(base_dir=str(tmp_path))
    manager = MemoryManager(persistent=persistent)
    assert manager.persistent is persistent
