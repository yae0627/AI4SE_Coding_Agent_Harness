# src/ai4se_agent/core/state_machine.py
from transitions import Machine
from ai4se_agent.core.agent_state import AgentState
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.llm.base import LLMAdapter
from ai4se_agent.tools.registry import ToolRegistry
from ai4se_agent.guardrails.engine import GuardrailEngine
from ai4se_agent.feedback.loop import FeedbackLoop
from ai4se_agent.memory.manager import MemoryManager
from ai4se_agent.types import StopReason


class HarnessStateMachine:
    states = [
        "IDLE", "CONTEXT_ORG", "LLM_CALL", "ACTION_PARSE",
        "GUARDRAIL", "WAIT_APPROVAL", "TOOL_EXEC", "TOOL_ERROR",
        "FEEDBACK", "MEMORY_UPDATE", "STOP"
    ]

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
        self._pending_action = None
        self._pending_guardrail = None

        self.machine = Machine(
            model=self,
            states=HarnessStateMachine.states,
            initial="IDLE",
            auto_transitions=False,
            model_attribute="_fsm_state",
        )

        self.machine.add_transition("start", "IDLE", "CONTEXT_ORG", after="_on_context_org")
        self.machine.add_transition("retry_context", "CONTEXT_ORG", "CONTEXT_ORG", after="_on_context_org")
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
        self.machine.add_transition("stop", "*", "STOP")

    def run(self) -> dict:
        self.start()
        self.state.current_state = self.state
        return self._build_result()

    def _on_context_org(self) -> None:
        self.state.increment_iteration()
        if self.state.iteration > self.max_iterations:
            self.stop_reason = StopReason.MAX_ITERATION
            self.stop()
            return
        self.call_llm()

    def _on_llm_call(self) -> None:
        try:
            messages = self.state.context
            response = self.llm.generate(messages)
            self.state.context.append({"role": "assistant", "content": response})
            self.parse_action()
        except Exception:
            self.state.error_count += 1
            if self.state.error_count >= 3:
                self.stop_reason = StopReason.LLM_ERROR
                self.stop()
            else:
                self.retry_context()

    def _on_action_parse(self) -> None:
        last_msg = self.state.context[-1]["content"]
        if "[DONE]" in last_msg:
            self.stop_reason = StopReason.SUCCESS
            self.stop()
            return
        action = self.parser.parse(last_msg)
        if action is None:
            self.retry_parse()
            return
        errors = self.validator.validate(action)
        if errors:
            self.retry_parse()
            return
        self._pending_action = action
        self.check_guardrails()

    def _on_guardrail(self) -> None:
        result = self.guardrails.check(self._pending_action)
        self._pending_guardrail = result
        if result.verdict == "DENY":
            self.deny_action()
        elif result.verdict == "REQUIRE_APPROVAL":
            self.request_approval()
        else:
            self.execute()

    def _on_wait_approval(self) -> None:
        print(f"\n[DANGEROUS ACTION] Policy: {self._pending_guardrail.policy}")
        print(f"Reason: {self._pending_guardrail.reason}")
        print(f"Action: {self._pending_action}")
        answer = input("Approve? (y/n): ").strip().lower()
        if answer == "y":
            self.approve()
        else:
            self.reject()

    def _on_tool_exec(self) -> None:
        result = self.tools.execute(self._pending_action)
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
        if self.feedback:
            plan = self.feedback.run(None, self.state.retry_count)
            if plan:
                self.state.retry_count += 1
                if self.state.retry_count >= 3:
                    self.state.retry_count = 0
                self.feedback_correct()
                return
        self.feedback_done()

    def _on_memory_update(self) -> None:
        self.continue_loop()

    def _build_result(self) -> dict:
        return {
            "status": "success" if self.stop_reason == StopReason.SUCCESS else "failed",
            "reason": self.stop_reason.value,
            "iterations": self.state.iteration,
        }
