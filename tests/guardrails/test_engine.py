from ai4se_agent.guardrails.engine import GuardrailEngine
from ai4se_agent.guardrails.command_policy import CommandPolicy
from ai4se_agent.types import Action

def test_engine_block_dangerous():
    engine = GuardrailEngine()
    engine.add_policy(CommandPolicy())
    action = Action(name="shell", parameters={"command": "rm -rf /"})
    result = engine.check(action)
    assert result.verdict == "DENY"
