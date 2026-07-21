# Task 12 Review: Mechanism Demo

## 1. Spec Compliance: ✅

**Files created (commit `c0015a9`):**
- `demo/mechanism_demo.py` (108 lines) — matches brief exactly, minus 4 ruff F541 fixes
- `demo/README.md` (19 lines) — present, describes the 5 demos and how to run

**All 5 demos present and matching the brief:**
1. `demo_guardrail()` — `CommandPolicy` denies `rm -rf /` ✓
2. `demo_feedback_loop()` — `TestSensor` → `FailureClassifier` → `CorrectionPlanner` ✓
3. `demo_incremental_correction()` — 3 retries, escalation to full replan ✓
4. `demo_failure_db()` — `FailureDB` record + query_similar ✓
5. `demo_workspace_policy()` — `WorkspacePolicy` denies `..` path escape ✓

**F541 lint fix (justified):** The brief's code had 4 `print(f"...")` statements with no placeholders, violating ruff F541. The implementer applied `ruff --fix` to remove the unnecessary `f` prefixes. This is behavior-preserving (byte-identical stdout) and required by the brief's own Global Constraint "Lint must pass (ruff)". The 4 changed lines:
- `print("  Action: shell rm -rf /")`
- `print("  Tool result: FAILED (exit code 1)")`
- `print("  Recorded failure: logic_error")`
- `print("  Action: read_file ../../etc/passwd")`

**No over-building:** No files outside `demo/` were added by the implementer's commit. `demo/README.md` content is appropriate and not excessive.

**FailureDB fix (commit `2720ca1`, controller-applied):** The implementer's report correctly identified a pre-existing Windows-only bug in `src/ai4se_agent/feedback/failure_db.py` (SQLite connection leak via `with sqlite3.connect()` which only manages transactions, not connection lifecycle). The controller applied the recommended fix in a separate commit, which is the correct scope separation (bugfix vs. feature task).

## 2. Code Quality: Approved

**Demo script:**
- Clean, follows Python conventions, no unnecessary comments (only the brief-mandated docstring and the `# demo/mechanism_demo.py` path comment from the brief)
- All 5 demos demonstrate the correct behaviors
- No mock LLM/network dependency — uses only deterministic components (`TestSensor`, `FailureClassifier`, `CorrectionPlanner`, `FailureDB`, `CommandPolicy`, `WorkspacePolicy`)
- No agent orchestration frameworks used

**FailureDB fix (`src/ai4se_agent/feedback/failure_db.py`):**
- Correct pattern: `conn = sqlite3.connect(...)` + `try/finally: conn.close()`
- Explicit `conn.commit()` replaces the implicit transaction commit that `with` previously provided
- Cross-platform correctness fix (the bug was masked on Linux where open files can be deleted)
- No regression — `tests/feedback/test_failure_db.py` still passes

**Verification results (run during review):**
- `python demo/mechanism_demo.py` → all 5 demos print PASS, ending with `=== All demos passed ===` (Demo 5 now runs in the full script after the FailureDB fix)
- `ruff check demo/ src/ai4se_agent/feedback/failure_db.py` → `All checks passed!`
- `python -m pytest tests/ -q` → 48 passed
- `python -m pytest tests/feedback/test_failure_db.py -v` → 1 passed

## 3. Findings

### Critical
- None

### Important
- None

### Minor
1. **AGENT_LOG missing entry for commit `2720ca1`.** Per `AGENTS.md` §4, every task/commit must be logged. The controller's FailureDB fix commit (`2720ca1`) has no corresponding AGENT_LOG entry — only the implementer's `c0015a9` is logged. Recommend appending a row for the bugfix (e.g., `#task-12 | fix | Close SQLite connections explicitly in FailureDB to prevent Windows file lock | controller fix for Windows cleanup crash | 2720ca1`).
2. **Report's "Demo 5 not reached" is stale post-fix.** The implementer's report states Demo 5 is "not reached" in the full run. This was accurate at report time (before the controller's fix), but after commit `2720ca1` the full script runs end-to-end with all 5 demos passing. Not a code issue — just noting the report predates the fix.

## 4. Verdict: Approved

The Task 12 deliverable matches the brief (with the justified, behavior-preserving F541 lint fix), all 5 demos pass end-to-end, lint passes, and all 48 tests pass. The controller's FailureDB fix is a correct, well-scoped bugfix that resolves the Windows connection-leak issue identified in the implementer's report. The only finding is a minor process gap (missing AGENT_LOG entry for the fix commit).
