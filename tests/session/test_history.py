from ai4se_agent.session.history import MessageHistory


def test_add_user_message():
    h = MessageHistory()
    h.add_user("hello")
    messages = h.get_recent()
    assert len(messages) == 1
    assert messages[0] == {"role": "user", "content": "hello"}


def test_add_assistant_message():
    h = MessageHistory()
    h.add_assistant("action: shell command=ls")
    messages = h.get_recent()
    assert messages[0]["role"] == "assistant"
    assert "shell" in messages[0]["content"]


def test_add_tool_result():
    h = MessageHistory()
    h.add_tool_result("shell", "file1.txt\nfile2.txt")
    messages = h.get_recent()
    assert messages[0]["role"] == "tool"
    assert "file1.txt" in messages[0]["content"]


def test_add_system_message():
    h = MessageHistory()
    h.add_system("Project rules: no rm -rf")
    messages = h.get_recent()
    assert messages[0]["role"] == "system"


def test_get_recent_ordering():
    h = MessageHistory()
    h.add_user("task 1")
    h.add_assistant("response 1")
    h.add_user("task 2")
    messages = h.get_recent()
    assert len(messages) == 3
    assert messages[0]["content"] == "task 1"
    assert messages[2]["content"] == "task 2"


def test_get_recent_truncation():
    h = MessageHistory(max_messages=3)
    for i in range(5):
        h.add_user(f"msg {i}")
    messages = h.get_recent()
    assert len(messages) == 3
    assert messages[0]["content"] == "msg 2"
    assert messages[-1]["content"] == "msg 4"


def test_add_turn():
    h = MessageHistory()
    h.add_turn("user says hi", {"status": "success", "reason": "success", "iterations": 3})
    messages = h.get_recent()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"


def test_clear():
    h = MessageHistory()
    h.add_user("msg")
    h.clear()
    assert h.get_recent() == []
