from ai4se_agent.core.action import ActionParser


def test_repair_windows_path_backslash_u():
    """\\U (not a valid JSON escape) is repaired to \\\\U.

    Uses \\System32 (\\S is invalid) and \\Admin (\\A is invalid).
    Avoids \\f (form feed) which IS a valid JSON escape.
    """
    parser = ActionParser()
    text = '{"action": {"name": "read_file", "parameters": {"path": "C:\\System32\\Admin\\data.txt"}}}'
    result = parser.parse(text)
    assert result.success is True
    assert result.action.name == "read_file"
    # \S and \A were repaired: path contains literal backslash + S, backslash + A
    path = result.action.parameters["path"]
    assert "System32" in path
    assert "Admin" in path

def test_repair_windows_path_backslash_d():
    """\\D (not a valid JSON escape) is repaired in drive-letter paths."""
    parser = ActionParser()
    text = '{"action": {"name": "read_file", "parameters": {"path": "D:\\data\\logs\\app.log"}}}'
    result = parser.parse(text)
    assert result.success is True
    assert "data" in result.action.parameters["path"]
    assert "logs" in result.action.parameters["path"]


def test_repair_windows_path_multiple_invalid_escapes():
    parser = ActionParser()
    text = '{"action": {"name": "read_file", "parameters": {"path": "D:\\projects\\src\\main.py"}}}'
    result = parser.parse(text)
    assert result.success is True
    assert "projects" in result.action.parameters["path"]


def test_repair_does_not_break_valid_escapes():
    """Valid JSON escapes (\\n, \\t, \\\", \\\\) are NOT altered."""
    parser = ActionParser()
    text = '{"action": {"name": "shell", "parameters": {"command": "echo \\"hello\\"\\necho world"}}}'
    result = parser.parse(text)
    assert result.success is True
    # newline escape should still be a newline
    assert "echo" in result.action.parameters["command"]


def test_repair_does_not_break_windows_path_with_message():
    parser = ActionParser()
    text = '{"message": "reading from D drive", "action": {"name": "read_file", "parameters": {"path": "D:\\data\\log.txt"}}}'
    result = parser.parse(text)
    assert result.success is True
    assert result.message == "reading from D drive"
    assert result.action.name == "read_file"


def test_repair_and_quote_repair_chain():
    """Both repairs can chain: escape repair first, then quote repair."""
    parser = ActionParser()
    # Has BOTH invalid escapes (\U) AND unescaped quotes in content
    text = (
        '{"action": {"name": "write_file", "parameters": {'
        '"path": "C:\\Users\\test\\out.cpp", '
        '"content": "#include <iostream>\\nint main() { std::cout << \\"hi\\"; }\\n"'
        '}}}'
    )
    result = parser.parse(text)
    assert result.success is True
    assert result.action.name == "write_file"
    assert 'std::cout << "hi"' in result.action.parameters["content"]


def test_valid_json_unchanged():
    """Clean JSON with proper escaping is not modified."""
    parser = ActionParser()
    text = '{"action": {"name": "shell", "parameters": {"command": "echo hello"}}}'
    result = parser.parse(text)
    assert result.success is True
    assert result.action.parameters["command"] == "echo hello"
