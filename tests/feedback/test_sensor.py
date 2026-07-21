from ai4se_agent.feedback.sensor import TestSensor
from ai4se_agent.types import ToolResult

def test_test_sensor_parses_failure():
    sensor = TestSensor()
    result = ToolResult(success=False, output="FAILED test_order.py::test_validate - AssertionError: expected True got False",
                        metadata={"exit_code": 1})
    feedback = sensor.sense(result)
    assert feedback.success is False
    assert feedback.category == "test_failure"
    assert feedback.source == "pytest"

def test_test_sensor_parses_success():
    sensor = TestSensor()
    result = ToolResult(success=True, output="1 passed", metadata={"exit_code": 0})
    feedback = sensor.sense(result)
    assert feedback.success is True
