# Task 10 Report: State Machine + Integration

## Status: DONE_WITH_CONCERNS

## Files Created
- `src/ai4se_agent/core/state_machine.py` — `HarnessStateMachine` (11-state FSM)
- `tests/core/test_state_machine.py` — integration test

No existing files were modified (the `core/__init__.py` and `tests/core/__init__.py` were left untouched as instructed).

## TDD Cycle

### RED (Step 2)
Wrote the test file verbatim from the brief. Ran `pytest tests/core/test_state_machine.py -v`:
- Result: **FAILED** (collection error)
- Reason: `ModuleNotFoundError: No module named 'ai4se_agent.core.state_machine'`
- This is the expected, correct RED failure (feature missing, not a typo).

### GREEN (Step 4)
Wrote the implementation from the brief. The exact brief code did **not** pass on its own — two bugs in the brief's code required minimal root-cause fixes (see Concerns). After the fixes:
- `pytest tests/core/test_state_machine.py -v` → **1 passed**
- Full suite `pytest -q` → **47 passed** (no regressions)

### Lint (Step 5)
`ruff check src/ai4se_agent/core/state_machine.py tests/core/test_state_machine.py` → **All checks passed!** (exit 0)
- Required removing 5 unused imports (F401) present in the brief's exact code (see Concerns).

## Commit
- Hash: `6d3320b` (full: `6d3320bb1a32d338b16be7147ebac39efb68b042`)
- Message: `feat: add HarnessStateMachine - 11-state FSM with transitions`
- Files: 2 files changed, 197 insertions(+)

## AGENT_LOG
Appended via `python scripts/log_agent.py`:
`| 2026-07-21 17:18 | #task-10 | state-machine | Add HarnessStateMachine - 11-state FSM with transitions | - | 6d3320b |`

## Concerns / Deviations from the Brief's Exact Code

The brief's exact implementation code contained **two runtime bugs** and **lint violations** that prevented Step 4 ("verify it PASSES") and Step 5 ("verify no lint errors") from succeeding. Per the TDD discipline (fix code, not test) and systematic-debugging (fix root cause), I made the minimal root-cause fixes. Each deviation is documented below. No features, error handling, or comments were added.

### Concern 1: `self.state` name collision with the `transitions` library (runtime bug)
- **Root cause:** The `transitions` library's `Machine(model=self, ...)` sets `model.state` to the current FSM state string (default `model_attribute="state"`). The brief's code also uses `self.state` to hold the `AgentState` instance (`self.state = agent_state`). The `Machine(...)` call in `__init__` therefore **overwrites** `self.state` (AgentState) with the string `"IDLE"`, so every `self.state.<AgentState method>` call (e.g. `self.state.increment_iteration()`) raised `AttributeError: 'str' object has no attribute 'increment_iteration'`.
- **Evidence:** Confirmed empirically — after `Machine(model=self, ...)`, `type(self.state)` is `str`.
- **Minimal fix (1 line):** Added `model_attribute="_fsm_state"` to the `Machine(...)` constructor so the FSM tracks its state in `self._fsm_state`, leaving `self.state` as the `AgentState`. This is a supported parameter in `transitions` 0.9.3 (verified via `inspect.signature`).
- **Alternative considered:** Renaming all `self.state` (AgentState) references to `self.agent_state`. Rejected as more invasive than the one-parameter fix.

### Concern 2: `stop` transition only defined from `MEMORY_UPDATE` (runtime bug)
- **Root cause:** The brief defines `add_transition("stop", "MEMORY_UPDATE", "STOP")`, but `self.stop()` is called from `CONTEXT_ORG` (max iterations), `LLM_CALL` (error_count >= 3), `ACTION_PARSE` ([DONE]), and `TOOL_ERROR` (retry_count >= 3). With `auto_transitions=False` and `ignore_invalid_triggers` left at default (False), calling `self.stop()` from any state other than `MEMORY_UPDATE` raises `transitions.core.MachineError: "Can't trigger event stop from state <X>!"`. In the test path this surfaces in `_on_tool_error` (state `TOOL_ERROR`) after the empty `ToolRegistry` fails 3×.
- **Evidence:** After fixing Concern 1, the test failed with `MachineError: "Can't trigger event stop from state TOOL_ERROR!"`.
- **Minimal fix (1 line):** Changed the source from `"MEMORY_UPDATE"` to the wildcard `"*"`: `add_transition("stop", "*", "STOP")`. This is the standard `transitions`-library idiom for a terminal transition reachable from any state, and is a strict superset of the original (still allows `stop` from `MEMORY_UPDATE`).

### Concern 3: Unused imports (F401) in the brief's exact code
- The brief's Step 5 explicitly requires "verify no lint errors" and the Global Constraints require "Lint must pass (ruff)". The brief's exact code imported but never referenced:
  - `GuardrailResult` in `state_machine.py` (only `StopReason` is used)
  - `FeedbackLoop`, `FailureClassifier`, `CorrectionPlanner`, `TestSensor` in `test_state_machine.py` (none referenced by the test body)
- **Minimal fix:** Removed the 5 unused imports. This removes code (does not add features, error handling, or comments) and satisfies the brief's explicit lint requirement. Adding `# noqa` comments was rejected because the brief forbids adding comments.

### Note: `run()` line `self.state.current_state = self.state`
- This line in the brief is semantically odd (it assigns the `AgentState` object to its own `current_state` str field). With the Concern 1 fix in place it does **not** raise and does not affect the test (the test does not inspect `current_state`). Per systematic-debugging's "ONE change at a time / no while-I'm-here improvements" rule, I left this line verbatim from the brief rather than "fixing" it, since it is not a root cause of any test failure.

## Verification Summary
| Check | Command | Result |
|-------|---------|--------|
| RED | `pytest tests/core/test_state_machine.py -v` | FAILED (ModuleNotFoundError) ✓ expected |
| GREEN | `pytest tests/core/test_state_machine.py -v` | 1 passed ✓ |
| Regression | `pytest -q` | 47 passed ✓ |
| Lint | `ruff check <2 files>` | All checks passed! ✓ |
| Commit | `git log --oneline -1` | 6d3320b ✓ |
| Log | `python scripts/log_agent.py ...` | Appended ✓ |
