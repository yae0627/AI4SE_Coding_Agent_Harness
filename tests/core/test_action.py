# tests/core/test_action.py
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.types import Action

def test_parse_valid_action():
    parser = ActionParser()
    result = parser.parse('action: write_file path=test.txt content=hello')
    assert result.success is True
    assert result.action.name == "write_file"
    assert result.action.parameters["path"] == "test.txt"

def test_parse_missing_action():
    parser = ActionParser()
    result = parser.parse("some random text")
    assert result.success is False

def test_validate_missing_param():
    validator = ActionValidator()
    action = Action(name="write_file", parameters={})
    errors = validator.validate(action)
    assert any(p in errors[0] for p in ["path", "content"])
