import threading
from pathlib import Path
from typing import TYPE_CHECKING

from ai4se_agent.cli.commands import handle_command
from ai4se_agent.cli.renderer import NullRenderer, Renderer, separator, prompt_str
from ai4se_agent.config.loader import ConfigLoader
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.core.events import AgentEvent
from ai4se_agent.core.interrupt import InterruptChannel
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
        self._agent_running = False

    def _wire_renderer(self, bus: "EventBus") -> None:
        if hasattr(self._renderer, '_on_tool_start'):
            bus.subscribe("TOOL_START", self._renderer._on_tool_start)
            bus.subscribe("TOOL_END", self._renderer._on_tool_end)
            bus.subscribe("LLM_END", self._renderer._on_llm_end)
            bus.subscribe("ACTION_CREATED", self._renderer._on_action_created)
            bus.subscribe("GUARDRAIL_PASS", self._renderer._on_guardrail_pass)
            bus.subscribe("GUARDRAIL_DENY", self._renderer._on_guardrail_deny)
            bus.subscribe("FEEDBACK_COMPLETED", self._renderer._on_feedback_completed)
            bus.subscribe("APPROVAL_REQUIRED", self._renderer._on_approval_required)
            bus.subscribe("AGENT_STOP", self._renderer._on_agent_stop)
            bus.subscribe("RESPOND", self._renderer._on_respond_event)

    def start(self) -> None:
        cfg = self._config.load()
        model = cfg.model.active or "unknown"
        print(f"ai4se-agent  {cfg.provider.name}:{model}")
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

        agent_thread: threading.Thread | None = None
        last_result: dict | None = None

        while True:
            try:
                print(separator())
                prompt = prompt_str() if not self._agent_running else ""
                line = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                if self._agent_running and agent_thread and agent_thread.is_alive():
                    session.memory._interrupt.request_stop() if hasattr(session.memory, '_interrupt') else None
                print()
                break

            if not line:
                continue

            if line.startswith("/") or line in ("exit", "quit"):
                if line in ("exit", "quit"):
                    if self._agent_running and agent_thread and agent_thread.is_alive():
                        session._interrupt.request_stop()
                        agent_thread.join(timeout=2)
                    break
                if not handle_command(line, self):
                    break
                continue

            # During agent execution, route commands to interrupt channel
            if self._agent_running:
                ch = session._interrupt
                if line == "/stop":
                    ch.request_stop()
                elif line == "/approve":
                    ch.send_approval(True)
                elif line == "/reject":
                    ch.send_approval(False)
                else:
                    print("  Agent is running. /stop /approve /reject")
                continue

            # Check if agent finished
            if agent_thread and not agent_thread.is_alive():
                agent_thread.join()
                self._agent_running = False
                if last_result:
                    pass  # result shown by on_stop event
                last_result = None
                agent_thread = None

            # Start new task in background thread
            ch = InterruptChannel()
            session._interrupt = ch
            self._agent_running = True
            last_result = None

            def run_task(task: str):
                nonlocal last_result
                result = session.send(task, interrupt=ch)
                last_result = result

            agent_thread = threading.Thread(target=run_task, args=(line,), daemon=True)
            agent_thread.start()

            # Poll for completion while allowing input
            import time
            while agent_thread.is_alive():
                try:
                    inner = input().strip()
                except (EOFError, KeyboardInterrupt):
                    ch.request_stop()
                    print()
                    break

                if not inner:
                    continue
                if inner == "/stop":
                    ch.request_stop()
                elif inner == "/approve":
                    ch.send_approval(True)
                elif inner == "/reject":
                    ch.send_approval(False)
                elif inner in ("exit", "quit"):
                    ch.request_stop()
                    break
                else:
                    print("  Agent is running. /stop /approve /reject")

            if agent_thread.is_alive():
                agent_thread.join(timeout=1)
            self._agent_running = False

        bus.publish(AgentEvent(type="SESSION_END", iteration=0, state="STOP",
                               payload={"reason": "user_exit"}))

    def exit(self) -> None:
        print("Session ended")
