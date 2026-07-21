# tests/core/test_action.py
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.types import Action

def test_parse_valid_action():
    parser = ActionParser()
    action = parser.parse('action: write_file path=test.txt content=hello')
    assert action.name == "write_file"
    assert action.params["path"] == "test.txt"

def test_parse_missing_action():
    parser = ActionParser()
    result = parser.parse("some random text")
    assert result is None

def test_validate_missing_param():
    validator = ActionValidator()
    action = Action(name="write_file", params={})
    errors = validator.validate(action)
    assert "path" in errors[0] or "content" in errors[0]
