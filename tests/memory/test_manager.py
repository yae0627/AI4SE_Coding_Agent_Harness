import json
from pathlib import Path
from ai4se_agent.memory.manager import MemoryManager
from ai4se_agent.session.history import ConversationMemory
from ai4se_agent.memory.persistent import PersistentMemory


def test_manager_aggregates_conversation_and_persistent(tmp_path):
    conv = ConversationMemory()
    pers = PersistentMemory(base_dir=str(tmp_path))
    mgr = MemoryManager(session=conv, persistent=pers)

    conv.append("user", "hello")
    pers.save_rule("test_rule", "use pytest")

    assert len(mgr.session.get_all()) == 1
    assert mgr.get_rules() == ["use pytest"]


def test_manager_get_rules_empty_when_no_rules(tmp_path):
    mgr = MemoryManager(persistent=PersistentMemory(base_dir=str(tmp_path)))
    assert mgr.get_rules() == []


def test_manager_get_rules_sorted(tmp_path):
    pers = PersistentMemory(base_dir=str(tmp_path))
    pers.save_rule("z_rule", "rule z")
    pers.save_rule("a_rule", "rule a")
    mgr = MemoryManager(persistent=pers)
    rules = mgr.get_rules()
    assert rules == ["rule a", "rule z"]


def test_manager_log_failure(tmp_path):
    mgr = MemoryManager(
        persistent=PersistentMemory(base_dir=str(tmp_path)),
        failure_log_dir=str(tmp_path / "failures"),
    )
    mgr.log_failure({
        "type": "test_failure",
        "tool": "pytest",
        "message": "assert 1 == 2",
        "iteration": 3,
    })
    log_dir = Path(tmp_path) / "failures"
    files = list(log_dir.glob("*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["type"] == "test_failure"


def test_manager_default_session_created():
    mgr = MemoryManager()
    assert isinstance(mgr.session, ConversationMemory)
    assert mgr.session.max_messages == 50
