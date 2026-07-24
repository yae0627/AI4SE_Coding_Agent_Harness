import shutil
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ai4se_agent.core.events import AgentEvent
from ai4se_agent.types import Action, GuardrailResult, StopReason, ToolResult

if TYPE_CHECKING:
    from ai4se_agent.core.event_bus import EventBus

# ── ANSI color constants ─────────────────────────────────────
_RESET = "\033[0m"
_DIM = "\033[2m"
_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_WHITE_B = "\033[1;37m"


def _c(code: str, text: str) -> str:
    return f"{code}{text}{_RESET}"


def _compact_params(params: dict) -> str:
    """Format tool parameters into a compact single-line summary."""
    if not params:
        return ""
    # Pick the most descriptive param: path > command > message > first value
    for key in ("path", "command", "message"):
        if key in params:
            val = str(params[key])
            return val[:60]
    first = next(iter(params.values()), "")
    return str(first)[:60]


def separator() -> str:
    """Blue horizontal separator spanning terminal width."""
    w = shutil.get_terminal_size().columns
    return _c(_BLUE, "─" * w)


def prompt_str() -> str:
    """Blue prompt prefix for input."""
    return _c(_BLUE, "> ")


class Renderer(ABC):
    @abstractmethod
    def on_state_change(self, old_state: str, new_state: str, iteration: int) -> None:
        pass

    @abstractmethod
    def on_llm_call(self, iteration: int, model: str, response: str) -> None:
        pass

    @abstractmethod
    def on_action(
        self, iteration: int, action: Action, guardrail_result: GuardrailResult | None
    ) -> None:
        pass

    @abstractmethod
    def on_tool_exec(self, iteration: int, tool: str, result: ToolResult) -> None:
        pass

    @abstractmethod
    def on_feedback(self, iteration: int, has_plan: bool, plan_scope: str) -> None:
        pass

    @abstractmethod
    def on_stop(self, reason: StopReason, iteration: int) -> None:
        pass

    @abstractmethod
    def on_token_usage(self, iteration: int, prompt_tokens: int, completion_tokens: int) -> None:
        pass

    @abstractmethod
    def on_timing(self, state_name: str, elapsed_ms: float) -> None:
        pass


class NullRenderer(Renderer):
    def on_state_change(self, old_state: str, new_state: str, iteration: int) -> None:
        pass

    def on_llm_call(self, iteration: int, model: str, response: str) -> None:
        pass

    def on_action(
        self, iteration: int, action: Action, guardrail_result: GuardrailResult | None
    ) -> None:
        pass

    def on_tool_exec(self, iteration: int, tool: str, result: ToolResult) -> None:
        pass

    def on_feedback(self, iteration: int, has_plan: bool, plan_scope: str) -> None:
        pass

    def on_stop(self, reason: StopReason, iteration: int) -> None:
        pass

    def on_token_usage(self, iteration: int, prompt_tokens: int, completion_tokens: int) -> None:
        pass

    def on_timing(self, state_name: str, elapsed_ms: float) -> None:
        pass


