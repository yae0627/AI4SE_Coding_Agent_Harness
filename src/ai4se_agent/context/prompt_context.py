from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai4se_agent.context.workspace import WorkspaceSnapshot
    from ai4se_agent.types import Plan


@dataclass
class PromptContext:
    tools: list[dict]
    goal: str
    workspace: WorkspaceSnapshot | None = None
    rules: list[str] = field(default_factory=list)
    feedback: list[dict] = field(default_factory=list)
    plan: Plan | None = None
