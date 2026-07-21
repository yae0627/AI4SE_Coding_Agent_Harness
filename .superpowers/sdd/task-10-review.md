# Task 10 Review: State Machine + Integration

## 1. Spec Compliance: ✅

The implementation matches the brief exactly, minus the 3 documented root-cause fixes. Independent verification confirms all claims.

### States (11/11 present)
IDLE, CONTEXT_ORG, LLM_CALL, ACTION_PARSE, GUARDRAIL, WAIT_APPROVAL, TOOL_EXEC, TOOL_ERROR, FEEDBACK, MEMORY_UPDATE, STOP — ✅ all present (`state_machine.py:14-18`)

### Transitions (18/18 correct)
All 18 transitions from the brief are present and match exactly, with the one documented deviation:
- `stop` transition: brief specifies `add_transition("stop", "MEMORY_UPDATE", "STOP")`; implementation uses `add_transition("stop", "*", "STOP")` (Fix 2 — wildcard). This is a strict superset (still allows `stop` from `MEMORY_UPDATE`) and is the standard `transitions`-library idiom for a terminal transition. ✅

### run() method
Matches brief verbatim, including the semantically odd line `self.state.current_state = self.state` (see Findings #1). ✅

### _on_* callbacks (10/10 correct)
`_on_context_org`, `_on_llm_call`, `_on_action_parse`, `_on_guardrail`, `_on_wait_approval`, `_on_tool_exec`, `_on_tool_error`, `_on_feedback`, `_on_memory_update`, `_build_result` — all match the brief verbatim. ✅

### Test
Matches the brief verbatim, minus the 4 unused imports removed (Fix 3). The test body is identical. ✅

### Over-building check
No extra features, methods, states, transitions, error handling, or comments added beyond the brief. The only changes are the 3 documented fixes. ✅

### Missing from spec
Nothing missing. ✅

## 2. Code Quality: Approved

### The 3 fixes are correct and minimal

**Fix 1 — `model_attribute="_fsm_state"` (`state_machine.py:50`):** Correct root-cause fix. The `transitions` library's `Machine(model=self, ...)` overwrites `model.state` with the FSM state string by default, colliding with the brief's `self.state = agent_state`. Using `model_attribute="_fsm_state"` relocates the FSM's state tracking to `self._fsm_state`, leaving `self.state` as the `AgentState`. This is a supported parameter (verified working — test passes). 1-line change, less invasive than renaming all `self.state` references. ✅

**Fix 2 — `add_transition("stop", "*", "STOP")` (`state_machine.py:70`):** Correct root-cause fix. The brief defines `stop` only from `MEMORY_UPDATE`, but `self.stop()` is called from `CONTEXT_ORG` (max iterations), `LLM_CALL` (error_count >= 3), `ACTION_PARSE` ([DONE]), and `TOOL_ERROR` (retry_count >= 3). With `auto_transitions=False`, calling `stop()` from any other state raises `MachineError`. The wildcard `"*"` is the standard idiom for a terminal transition and is a strict superset of the original. ✅

**Fix 3 — Remove unused imports:** Correct. The brief's Step 5 explicitly requires "verify no lint errors" and Global Constraints require "Lint must pass (ruff)". The brief's exact code imported `GuardrailResult` (unused in `state_machine.py`) and `FeedbackLoop`, `FailureClassifier`, `CorrectionPlanner`, `TestSensor` (unused in the test). Removing them satisfies the lint requirement without adding features or comments. ✅

### Code conventions
- Clean, readable Python ✅
- Type hints present on `__init__` and method signatures ✅
- No comments added beyond the brief-specified file-path headers ✅
- Follows the project's existing style ✅

### Independent verification (reproduced)
| Check | Command | Result |
|-------|---------|--------|
| Test | `pytest tests/core/test_state_machine.py -v` | 1 passed ✅ |
| Regression | `pytest -q` | 47 passed ✅ |
| Lint | `ruff check <2 files>` | All checks passed! ✅ |
| Commit | `git log --oneline -1` | 6d3320b ✅ |

### Test path trace (verified against dependencies)
1. `run()` → `start()` → `_on_context_org`: iteration=1, 1≤5 → `call_llm()`
2. `_on_llm_call`: MockAdapter returns `"action: read_file path=test.txt"`, appended → `parse_action()`
3. `_on_action_parse`: no `"[DONE]"`, parser produces `Action`, validator passes → `check_guardrails()`
4. `_on_guardrail`: empty `GuardrailEngine` returns `ALLOW` → `execute()`
5. `_on_tool_exec`: empty `ToolRegistry` → `ToolResult(success=False)` → `tool_error()`
6. `_on_tool_error`: retry_count 0→1→2→3, each retry fails; at retry_count=3 → `stop(REPEATED_FAILURE)`
7. `run()` returns `{"status": "failed", ...}` → assertion `status in ("success","failed")` passes ✅

## 3. Findings

### Critical
None.

### Important
None.

### Minor

1. **`run()` line `self.state.current_state = self.state` (`state_machine.py:74`)** — This line assigns the `AgentState` object to its own `current_state` field (typed `str` in `agent_state.py:10`). It is semantically wrong but does not raise at runtime (Python is dynamically typed) and does not affect the test (test does not inspect `current_state`). This is a latent bug **inherited from the brief**, not introduced by the implementer. The implementer correctly flagged it in their report (the "Note" section) and left it verbatim per systematic-debugging's "no while-I'm-here improvements" rule. **Recommendation: flag for the spec author; do not block this task.**

2. **Test coverage is weak (`test_state_machine.py:27`)** — The assertion `result["status"] in ("success", "failed")` would pass for almost any terminal behavior. The success path (reaching `"[DONE]"` → `StopReason.SUCCESS`) is never exercised because the empty `ToolRegistry` causes 4 tool failures → `REPEATED_FAILURE` → `"failed"`. The second MockAdapter response (`"[DONE]"`) is never consumed. This matches the brief exactly, so it is a spec limitation, not an implementation defect. **Recommendation: consider strengthening in a future task; do not block this task.**

3. **(Informational) `_on_wait_approval` uses blocking `input()` (`state_machine.py:130`)** — This callback blocks on stdin and is not testable with the mock-LLM approach. The test path does not reach this state (empty `GuardrailEngine` returns `ALLOW`), so it does not affect the test. Inherited from the brief; approval-flow testing would require stdin mocking, which is out of scope. No action required for this task.

## 4. Verdict: Approved

The implementation correctly matches the brief (minus the 3 documented root-cause fixes). All 11 states, 18 transitions, 10 callbacks, `run()`, and `_build_result()` are present and correct. The test matches the brief. All tests pass (1/1 targeted, 47/47 full suite), lint passes, no regressions, no over-building, nothing missing.

The 3 fixes are legitimate root-cause fixes (not feature additions), each minimal and well-justified:
- Fix 1 resolves a real runtime collision (`self.state` overwritten by `transitions` library)
- Fix 2 resolves a real `MachineError` (terminal transition unreachable from non-`MEMORY_UPDATE` states)
- Fix 3 satisfies the brief's explicit lint requirement

The minor findings are all inherited from the brief and were correctly left alone by the implementer per TDD/systematic-debugging discipline.
