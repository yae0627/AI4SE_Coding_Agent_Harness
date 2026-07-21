# Task 12 Report: Mechanism Demo

## Status: DONE_WITH_CONCERNS

## Files Created

| File | Description |
|------|-------------|
| `demo/mechanism_demo.py` | Demo script exercising 5 core mechanisms (guardrail, feedback loop, incremental correction, FailureDB, workspace policy). |
| `demo/README.md` | Short markdown explaining the 5 demos and how to run them. |

No files outside `demo/` were modified by this task. `AGENT_LOG.md` was updated by `scripts/log_agent.py` (step 7) and left uncommitted, per the dispatcher's flow.

## Demo Run Results

Command: `python demo/mechanism_demo.py`

| Demo | Result (full run) | Result (isolated) |
|------|------------------|-------------------|
| 1. Guardrail Intercepts Dangerous Action | PASS | PASS |
| 2. Feedback Loop Detects Failure and Generates Correction | PASS | PASS |
| 3. Incremental Correction Strategy (重点维度) | PASS | PASS |
| 4. FailureDB Records and Queries Failure Patterns | PASS (logic) | PASS |
| 5. WorkspacePolicy Blocks Path Escape | **not reached** | PASS |

**Summary: 5/5 demo logics pass.** Demos 1-4 print PASS in the full run. Demo 5 prints PASS when run in isolation (verified separately). The full script does not complete in a single Windows run because Demo 4's `tempfile.TemporaryDirectory()` cleanup raises `PermissionError: [WinError 32]` before Demo 5 executes. See Concern #1.

## Lint Results

Command: `ruff check demo/`

- **Initial run**: 4 errors — `F541 f-string without any placeholders` on 4 `print(f"...")` lines that came verbatim from the brief (lines printing static text with no `{}` placeholders).
- **Fix applied**: `ruff check demo/ --fix` removed the 4 unnecessary `f` prefixes. This is purely cosmetic (output is byte-identical) and does not add features, error handling, or comments.
- **Final run**: `All checks passed!`

Rationale: the brief's Global Constraints require "Lint must pass (ruff)", and the dispatcher's step 5 requires "verify no lint errors". The brief's exact code violated its own lint constraint, so the minimal behavior-preserving fix was applied. See Concern #2.

## Commit

- Hash: `c0015a9`
- Message: `feat: add mechanism demo for guardrail, feedback, correction, failure DB, workspace policy`
- Files in commit: `demo/README.md`, `demo/mechanism_demo.py` (2 files, 127 insertions)

## Agent Log

`scripts/log_agent.py` appended:
```
| 2026-07-21 17:37 | #task-12 | demo | Add mechanism demo for guardrail, feedback, correction, failure DB, workspace policy | - | c0015a9 |
```

## Concerns

### Concern #1 (Windows): FailureDB leaks SQLite connections → TemporaryDirectory cleanup crashes

**Symptom**: Running `python demo/mechanism_demo.py` on Windows prints PASS for Demos 1-4, then crashes during Demo 4's `with tempfile.TemporaryDirectory() as tmp:` exit:
```
PermissionError: [WinError 32] 另一个程序正在使用此文件，进程无法访问。: '...\\failure.db'
```
Demo 5 never runs in the full script.

**Root cause** (pre-existing, in `src/ai4se_agent/feedback/failure_db.py`, NOT in the demo):
`FailureDB._init_db / record_failure / query_similar` each use `with sqlite3.connect(self._db_path) as conn:`. In Python's `sqlite3`, the `with` context manager only manages the transaction (commit/rollback) — it does **not** close the connection. The connection objects go out of scope but are not deterministically closed until garbage collection. On Linux, open files can still be deleted, so `TemporaryDirectory` cleanup succeeds. On Windows, open file handles block deletion, so cleanup raises `WinError 32`.

**Verification**: After `gc.collect()`, the same temp directory cleans up successfully — confirming the connection is the only open handle.

**Demo 5 verification (isolated)**: Running Demo 5's logic standalone on Windows prints PASS:
```
workspace=C:\Users\11053\AppData\Local\Temp\tmpXXXX
real_path=C:\Users\11053\AppData\Local\etc\passwd
verdict=DENY
reason=Path escapes workspace: C:\Users\11053\AppData\Local\etc\passwd
PASS: WorkspacePolicy blocked path escape
```
So the dispatcher's flagged Windows path-escape concern is **not** an issue — `WorkspacePolicy` correctly denies the escape on Windows because `os.path.realpath` resolves `tmp/../../etc/passwd` to a path outside the workspace.

**Why not fixed here**: Task 12's brief restricts changes to 2 demo files and requires exact demo code. The dispatcher states "Tasks 1-11 are ALL complete". Modifying `FailureDB` is out of scope for Task 12. The demo code itself is correct per the brief.

**Recommended follow-up fix** (for a separate task/bugfix): in `FailureDB`, explicitly close connections, e.g.:
```python
with sqlite3.connect(self._db_path) as conn:
    conn.execute(...)
    conn.close()   # or use try/finally
```
or restructure to use a single long-lived connection that is closed in a `__del__`/`close()` method. This is a cross-platform correctness bug, not a Windows-specific quirk — it is simply masked on Linux.

### Concern #2: Brief code had ruff F541 violations

The brief's exact demo code contained 4 `print(f"...")` statements with no placeholders, which ruff flags as `F541`. The brief's Global Constraints require "Lint must pass (ruff)". To resolve the conflict, `ruff --fix` removed the 4 unnecessary `f` prefixes. The change is behavior-preserving (identical stdout) and does not add features, error handling, or comments. The committed `demo/mechanism_demo.py` therefore differs from the brief by exactly 4 removed `f` prefixes.

## Verification Checklist

- [x] `demo/` directory created
- [x] `demo/mechanism_demo.py` written (brief code + 4 ruff F541 fixes)
- [x] `demo/README.md` written
- [x] Demo run: 5/5 demo logics PASS (Demos 1-4 in full run, Demo 5 in isolation)
- [x] `ruff check demo/` passes (0 errors)
- [x] Committed with exact brief message → `c0015a9`
- [x] `scripts/log_agent.py` ran, AGENT_LOG.md updated with `c0015a9`
