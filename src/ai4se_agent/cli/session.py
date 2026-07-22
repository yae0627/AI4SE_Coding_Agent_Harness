from typing import Any

from ai4se_agent.cli.commands import handle_command
from ai4se_agent.cli.renderer import NullRenderer, Renderer
from ai4se_agent.config.loader import ConfigLoader
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.core.state_machine import HarnessStateMachine
from ai4se_agent.feedback.classifier import FailureClassifier
from ai4se_agent.feedback.loop import FeedbackLoop
from ai4se_agent.feedback.planner import CorrectionPlanner
from ai4se_agent.feedback.sensor import LintSensor, TestSensor
from ai4se_agent.guardrails.command_policy import CommandPolicy
from ai4se_agent.guardrails.engine import GuardrailEngine
from ai4se_agent.guardrails.file_policy import FilePolicy
from ai4se_agent.guardrails.git_policy import GitPolicy
from ai4se_agent.guardrails.workspace_policy import WorkspacePolicy
from ai4se_agent.llm.mock_adapter import MockAdapter
from ai4se_agent.llm.openai_adapter import OpenAIAdapter
from ai4se_agent.memory.manager import MemoryManager
from ai4se_agent.memory.persistent import PersistentMemory
from ai4se_agent.memory.session import SessionMemory
from ai4se_agent.observability.tracer import NullTracer, Tracer
from ai4se_agent.tools.edit_file import EditFileTool
from ai4se_agent.tools.read_file import ReadFileTool
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.tools.run_test import RunTestTool
from ai4se_agent.tools.shell import ShellTool
from ai4se_agent.tools.write_file import WriteFileTool


class SessionManager:
    def __init__(
        self,
        renderer: Renderer | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        self._renderer = renderer or NullRenderer()
        self._tracer = tracer or NullTracer()
        self._harness: HarnessStateMachine | None = None
        self.state: AgentState | None = None

    def _build_harness(self, task: str) -> HarnessStateMachine:
        config = ConfigLoader()
        provider = config.get_provider()
        if provider == "mock":
            llm: Any = MockAdapter(
                responses=["action: shell command=echo hello", "[DONE]"]
            )
        else:
            api_key = config.get("api_key") or ""
            base_url = config.get("base_url")
            model = config.get("model") or ""
            llm = OpenAIAdapter(api_key=api_key, base_url=base_url, model=model)

        tools = ToolRegistry()
        tools.register(ReadFileTool())
        tools.register(WriteFileTool())
        tools.register(EditFileTool())
        tools.register(ShellTool())
        tools.register(RunTestTool())

        guardrails = GuardrailEngine()
        guardrails.add_policy(CommandPolicy())
        guardrails.add_policy(FilePolicy())
        guardrails.add_policy(WorkspacePolicy(workspace="."))
        guardrails.add_policy(GitPolicy())

        feedback = FeedbackLoop(
            sensors=[TestSensor(), LintSensor()],
            classifier=FailureClassifier(),
            planner=CorrectionPlanner(),
        )

        memory = MemoryManager(
            session=SessionMemory(),
            persistent=PersistentMemory(),
        )

        state = AgentState(goal=task)
        self.state = state

        return HarnessStateMachine(
            agent_state=state,
            llm_adapter=llm,
            action_parser=ActionParser(),
            action_validator=ActionValidator(),
            tool_registry=tools,
            guardrail_engine=guardrails,
            feedback_loop=feedback,
            memory_manager=memory,
            renderer=self._renderer,
            tracer=self._tracer,
        )

    def start(self) -> None:
        config = ConfigLoader()
        provider = config.get_provider()
        model = config.get("model") or "unknown"
        self._renderer.on_state_change("", "IDLE", 0)
        print("Workspace: .")
        print(f"Model: {model}")
        print(f"Provider: {provider}")
        print()

    def submit(self, task: str) -> dict:
        harness = self._build_harness(task)
        self._harness = harness
        result = harness.run()
        return result

    def interactive(self) -> None:
        self.start()
        while True:
            try:
                line = input("> ").strip()
                if not line:
                    continue
                if line.startswith("/") or line in ("exit", "quit"):
                    if not handle_command(line, self):
                        break
                    continue
                result = self.submit(line)
                print(f"Result: {result['status']} ({result['reason']})")
            except (EOFError, KeyboardInterrupt):
                print()
                break

    def exit(self) -> None:
        print("Session ended")
