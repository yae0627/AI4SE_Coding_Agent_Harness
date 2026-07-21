from ai4se_agent.memory.manager import MemoryManager
from ai4se_agent.memory.session import SessionMemory
from ai4se_agent.memory.persistent import PersistentMemory

def test_manager_adds_to_session(tmp_path):
    mgr = MemoryManager(session=SessionMemory(), persistent=PersistentMemory(base_dir=str(tmp_path)))
    mgr.add_to_session("user", "test")
    assert len(mgr.get_session_history()) == 1
