from ai4se_agent.memory.session import SessionMemory

def test_session_add_and_get():
    mem = SessionMemory(max_turns=5)
    mem.add("user", "hello")
    mem.add("assistant", "hi")
    turns = mem.get_recent(2)
    assert len(turns) == 2
    assert turns[0]["role"] == "user"

def test_session_lru_eviction():
    mem = SessionMemory(max_turns=3)
    for i in range(5):
        mem.add("user", f"msg{i}")
    turns = mem.get_recent(10)
    assert len(turns) == 3
    assert turns[0]["content"] == "msg2"
