# Mechanism Demo

This directory contains a demonstration script (`mechanism_demo.py`) that exercises five core mechanisms of the AI4SE Coding Agent Harness without requiring a network or real LLM.

## What it demonstrates

1. **Guardrail Intercepts Dangerous Action** — `CommandPolicy` denies a destructive shell command (`rm -rf /`).
2. **Feedback Loop Detects Failure and Generates Correction** — `TestSensor` observes a failing `ToolResult`, `FailureClassifier` classifies it, and `CorrectionPlanner` produces a `CorrectionPlan`.
3. **Incremental Correction Strategy (重点维度)** — Shows the feedback loop running across three retry attempts, illustrating the escalation from incremental fixes toward a full replan.
4. **FailureDB Records and Queries Failure Patterns** — `FailureDB` persists a failure pattern to SQLite and retrieves similar patterns by type.
5. **WorkspacePolicy Blocks Path Escape** — `WorkspacePolicy` denies a `read_file` action whose path escapes the workspace root via `..` traversal.

## Running

```bash
python demo/mechanism_demo.py
```

Expected output: each of the five demos prints `PASS`, followed by `=== All demos passed ===`.
