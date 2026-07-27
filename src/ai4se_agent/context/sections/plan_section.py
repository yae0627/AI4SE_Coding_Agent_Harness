from ai4se_agent.context.prompt_section import PromptSection
from ai4se_agent.context.prompt_context import PromptContext


class PlanSection(PromptSection):
    def build(self, ctx: PromptContext) -> str:
        plan = ctx.plan
        if not plan or not plan.steps:
            return ""

        markers = {"pending": "[ ]", "in_progress": "[>]", "done": "[x]", "failed": "[!]"}
        lines = ["## Plan Progress"]
        for i, step in enumerate(plan.steps):
            m = markers.get(step.status, "[?]")
            lines.append(f"  {i+1}. {m} {step.description}")
        lines.append("")
        lines.append("Use plan_update to mark steps as in_progress, done, or failed.")
        if plan.completed():
            lines.append("All steps completed — call finish to end the task.")
        return "\n".join(lines)
