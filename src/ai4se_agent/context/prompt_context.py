from dataclasses import dataclass, field


@dataclass
class PromptContext:
    tools: list[dict]
    goal: str
    workspace: "WorkspaceSnapshot | None" = None
    rules: list[str] = field(default_factory=list)
    feedback: list[dict] = field(default_factory=list)
