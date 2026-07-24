from ai4se_agent.session.history import ConversationMemory


def test_append_user_message():
    mem = ConversationMemory()
    mem.append("user", "hello")
    messages = mem.get_recent()
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "hello"


def test_append_with_metadata():
    mem = ConversationMemory()
    mem.append("assistant", "", metadata={"action": "shell", "params": {"command": "dir"}})
    messages = mem.get_recent()
    assert messages[0]["metadata"]["action"] == "shell"


def test_append_tool_result():
    mem = ConversationMemory()
    mem.append("tool", "file1.txt\nfile2.txt", metadata={"tool": "shell", "success": True})
    messages = mem.get_recent()
    assert messages[0]["role"] == "tool"
    assert messages[0]["metadata"]["tool"] == "shell"


def test_get_recent_ordering():
    mem = ConversationMemory()
    mem.append("user", "task 1")
    mem.append("assistant", "response 1")
    mem.append("user", "task 2")
    messages = mem.get_recent()
    assert len(messages) == 3
    assert messages[0]["content"] == "task 1"
    assert messages[2]["content"] == "task 2"


def test_get_recent_truncation():
    mem = ConversationMemory(max_messages=3)
    for i in range(5):
        mem.append("user", f"msg {i}")
    messages = mem.get_recent()
    assert len(messages) == 3
    assert messages[0]["content"] == "msg 2"
    assert messages[-1]["content"] == "msg 4"


def test_extend_bulk_append():
    mem = ConversationMemory()
    mem.extend([
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
        {"role": "tool", "content": "ok", "metadata": {"tool": "shell"}},
    ])
    assert len(mem.get_recent()) == 3
    assert mem.get_recent()[2]["metadata"]["tool"] == "shell"


def test_get_all():
    mem = ConversationMemory()
    mem.append("user", "a")
    mem.append("user", "b")
    assert len(mem.get_all()) == 2


def test_clear():
    mem = ConversationMemory()
    mem.append("user", "msg")
    mem.clear()
    assert mem.get_recent() == []


def test_max_messages_default():
    mem = ConversationMemory()
    assert mem.max_messages == 50


def test_sliding_window_evicts_oldest():
    mem = ConversationMemory(max_messages=4)
    mem.append("user", "msg0")
    mem.append("user", "msg1")
    mem.append("user", "msg2")
    mem.append("user", "msg3")
    mem.append("assistant", "msg4")
    messages = mem.get_recent()
    assert len(messages) == 4
    assert messages[0]["content"] == "msg1"
    assert messages[-1]["content"] == "msg4"
