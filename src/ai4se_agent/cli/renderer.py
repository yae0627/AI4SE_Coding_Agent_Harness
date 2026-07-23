import shutil
from abc import ABC, abstractmethod

from ai4se_agent.types import Action, GuardrailResult, StopReason, ToolResult


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
    def __init__(self, verbose: bool = False, max_output: int = 500):
        self._verbose = verbose
        self._max_output = max_output
        self._total_tokens: int = 0
        self._total_elapsed_ms: float = 0.0

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
