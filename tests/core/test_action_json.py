import json
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.types import Action


SCHEMAS = [
    {
        "name": "write_file",
        "description": "Write content to a file",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "File content"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "shell",
        "description": "Run a shell command",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command"},
                "timeout": {"type": "integer", "description": "Timeout"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "finish",
        "description": "Signal task completion",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Summary"}
            },
            "required": []
        }
    }
]


def test_parse_json_action():
    parser = ActionParser()
    result = parser.parse('{"action": "write_file", "parameters": {"path": "a.cpp", "content": "int main() {}"}}')
    assert result.success is True
    assert result.action is not None
    assert result.action.name == "write_file"
    assert result.action.parameters["path"] == "a.cpp"
    assert result.action.parameters["content"] == "int main() {}"


def test_parse_json_with_code_block():
    parser = ActionParser()
    text = '```json\n{"action": "shell", "parameters": {"command": "g++ -o a a.cpp"}}\n```'
    result = parser.parse(text)
    assert result.success is True
    assert result.action.name == "shell"


def test_parse_json_with_plain_code_block():
    parser = ActionParser()
    text = '```\n{"action": "shell", "parameters": {"command": "g++ -o a a.cpp"}}\n```'
    result = parser.parse(text)
    assert result.success is True
    assert result.action.name == "shell"


def test_parse_invalid_json():
    parser = ActionParser()
    result = parser.parse("not json at all")
    assert result.success is False
    assert result.error is not None


def test_parse_missing_action_field():
    parser = ActionParser()
    result = parser.parse('{"name": "write_file", "params": {}}')
    assert result.success is False


def test_parse_finish_action():
    parser = ActionParser()
    result = parser.parse('{"action": "finish", "parameters": {"summary": "done"}}')
    assert result.success is True
    assert result.action.name == "finish"


def test_validate_known_action():
    validator = ActionValidator(SCHEMAS)
    action = Action(name="write_file", parameters={"path": "x.cpp", "content": "x"})
    errors = validator.validate(action)
    assert errors == []


def test_validate_missing_required():
    validator = ActionValidator(SCHEMAS)
    action = Action(name="write_file", parameters={"path": "x.cpp"})
    errors = validator.validate(action)
    assert len(errors) == 1
    assert "content" in errors[0]


def test_validate_unknown_action():
    validator = ActionValidator(SCHEMAS)
    action = Action(name="nonexistent", parameters={})
    errors = validator.validate(action)
    assert len(errors) == 1
    assert "unknown" in errors[0].lower() or "nonexistent" in errors[0]


def test_validate_type_check():
    validator = ActionValidator(SCHEMAS)
    action = Action(name="shell", parameters={"command": 42})
    errors = validator.validate(action)
    assert len(errors) == 1
    assert "string" in errors[0]


def test_validate_finish_action():
    validator = ActionValidator(SCHEMAS)
    action = Action(name="finish", parameters={"summary": "done"})
    errors = validator.validate(action)
    assert errors == []


def test_legacy_fallback():
    parser = ActionParser(fallback=True)
    result = parser.parse("action: write_file path=test.txt content=hello")
    assert result.success is True
    assert result.action.name == "write_file"
    assert result.action.parameters["path"] == "test.txt"
