import shutil
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ai4se_agent.core.events import AgentEvent
from ai4se_agent.types import Action, GuardrailResult, StopReason, ToolResult

if TYPE_CHECKING:
    from ai4se_agent.core.event_bus import EventBus


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
        if event_bus:
            event_bus.subscribe("TOOL_START", self._on_tool_start)
            event_bus.subscribe("TOOL_END", self._on_tool_end)
            event_bus.subscribe("LLM_END", self._on_llm_end)
            event_bus.subscribe("ACTION_CREATED", self._on_action_created)
            event_bus.subscribe("GUARDRAIL_PASS", self._on_guardrail_pass)
            event_bus.subscribe("GUARDRAIL_DENY", self._on_guardrail_deny)
            event_bus.subscribe("FEEDBACK_COMPLETED", self._on_feedback_completed)
            event_bus.subscribe("RESPOND", self._on_respond_event)
            event_bus.subscribe("AGENT_STOP", self._on_agent_stop)

    def _print(self, line: str) -> None:
        width = shutil.get_terminal_size().columns
        print(line[:width])

    def on_state_change(self, old_state: str, new_state: str, iteration: int) -> None:
        if new_state == "STOP":
            return
        self._print(f"[{new_state}] Iteration {iteration}")

    def on_llm_call(self, iteration: int, model: str, response: str) -> None:
        if self._verbose:
            self._print(f"  model: {model}")
            limit = 500 if self._verbose else 200
            self._print(f"  response: {response[:limit]}")

    def on_action(
        self, iteration: int, action: Action, guardrail_result: GuardrailResult | None
    ) -> None:
        self._print(f"  action: {action.name}({action.parameters})")
        if guardrail_result is not None:
            self._print(
                f"  guardrail: {guardrail_result.policy} -> {guardrail_result.verdict}"
            )

    def on_tool_exec(self, iteration: int, tool: str, result: ToolResult) -> None:
        status = "OK" if result.success else "FAILED"
        self._print(f"  result: {status}")
        if self._verbose or not result.success:
            self._print(f"  output: {result.output[:self._max_output]}")

    def on_feedback(self, iteration: int, has_plan: bool, plan_scope: str) -> None:
        if has_plan:
            self._print(f"  feedback: correction planned -- {plan_scope[:100]}")
        else:
            self._print("  feedback: success")

    def on_stop(self, reason: StopReason, iteration: int) -> None:
        self._print(
            f"STOP: {reason.value} | {iteration} iters | "
            f"{self._total_tokens} tokens | {self._total_elapsed_ms / 1000:.1f}s"
        )

    def on_token_usage(self, iteration: int, prompt_tokens: int, completion_tokens: int) -> None:
        self._total_tokens += prompt_tokens + completion_tokens
        self._print(f"  token: {prompt_tokens}↑/{completion_tokens}↓")

    def on_timing(self, state_name: str, elapsed_ms: float) -> None:
        self._total_elapsed_ms += elapsed_ms
        if self._verbose:
            self._print(f"  [{state_name}] {elapsed_ms:.1f}ms")

    def _on_tool_start(self, event: AgentEvent) -> None:
        pass

    def _on_tool_end(self, event: AgentEvent) -> None:
        success = event.payload.get("success", True)
        status = "OK" if success else "FAILED"
        self._print(f"  result: {status}")
        output = event.payload.get("output_preview", "")
        if self._verbose or not success:
            if output:
                self._print(f"  output: {output[:self._max_output]}")

    def _on_llm_end(self, event: AgentEvent) -> None:
        if self._verbose:
            model = event.payload.get("model", "")
            preview = event.payload.get("response_preview", "")
            self._print(f"  model: {model}")
            self._print(f"  response: {preview[:500 if self._verbose else 200]}")

    def _on_action_created(self, event: AgentEvent) -> None:
        name = event.payload.get("action_name", "unknown")
        params = event.payload.get("parameters", {})
        self._print(f"  action: {name}({params})")

    def _on_guardrail_pass(self, event: AgentEvent) -> None:
        policy = event.payload.get("policy", "")
        self._print(f"  guardrail: {policy} -> ALLOW")

    def _on_guardrail_deny(self, event: AgentEvent) -> None:
        policy = event.payload.get("policy", "")
        self._print(f"  guardrail: {policy} -> DENY")

    def _on_feedback_completed(self, event: AgentEvent) -> None:
        has_plan = event.payload.get("has_plan", False)
        if has_plan:
            scope = event.payload.get("scope", "")
            self._print(f"  feedback: correction planned -- {scope[:100]}")
        else:
            self._print("  feedback: success")

    def _on_respond_event(self, event: AgentEvent) -> None:
        message = event.payload.get("message", "")
        self._print(f"  [respond] {message}")

    def _on_approval_required(self, event: AgentEvent) -> None:
        policy = event.payload.get("policy", "unknown")
        reason = event.payload.get("reason", "")
        action_name = event.payload.get("action_name", "")
        self._print(f"  [HITL] Policy: {policy}")
        self._print(f"  Reason: {reason}")
        self._print(f"  Action: {action_name}")
        self._print(f"  Type /approve or /reject")

    def _on_agent_stop(self, event: AgentEvent) -> None:
        reason = event.payload.get("reason", "unknown")
        iterations = event.payload.get("iterations", 0)
        self._print(
            f"STOP: {reason} | {iterations} iters | "
            f"{self._total_tokens} tokens | {self._total_elapsed_ms / 1000:.1f}s"
        )
