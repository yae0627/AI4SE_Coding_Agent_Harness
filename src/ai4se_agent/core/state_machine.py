# src/ai4se_agent/core/state_machine.py
from pathlib import Path
from typing import Any, Optional
from transitions import Machine
from ai4se_agent.cli.renderer import NullRenderer, Renderer
from ai4se_agent.context.builder import ContextBuilder
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.feedback.loop import FeedbackLoop
from ai4se_agent.guardrails.engine import GuardrailEngine
from ai4se_agent.llm.base import LLMAdapter
from ai4se_agent.memory.manager import MemoryManager
from ai4se_agent.observability.events import (
    ActionEvent,
    FeedbackEvent,
    GuardrailEvent,
    LLMEvent,
    ToolEvent,
)
from ai4se_agent.observability.tracer import NullTracer, Tracer
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.core.events import AgentEvent
from ai4se_agent.types import Action, GuardrailResult, StopReason, ToolResult


class HarnessStateMachine:
    states = [
        "IDLE", "CONTEXT_ORG", "LLM_CALL", "ACTION_PARSE",
        "GUARDRAIL", "WAIT_APPROVAL", "TOOL_EXEC", "TOOL_ERROR",
        "FEEDBACK", "MEMORY_UPDATE", "STOP"
    ]

    def __getattr__(self, name: str) -> Any:
        ...

    def __init__(
        self,
        agent_state: AgentState,
        llm_adapter: LLMAdapter,
        action_parser: ActionParser,
        action_validator: ActionValidator,
        tool_registry: ToolRegistry,
        guardrail_engine: GuardrailEngine,
        feedback_loop: FeedbackLoop | None,
        memory_manager: MemoryManager,
        max_iterations: int = 20,
        renderer: Renderer = NullRenderer(),
        tracer: Tracer = NullTracer(),
        event_bus: "EventBus | None" = None,
    ):
        self.state = agent_state
        self.llm = llm_adapter
        self.parser = action_parser
        self.validator = action_validator
        self.tools = tool_registry
        self.guardrails = guardrail_engine
        self.feedback = feedback_loop
        self.memory = memory_manager
        self.max_iterations = max_iterations
        self.stop_reason = StopReason.SUCCESS
        self._pending_action: Optional[Action] = None
        self._pending_guardrail: Optional[GuardrailResult] = None
        self._last_tool_result: Optional[ToolResult] = None
        self._context_builder = ContextBuilder(
            tool_registry=self.tools, workspace_root=str(Path.cwd().resolve())
        )
        self._renderer = renderer
        self._tracer = tracer
        self._event_bus = event_bus

        self.machine = Machine(
            model=self,
            states=HarnessStateMachine.states,
            initial="IDLE",
            auto_transitions=False,
            model_attribute="_fsm_state",
        )

        self.machine.add_transition("start", "IDLE", "CONTEXT_ORG", after="_on_context_org")
        self.machine.add_transition("retry_context", "CONTEXT_ORG", "CONTEXT_ORG", after="_on_context_org")
        self.machine.add_transition("llm_error", "LLM_CALL", "CONTEXT_ORG", after="_on_context_org")
        self.machine.add_transition("call_llm", "CONTEXT_ORG", "LLM_CALL", after="_on_llm_call")
        self.machine.add_transition("parse_action", "LLM_CALL", "ACTION_PARSE", after="_on_action_parse")
        self.machine.add_transition("retry_parse", "ACTION_PARSE", "CONTEXT_ORG", after="_on_context_org")
        self.machine.add_transition("check_guardrails", "ACTION_PARSE", "GUARDRAIL", after="_on_guardrail")
        self.machine.add_transition("deny_action", "GUARDRAIL", "CONTEXT_ORG", after="_on_context_org")
        self.machine.add_transition("request_approval", "GUARDRAIL", "WAIT_APPROVAL", after="_on_wait_approval")
        self.machine.add_transition("approve", "WAIT_APPROVAL", "TOOL_EXEC", after="_on_tool_exec")
        self.machine.add_transition("reject", "WAIT_APPROVAL", "CONTEXT_ORG", after="_on_context_org")
        self.machine.add_transition("execute", "GUARDRAIL", "TOOL_EXEC", after="_on_tool_exec")
        self.machine.add_transition("tool_error", "TOOL_EXEC", "TOOL_ERROR", after="_on_tool_error")
        self.machine.add_transition("tool_success", "TOOL_EXEC", "FEEDBACK", after="_on_feedback")
        self.machine.add_transition("retry_tool", "TOOL_ERROR", "TOOL_EXEC", after="_on_tool_exec")
        self.machine.add_transition("feedback_done", "FEEDBACK", "MEMORY_UPDATE", after="_on_memory_update")
        self.machine.add_transition("feedback_correct", "FEEDBACK", "CONTEXT_ORG", after="_on_context_org")
        self.machine.add_transition("continue_loop", "MEMORY_UPDATE", "CONTEXT_ORG", after="_on_context_org")
        self.machine.add_transition("stop", "*", "STOP", after="_on_stop")

    def run(self) -> dict:
        self.start()
        return self._build_result()

    def _on_context_org(self) -> None:
        self.state.increment_iteration()
        if self.state.iteration > self.max_iterations:
            self.stop_reason = StopReason.MAX_ITERATION
            self._renderer.on_state_change("CONTEXT_ORG", "STOP", self.state.iteration)
            self.stop()
            return
        self._renderer.on_state_change("", "CONTEXT_ORG", self.state.iteration)
        self.call_llm()

    def _on_llm_call(self) -> None:
        try:
            messages = self._context_builder.build(self.state)
            self._emit("LLM_START", {"model": getattr(self.llm, "model", "")})
            response = self.llm.generate(messages)
            model = getattr(self.llm, "model", "")
            self._emit("LLM_END", {"model": model, "response_preview": response[:200]})
            self._renderer.on_llm_call(self.state.iteration, model, response)
            self._tracer.record(
                LLMEvent(self.state.iteration, model, messages, response)
            )
            self.state.history.append({"role": "assistant", "content": response})
            self.parse_action()
        except Exception:
            self.state.error_count += 1
            if self.state.error_count >= 3:
                self.stop_reason = StopReason.LLM_ERROR
                self.stop()
            else:
                self.llm_error()

    def _on_action_parse(self) -> None:
        last_msg = self.state.history[-1]["content"]
        result = self.parser.parse(last_msg)
        if not result.success:
            self.state.record_feedback(
                f"Your last response could not be parsed as a valid action. "
                f"Error: {result.error}. "
                f"Please respond with a JSON object: "
                f'{{"action": "<tool_name>", "parameters": {{...}}}}. '
                f"Make sure all double quotes inside string values are escaped with backslash (\\\")."
            )
            self.retry_parse()
            return
        action = result.action
        if action.name == "finish":
            self.stop_reason = StopReason.SUCCESS
            self._renderer.on_state_change("ACTION_PARSE", "STOP", self.state.iteration)
            self.stop()
            return
        errors = self.validator.validate(action)
        if errors:
            self.state.record_feedback(
                f"Action validation failed: {'; '.join(errors)}. "
                f"Please fix the missing or incorrect parameters and try again."
            )
            self.retry_parse()
            return
        self._pending_action = action
        self._emit("ACTION_CREATED", {"action_name": action.name, "parameters": dict(action.parameters)})
        self._tracer.record(
            ActionEvent(self.state.iteration, action.name, action.parameters)
        )
        self.check_guardrails()

    def _on_guardrail(self) -> None:
        assert self._pending_action is not None
        result = self.guardrails.check(self._pending_action)
        self._pending_guardrail = result
        self._renderer.on_action(self.state.iteration, self._pending_action, result)
        self._tracer.record(
            GuardrailEvent(
                self.state.iteration, result.verdict, result.policy, result.reason
            )
        )
        if result.verdict == "DENY":
            self._emit("GUARDRAIL_DENY", {"policy": result.policy, "reason": result.reason})
            self.deny_action()
        elif result.verdict == "REQUIRE_APPROVAL":
            self._emit("APPROVAL_REQUIRED", {"policy": result.policy, "reason": result.reason})
            self.request_approval()
        else:
            self._emit("GUARDRAIL_PASS", {"policy": result.policy})
            self.execute()

    def _on_wait_approval(self) -> None:
        assert self._pending_action is not None
        assert self._pending_guardrail is not None
        print(f"\n[DANGEROUS ACTION] Policy: {self._pending_guardrail.policy}")
        print(f"Reason: {self._pending_guardrail.reason}")
        print(f"Action: {self._pending_action}")
        answer = input("Approve? (y/n): ").strip().lower()
        if answer == "y":
            self.approve()
        else:
            self.reject()

    def _on_tool_exec(self) -> None:
        assert self._pending_action is not None
        self._emit("TOOL_START", {"tool": self._pending_action.name, "parameters": dict(self._pending_action.parameters)})
        result = self.tools.execute(self._pending_action)
        self._last_tool_result = result
        self._emit("TOOL_END", {"tool": self._pending_action.name, "success": result.success, "output_preview": result.output[:500]})
        self.state.record_turn(self._pending_action, result.output)
        self._renderer.on_tool_exec(
            self.state.iteration, self._pending_action.name, result
        )
        self._tracer.record(
            ToolEvent(
                self.state.iteration,
                self._pending_action.name,
                result.success,
                result.output,
            )
        )
        if result.success:
            self.tool_success()
        else:
            self.tool_error()

    def _on_tool_error(self) -> None:
        if self.state.retry_count < 3:
            self.state.retry_count += 1
            self.retry_tool()
        else:
            self.stop_reason = StopReason.REPEATED_FAILURE
            self.stop()

    def _on_feedback(self) -> None:
        assert self._last_tool_result is not None
        if self.feedback:
            plan = self.feedback.run(self._last_tool_result, self.state.retry_count)
            if plan:
                feedback_msg = (
                    f"Feedback: {plan.strategy}\n"
                    f"Scope: {plan.scope}\n"
                    f"Target files: {plan.target_files}\n"
                    f"Retry count: {plan.retry_count}"
                )
                self.state.record_feedback(feedback_msg)
                self.state.retry_count += 1
                if self.state.retry_count >= 3:
                    self.state.retry_count = 0
                self._renderer.on_feedback(self.state.iteration, True, plan.scope)
                self._tracer.record(
                    FeedbackEvent(self.state.iteration, plan.scope, True)
                )
                self._emit("FEEDBACK_COMPLETED", {"has_plan": True, "scope": plan.scope})
                self.feedback_correct()
                return
        self._renderer.on_feedback(self.state.iteration, False, "")
        self._tracer.record(FeedbackEvent(self.state.iteration, "", False))
        self._emit("FEEDBACK_COMPLETED", {"has_plan": False, "scope": ""})
        self.feedback_done()

    def _on_stop(self) -> None:
        self._emit("AGENT_STOP", {"reason": self.stop_reason.value, "iterations": self.state.iteration})
        self._renderer.on_stop(self.stop_reason, self.state.iteration)

    def _on_memory_update(self) -> None:
        self._emit("MEMORY_WRITE", {})
        self.continue_loop()

    def _emit(self, event_type: str, payload: dict | None = None) -> None:
        if self._event_bus is None:
            return
        self._event_bus.publish(AgentEvent(
            type=event_type,
            iteration=self.state.iteration,
            state=self._fsm_state,
            payload=payload or {},
        ))

    def _build_result(self) -> dict:
        return {
            "status": "success" if self.stop_reason == StopReason.SUCCESS else "failed",
            "reason": self.stop_reason.value,
            "iterations": self.state.iteration,
        }
