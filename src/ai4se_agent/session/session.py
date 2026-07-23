import uuid
from ai4se_agent.config.loader import ConfigLoader
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.core.event_bus import EventBus
from ai4se_agent.core.events import AgentEvent
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
from ai4se_agent.llm.manager import LLMManager
from ai4se_agent.memory.manager import MemoryManager
from ai4se_agent.memory.persistent import PersistentMemory
from ai4se_agent.memory.session import SessionMemory
from ai4se_agent.session.history import MessageHistory
from ai4se_agent.tools.edit_file import EditFileTool
from ai4se_agent.tools.read_file import ReadFileTool
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.tools.run_test import RunTestTool
from ai4se_agent.tools.shell import ShellTool
from ai4se_agent.tools.write_file import WriteFileTool


class AgentRuntime:
    def __init__(
        self,
        goal: str,
        history: list[dict],
        config: ConfigLoader,
        event_bus: EventBus | None = None,
    ):
        self.goal = goal
        self._history = history
        self._config = config
        self._event_bus = event_bus
        self._llm = LLMManager(config)
        self._state: AgentState | None = None

    def run(self) -> dict:
        self._emit("AGENT_START", payload={"goal": self.goal})

        llm = self._llm.get_adapter()

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

        self._state = AgentState(goal=self.goal)
        self._state.history = list(self._history)

        machine = HarnessStateMachine(
            agent_state=self._state,
            llm_adapter=llm,
            action_parser=ActionParser(),
            action_validator=ActionValidator(schemas=tools.list_schemas()),
            tool_registry=tools,
            guardrail_engine=guardrails,
            feedback_loop=feedback,
            memory_manager=memory,
            event_bus=self._event_bus or EventBus(),
        )
        result = machine.run()
        # AGENT_STOP is emitted by StateMachine._on_stop via EventBus
        return result

    def _emit(self, event_type: str, payload: dict | None = None) -> None:
        if self._event_bus is None:
            return
        iteration = self._state.iteration if self._state else 0
        state_name = self._state.current_state if self._state else "IDLE"
        self._event_bus.publish(AgentEvent(
            type=event_type,
            iteration=iteration,
            state=state_name,
            payload=payload or {},
        ))


class Session:
    def __init__(
        self,
        config: ConfigLoader,
        event_bus: EventBus | None = None,
        history: MessageHistory | None = None,
    ):
        self.id = uuid.uuid4().hex[:12]
        self._config = config
        self._event_bus = event_bus or EventBus()
        self.history = history or MessageHistory()

    def send(self, message: str) -> dict:
        if self._event_bus:
            self._event_bus.publish(AgentEvent(
                type="SESSION_START", iteration=0, state="IDLE",
                payload={"session_id": self.id},
            ))
        runtime = AgentRuntime(
            goal=message,
            history=self.history.get_recent(),
            config=self._config,
            event_bus=self._event_bus,
        )
        result = runtime.run()
        self.history.add_turn(message, result)
        if self._event_bus:
            self._event_bus.publish(AgentEvent(
                type="SESSION_END", iteration=0, state="STOP",
                payload={"reason": result["reason"]},
            ))
        return result
