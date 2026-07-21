# Task 11 Report — CLI Entry Point

**Status:** DONE_WITH_CONCERNS
**Commit:** `820c07a`
**Branch:** `feat/core-shared-types`

## Files Created/Modified

| File | Action | Notes |
|------|--------|-------|
| `src/ai4se_agent/cli.py` | Created | Verbatim from brief Step 1 (incl. `# src/ai4se_agent/cli.py` filename comment, matching existing convention in `state_machine.py`). Defines `build_harness(task, workspace=".")` and `main()`. |
| `tests/test_cli.py` | Created | Based on brief Step 2, with one minimal, sanctioned deviation (see Concerns). |
| `pyproject.toml` | NOT modified | Verified `[project.scripts]` entry point already present at line 26-27: `ai4se-agent = "ai4se_agent.cli:main"`. Per task instructions, not re-added. |

## TDD Cycle

### RED — test written first (before `cli.py` existed)
Ran `pytest tests/test_cli.py -v`:
```
ModuleNotFoundError: No module named 'ai4se_agent.cli'
1 error during collection
```
Confirmed RED (test fails because implementation does not exist).

### GREEN — wrote `cli.py` (verbatim from brief), then re-ran test
First run with the **exact** brief test code FAILED:
```
openai.OpenAIError: Missing credentials. Please pass an `api_key`, ... or set the `OPENAI_API_KEY` ...
```
Root cause: `ConfigLoader().get_provider()` defaults to `"openai"` (no `.env` file, `LLM_PROVIDER` unset, `OPENAI_API_KEY` unset), so `build_harness` eagerly constructs `OpenAIAdapter(api_key=None, base_url=None)`, and `OpenAIAdapter.__init__` calls `OpenAI(api_key=None)` which validates credentials and raises. This violates the global constraint *"All core mechanisms must be testable with mock LLM (no network, no real LLM)"*.

After the minimal test adaptation (see Concerns), re-ran:
```
tests/test_cli.py::test_build_harness_creates_machine PASSED
1 passed in 1.02s
```

### Full suite (regression check)
Ran `pytest` (all tests):
```
48 passed in 1.69s
```
Including `tests/config/test_loader.py` (2 tests) — confirms the scoped `monkeypatch` did not leak into other tests (e.g. `test_config_returns_defaults` still asserts provider defaults to `"openai"`).

## Lint Results
Ran `ruff check src/ai4se_agent/cli.py tests/test_cli.py`:
```
All checks passed!
```

## Commit
```
820c07a feat: add CLI entry point and harness builder
 2 files changed, 93 insertions(+)
 create mode 100644 src/ai4se_agent/cli.py
 create mode 100644 tests/test_cli.py
```
Staged exactly the two files specified in brief Step 4 (`git add src/ai4se_agent/cli.py tests/test_cli.py`). Commit message used verbatim from brief.

## AGENT_LOG
Ran: `python scripts/log_agent.py "#task-11" "cli" "Add CLI entry point and harness builder" "-"`
Appended:
```
| 2026-07-21 17:29 | #task-11 | cli | Add CLI entry point and harness builder | - | 820c07a |
```

## Concerns / Issues Encountered

### 1. Brief test code fails without `LLM_PROVIDER=mock` (resolved with minimal test adaptation)
The brief's exact `build_harness` reads the LLM provider from `ConfigLoader` (env/`.env`). With no `.env` file and no `LLM_PROVIDER` env var, `get_provider()` returns the default `"openai"`, and the `else` branch eagerly builds `OpenAIAdapter(api_key=None, ...)` → `OpenAI(api_key=None)` raises `OpenAIError: Missing credentials`. This makes the brief's exact test (`pytest tests/test_cli.py -v`) fail on a plain invocation, contradicting brief Step 3 ("Expected: PASS") and the global mock-testability constraint.

**Resolution:** Kept `build_harness` and `main()` **100% verbatim** from the brief (no extra features/error-handling/comments added). Adapted the test minimally by adding the `monkeypatch` fixture and one line:
```python
def test_build_harness_creates_machine(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    harness = build_harness("test task", workspace="/tmp")
    ...
```
This mirrors the existing pattern in `tests/config/test_loader.py:7-9` (`test_config_accepts_env_override` uses `monkeypatch.setenv`). It is scoped to the single test (verified: `test_config_returns_defaults` still passes), requires no network/credentials, and is the standard pytest idiom for environment-dependent code. This is the same kind of environment-driven adaptation the task note explicitly sanctions for the `/tmp` workspace case.

**Alternative considered & rejected:**
- Setting `LLM_PROVIDER=mock` in the shell before pytest — fragile, won't work in CI or for other developers; brief Step 3 expects a plain `pytest` invocation to pass.
- A global `conftest.py` setting `LLM_PROVIDER=mock` — would break `test_config_returns_defaults` (asserts provider defaults to `"openai"`).
- Modifying `build_harness` to fall back to mock when `api_key` is `None` — explicitly forbidden by the task ("Use the EXACT code from the brief — do not add extra features, error handling").
- Creating a `.env` file with `LLM_PROVIDER=mock` — `.env` is gitignored, not a deliverable, and wouldn't work in CI.

### 2. `workspace="/tmp"` on Windows — no issue encountered
The task note anticipated `/tmp` might not exist on Windows. `WorkspacePolicy.__init__` only calls `os.path.realpath(workspace)`, which returns a path string without requiring the directory to exist. The test never calls `harness.run()`, so no guardrail `check()` runs. No change needed; the exact `workspace="/tmp"` value was retained.

### 3. `PersistentMemory()` side effect
`build_harness` constructs `PersistentMemory()`, which creates `memory/project_rules/` and `memory/session_summaries/` directories in the CWD. These are gitignored (`/memory/` in `.gitignore`) and were not committed. No impact.

## Verification Summary
- Test (target): 1/1 passing
- Test (full suite): 48/48 passing
- Lint: clean
- Entry point in `pyproject.toml`: present (pre-existing), unmodified
- Commit: `820c07a`
- AGENT_LOG: appended
