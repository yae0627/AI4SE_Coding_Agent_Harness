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


class TerminalRenderer(Renderer):
    def __init__(self, verbose: bool = False):
        self._verbose = verbose

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
            self._print(f"  response: {response[:200]}")

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
            self._print(f"  output: {result.output[:300]}")

    def on_feedback(self, iteration: int, has_plan: bool, plan_scope: str) -> None:
        if has_plan:
            self._print(f"  feedback: correction planned -- {plan_scope[:100]}")
        else:
            self._print("  feedback: success")

    def on_stop(self, reason: StopReason, iteration: int) -> None:
        self._print(f"STOP: {reason.value} after {iteration} iterations")
