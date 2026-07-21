from ai4se_agent.memory.persistent import PersistentMemory

def test_save_and_load_rule(tmp_path):
    mem = PersistentMemory(base_dir=str(tmp_path))
    mem.save_rule("branch_naming", "Use feat/ prefix")
    loaded = mem.load_rule("branch_naming")
    assert loaded == "Use feat/ prefix"

def test_save_summary(tmp_path):
    mem = PersistentMemory(base_dir=str(tmp_path))
    mem.save_summary("session-1", "Fixed bug in validator")
    summaries = mem.list_summaries()
    assert len(summaries) >= 1
