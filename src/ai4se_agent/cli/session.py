from pathlib import Path
from typing import TYPE_CHECKING

from ai4se_agent.cli.commands import handle_command
from ai4se_agent.cli.renderer import NullRenderer, Renderer
from ai4se_agent.config.loader import ConfigLoader
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.core.events import AgentEvent
from ai4se_agent.observability.tracer import NullTracer, Tracer

if TYPE_CHECKING:
    from ai4se_agent.core.event_bus import EventBus


class SessionManager:
    def __init__(
        self,
        config: ConfigLoader | None = None,
        renderer: Renderer | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        self._config = config or ConfigLoader()
        self._renderer = renderer or NullRenderer()
        self._tracer = tracer or NullTracer()
        self.state: AgentState | None = None

    def _wire_renderer(self, bus: "EventBus") -> None:
        if hasattr(self._renderer, '_on_tool_start'):
            bus.subscribe("TOOL_START", self._renderer._on_tool_start)
            bus.subscribe("TOOL_END", self._renderer._on_tool_end)
            bus.subscribe("LLM_END", self._renderer._on_llm_end)
            bus.subscribe("ACTION_CREATED", self._renderer._on_action_created)
            bus.subscribe("GUARDRAIL_PASS", self._renderer._on_guardrail_pass)
            bus.subscribe("GUARDRAIL_DENY", self._renderer._on_guardrail_deny)
            bus.subscribe("FEEDBACK_COMPLETED", self._renderer._on_feedback_completed)
            bus.subscribe("AGENT_STOP", self._renderer._on_agent_stop)

    def start(self) -> None:
        cfg = self._config.load()
        model = cfg.model.active or "unknown"
        print(f"Workspace: {Path.cwd().resolve()}")
        print(f"Model: {model}")
        print(f"Provider: {cfg.provider.name}")
        print()

    def submit(self, task: str) -> dict:
        from ai4se_agent.session.session import Session
        from ai4se_agent.core.event_bus import EventBus

        bus = EventBus()
        self._wire_renderer(bus)
        session = Session(config=self._config, event_bus=bus)
        return session.send(task)

    def interactive(self) -> None:
        from ai4se_agent.session.session import Session
        from ai4se_agent.core.event_bus import EventBus

        bus = EventBus()
        self._wire_renderer(bus)
        session = Session(config=self._config, event_bus=bus)
        bus.publish(AgentEvent(type="SESSION_START", iteration=0, state="IDLE",
                               payload={"session_id": session.id}))

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
                result = session.send(line)
                print(f"Result: {result['status']} ({result['reason']})")
            except (EOFError, KeyboardInterrupt):
                print()
                break

        bus.publish(AgentEvent(type="SESSION_END", iteration=0, state="STOP",
                               payload={"reason": "user_exit"}))

    def exit(self) -> None:
        print("Session ended")
