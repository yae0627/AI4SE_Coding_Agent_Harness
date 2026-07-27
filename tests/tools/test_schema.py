from ai4se_agent.tools.base import Tool
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.types import ParseResult


class _DummyTool(Tool):
    name = "dummy"

    @property
    def schema(self) -> dict:
        return {
            "name": "dummy",
            "description": "A dummy tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "msg": {"type": "string", "description": "A message"}
                },
                "required": ["msg"]
            }
        }

    def execute(self, params: dict):
        from ai4se_agent.types import ToolResult
        return ToolResult(success=True, output=params.get("msg", ""))


def test_tool_schema_is_dict():
    tool = _DummyTool()
    s = tool.schema
    assert isinstance(s, dict)
    assert s["name"] == "dummy"
    assert "parameters" in s


def test_registry_list_schemas():
    registry = ToolRegistry()
    registry.register(_DummyTool())
    schemas = registry.list_schemas()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "dummy"


def test_parse_result_creation():
    from ai4se_agent.types import Action
    r = ParseResult(success=True, action=Action(name="test", parameters={}))
    assert r.success is True
    assert r.action is not None
    assert r.error is None


def test_parse_result_failure():
    r = ParseResult(success=False, error="bad json")
    assert r.success is False
    assert r.action is None
    assert r.error == "bad json"


def test_control_schemas_include_ask_not_respond():
    from ai4se_agent.core.action_schema import CONTROL_SCHEMAS
    names = [s["name"] for s in CONTROL_SCHEMAS]
    assert "ask" in names, "CONTROL_SCHEMAS should include ask"
    assert "finish" in names, "CONTROL_SCHEMAS should include finish"
    assert "respond" not in names, "CONTROL_SCHEMAS should NOT include respond (deprecated)"