class TerminalRenderer(Renderer):
    def __init__(self, verbose: bool = False, max_output: int = 500,
                 event_bus: "EventBus | None" = None):
        self._verbose = verbose
        self._max_output = max_output
        self._total_tokens: int = 0
        self._total_elapsed_ms: float = 0.0
        self._tool_start_time: float = 0.0
        self._tool_start_params: dict = {}
        if event_bus:
            event_bus.subscribe("TOOL_START", self._on_tool_start)
            event_bus.subscribe("TOOL_END", self._on_tool_end)
            event_bus.subscribe("LLM_TOKEN", self._on_llm_token)
            event_bus.subscribe("LLM_END", self._on_llm_end)
            event_bus.subscribe("ACTION_CREATED", self._on_action_created)
            event_bus.subscribe("GUARDRAIL_PASS", self._on_guardrail_pass)
            event_bus.subscribe("GUARDRAIL_DENY", self._on_guardrail_deny)
            event_bus.subscribe("FEEDBACK_COMPLETED", self._on_feedback_completed)
            event_bus.subscribe("APPROVAL_REQUIRED", self._on_approval_required)
            event_bus.subscribe("RESPOND", self._on_respond_event)
            event_bus.subscribe("AGENT_STOP", self._on_agent_stop)
        self._streaming_line = False

    def _print(self, line: str) -> None:
        print(line)

    def _col(self, code: str, text: str) -> str:
        return _c(code, text)

    # ── Renderer ABC methods ─────────────────────────────────
    def on_state_change(self, old_state: str, new_state: str, iteration: int) -> None:
        pass  # internal detail, not shown to user

    def on_llm_call(self, iteration: int, model: str, response: str) -> None:
        if self._verbose:
            self._print(_c(_DIM, f"  model: {model}"))
            self._print(_c(_DIM, f"  response: {response[:500]}"))

    def on_action(
        self, iteration: int, action: Action, guardrail_result: GuardrailResult | None
    ) -> None:
        pass  # tool start/end provide richer output

    def on_tool_exec(self, iteration: int, tool: str, result: ToolResult) -> None:
        pass  # event-driven handlers below

    def on_feedback(self, iteration: int, has_plan: bool, plan_scope: str) -> None:
        pass

    def on_stop(self, reason: StopReason, iteration: int) -> None:
        self._print(_c(_DIM,
            f"  stop: {reason.value} | {iteration} iters | "
            f"{self._total_tokens} tokens | {self._total_elapsed_ms / 1000:.1f}s"
        ))

    def on_token_usage(self, iteration: int, prompt_tokens: int, completion_tokens: int) -> None:
        self._total_tokens += prompt_tokens + completion_tokens

    def on_timing(self, state_name: str, elapsed_ms: float) -> None:
        self._total_elapsed_ms += elapsed_ms

    # ── Event handlers ───────────────────────────────────────
    def _on_tool_start(self, event: AgentEvent) -> None:
        self._tool_start_time = time.time()
        self._tool_start_params = event.payload.get("parameters", {})

    def _on_tool_end(self, event: AgentEvent) -> None:
        elapsed = time.time() - self._tool_start_time
        self._total_elapsed_ms += elapsed * 1000
        tool = event.payload.get("tool", "unknown")
        success = event.payload.get("success", True)
        params_summary = _compact_params(self._tool_start_params)

        # Compact tool line:  tool_name  params_summary  N.Ns ok/FAIL
        tool_line = f"  {tool}  {params_summary}".ljust(50)
        elapsed_str = f"{elapsed:.1f}s"
        if success:
            self._print(_c(_DIM, tool_line) + _c(_GREEN, f" {elapsed_str} ok"))
        else:
            self._print(_c(_DIM, tool_line) + _c(_RED, f" {elapsed_str} FAIL"))

        # Show error details on failure
        if not success:
            error_preview = event.payload.get("output_preview", "")
            if error_preview:
                for line in error_preview.splitlines()[:3]:
                    self._print(_c(_RED, f"    {line[:self._max_output]}"))

    def _on_llm_token(self, event: AgentEvent) -> None:
        token = event.payload.get("token", "")
        if not self._streaming_line:
            print(end="", flush=True)
            self._streaming_line = True
        print(token, end="", flush=True)

    def _on_llm_end(self, event: AgentEvent) -> None:
        if self._streaming_line:
            print()
            self._streaming_line = False
        if self._verbose:
            model = event.payload.get("model", "")
            preview = event.payload.get("response_preview", "")
            self._print(_c(_DIM, f"  model: {model}"))
            self._print(_c(_DIM, f"  response: {preview[:500]}"))

    def _on_action_created(self, event: AgentEvent) -> None:
        pass  # tool start provides richer output

    def _on_guardrail_pass(self, event: AgentEvent) -> None:
        pass  # allow is the default, no need to print

    def _on_guardrail_deny(self, event: AgentEvent) -> None:
        policy = event.payload.get("policy", "")
        reason = event.payload.get("reason", "")
        self._print(_c(_RED, f"  blocked: {policy}") + _c(_DIM, f"  {reason}"))

    def _on_feedback_completed(self, event: AgentEvent) -> None:
        pass

    def _on_respond_event(self, event: AgentEvent) -> None:
        message = event.payload.get("message", "")
        for line in message.splitlines():
            self._print(f"  {line}")

    def _on_approval_required(self, event: AgentEvent) -> None:
        policy = event.payload.get("policy", "unknown")
        reason = event.payload.get("reason", "")
        action_name = event.payload.get("action_name", "")
        action_params = event.payload.get("action_params", {})
        cmd = action_params.get("command", action_params.get("path", ""))

        width = shutil.get_terminal_size().columns
        bar_w = min(width - 2, 60)
        bar = "─" * bar_w

        self._print("")
        self._print(_c(_YELLOW, f"  {bar}"))
        self._print(_c(_YELLOW, "  ") + _c(_WHITE_B, "APPROVAL REQUIRED"))
        self._print("")
        self._print(f"    Policy:  {policy}")
        self._print(f"    Action:  {action_name} {cmd}" if cmd else f"    Action:  {action_name}")
        self._print(f"    Risk:    {reason}")
        self._print("")
        self._print(_c(_YELLOW, "  /approve to confirm") + "  |  " + _c(_YELLOW, "/reject to deny"))
        self._print(_c(_YELLOW, f"  {bar}"))
        self._print("")

    def _on_agent_stop(self, event: AgentEvent) -> None:
        reason = event.payload.get("reason", "unknown")
        iterations = event.payload.get("iterations", 0)
        self._print(_c(_DIM,
            f"  stop: {reason} | {iterations} iters | "
            f"{self._total_tokens} tokens | {self._total_elapsed_ms / 1000:.1f}s"
        ))
