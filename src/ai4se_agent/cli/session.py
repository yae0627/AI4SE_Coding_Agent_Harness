import shutil
import sys
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
            bus.subscribe("LLM_MESSAGE", self._renderer._on_llm_message)
            bus.subscribe("PLAN_UPDATED", self._renderer._on_plan_updated)

    def start(self) -> None:
        cfg = self._config.load()
        model = cfg.model.active or "unknown"
        provider = cfg.provider.name or "unknown"
        w = min(shutil.get_terminal_size().columns, 60)
        bar = "=" * w
        print(bar)
        print("  AI4SE Agent  v0.1.0")
        print(f"  {provider} / {model}")
        print(bar)
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
        ch: InterruptChannel | None = None

        def _read_idle() -> str:
            """Read input with > prompt. When / is typed, show live
            command preview below the input line."""
            try:
                import msvcrt
            except ImportError:
                return input("> ").strip()

            from ai4se_agent.cli.commands import matching_commands

            chars: list[str] = []
            max_w = shutil.get_terminal_size().columns

            # Show initial prompt with leading blank line
            sys.stdout.write("\n\033[1;37m> \033[0m")
            sys.stdout.flush()

            def _redraw():
                """Redraw input line + preview. Always ends with cursor
                at the correct position on the input line."""
                line = "".join(chars)
                matches = matching_commands(line) if line.startswith("/") else []
                sys.stdout.write("\r\033[2K")
                sys.stdout.write(f"\033[1;37m> {line}\033[0m")
                sys.stdout.write("\033[J")
                count = 0
                if matches:
                    sys.stdout.write("\n")
                    count += 1
                    for name, desc in matches:
                        entry = f"  \033[2m{name:<12s} {desc}\033[0m"
                        sys.stdout.write(entry[:max_w - 1] + "\n")
                        count += 1
                if count > 0:
                    sys.stdout.write(f"\033[{count}A")
                sys.stdout.write(f"\r\033[{2 + len(line)}C")
                sys.stdout.flush()

            while True:
                ch = msvcrt.getwch()
                if ch in ("\r", "\n"):
                    # Clear preview, show final input line, and return
                    line = "".join(chars)
                    sys.stdout.write("\r\033[J")
                    sys.stdout.write(f"\r\033[1;37m> {line}\033[0m\n")
                    sys.stdout.flush()
                    return line.strip()
                if ch == "\x08":
                    if chars:
                        chars.pop()
                elif ch == "\x03":
                    raise KeyboardInterrupt
                elif ch.isprintable():
                    chars.append(ch)
                _redraw()

        def _read_running(current_thread) -> str:
            """Poll keyboard during agent execution. Returns immediately
            when the agent finishes, so the > prompt appears without
            requiring the user to press Enter."""
            try:
                import msvcrt
            except ImportError:
                return input().strip()
            chars: list[str] = []
            while current_thread and current_thread.is_alive():
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    if ch in ("\r", "\n"):
                        print()
                        return "".join(chars).strip()
                    elif ch == "\x08":
                        if chars:
                            chars.pop()
                            print("\b \b", end="", flush=True)
                    elif ch == "\x03":
                        raise KeyboardInterrupt
                    elif ch.isprintable():
                        chars.append(ch)
                        print(ch, end="", flush=True)
                else:
                    import time as _time
                    _time.sleep(0.1)
            return "".join(chars).strip()

        while True:
            # ── Read input ────────────────────────────────────────
            # Idle: blocking input("> ") with prompt.
            # Running: poll keyboard, return on Enter or agent finish.
            try:
                if self._agent_running:
                    line = _read_running(agent_thread)
                else:
                    line = _read_idle()
            except (EOFError, KeyboardInterrupt):
                if self._agent_running and ch:
                    ch.request_stop()
                    if agent_thread:
                        agent_thread.join(timeout=5)
                    agent_thread = None
                    ch = None
                    self._agent_running = False
                    print()
                    continue
                print()
                break

            # ── Clean up finished agent ───────────────────────────
            if agent_thread and not agent_thread.is_alive():
                agent_thread.join()
                agent_thread = None
                ch = None
                self._agent_running = False

            # ── Agent running → commands only ─────────────────────
            if self._agent_running:
                if not ch:
                    continue
                if line == "/stop":
                    ch.request_stop()
                elif line == "/approve":
                    ch.send_approval(True)
                elif line == "/reject":
                    ch.send_approval(False)
                elif line in ("exit", "quit"):
                    ch.request_stop()
                    break
                elif line.startswith("/"):
                    handle_command(line, self)
                elif line:
                    w = min(shutil.get_terminal_size().columns, 60)
                    print(f"\033[33m  " + "─" * (w - 4) + "\033[0m")
                    print(f"\033[33m  ● Running\033[0m  \033[2mtype /stop to cancel\033[0m")
                    print(f"\033[33m  " + "─" * (w - 4) + "\033[0m")
                    print()
                continue

            # ── Agent idle → new task or command ──────────────────
            if not line:
                continue
            if line in ("exit", "quit"):
                break
            if line.startswith("/"):
                if not handle_command(line, self):
                    break
                continue

            print()
            ch = InterruptChannel()
            session._interrupt = ch
            self._agent_running = True

            def run_task(task: str):
                session.send(task, interrupt=ch)

            agent_thread = threading.Thread(target=run_task, args=(line,), daemon=True)
            agent_thread.start()

            # Visual indicator that agent is now running
            w = min(shutil.get_terminal_size().columns, 60)
            print(f"\033[33m  " + "─" * (w - 4) + "\033[0m")
            print(f"\033[33m  ● Running\033[0m  \033[2mtype /stop to cancel\033[0m")
            print(f"\033[33m  " + "─" * (w - 4) + "\033[0m")
            print()

        bus.publish(AgentEvent(type="SESSION_END", iteration=0, state="STOP",
                               payload={"reason": "user_exit"}))

    def exit(self) -> None:
        print("Session ended")
