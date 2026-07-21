# src/ai4se_agent/cli.py
import sys
from ai4se_agent.config.loader import ConfigLoader
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.core.state_machine import HarnessStateMachine
from ai4se_agent.llm.openai_adapter import OpenAIAdapter
from ai4se_agent.llm.mock_adapter import MockAdapter
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.tools.read_file import ReadFileTool
from ai4se_agent.tools.write_file import WriteFileTool
from ai4se_agent.tools.edit_file import EditFileTool
from ai4se_agent.tools.shell import ShellTool
from ai4se_agent.tools.run_test import RunTestTool
from ai4se_agent.guardrails.engine import GuardrailEngine
from ai4se_agent.guardrails.command_policy import CommandPolicy
from ai4se_agent.guardrails.file_policy import FilePolicy
from ai4se_agent.guardrails.workspace_policy import WorkspacePolicy
from ai4se_agent.guardrails.git_policy import GitPolicy
from ai4se_agent.feedback.loop import FeedbackLoop
from ai4se_agent.feedback.sensor import TestSensor, LintSensor
from ai4se_agent.feedback.classifier import FailureClassifier
from ai4se_agent.feedback.planner import CorrectionPlanner
from ai4se_agent.memory.manager import MemoryManager
from ai4se_agent.memory.session import SessionMemory
from ai4se_agent.memory.persistent import PersistentMemory


def build_harness(task: str, workspace: str = ".") -> HarnessStateMachine:
    config = ConfigLoader()
    provider = config.get_provider()
    if provider == "mock":
        llm = MockAdapter(responses=["action: shell command=echo hello", "[DONE]"])
    else:
        api_key = config.get("api_key")
        base_url = config.get("base_url")
        llm = OpenAIAdapter(api_key=api_key, base_url=base_url)

    tools = ToolRegistry()
    tools.register(ReadFileTool())
    tools.register(WriteFileTool())
    tools.register(EditFileTool())
    tools.register(ShellTool())
    tools.register(RunTestTool())

    guardrails = GuardrailEngine()
    guardrails.add_policy(CommandPolicy())
    guardrails.add_policy(FilePolicy())
    guardrails.add_policy(WorkspacePolicy(workspace=workspace))
    guardrails.add_policy(GitPolicy())

    feedback = FeedbackLoop(
        sensors=[TestSensor(), LintSensor()],
        classifier=FailureClassifier(),
        planner=CorrectionPlanner()
    )

    memory = MemoryManager(
        session=SessionMemory(),
        persistent=PersistentMemory()
    )

    state = AgentState(goal=task)

    return HarnessStateMachine(
        agent_state=state,
        llm_adapter=llm,
        action_parser=ActionParser(),
        action_validator=ActionValidator(),
        tool_registry=tools,
        guardrail_engine=guardrails,
        feedback_loop=feedback,
        memory_manager=memory,
    )


def main():
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Task: ")
    harness = build_harness(task)
    result = harness.run()
    print(f"\nResult: {result['status']} ({result['reason']}) after {result['iterations']} iterations")


if __name__ == "__main__":
    main()
