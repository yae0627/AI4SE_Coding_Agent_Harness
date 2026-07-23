from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai4se_agent.context.workspace import WorkspaceSnapshot


@dataclass
class PromptContext:
    tools: list[dict]
    goal: str
    workspace: "WorkspaceSnapshot | None" = None  # noqa: F821  # forward ref, resolved at runtime by PromptComposer
    rules: list[str] = field(default_factory=list)
    feedback: list[dict] = field(default_factory=list)
