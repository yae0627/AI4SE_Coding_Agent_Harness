from ai4se_agent.context.prompt_context import PromptContext
from ai4se_agent.context.prompt_section import PromptSection


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
        current = plan.current_step()
        if current and current.status == "in_progress":
            lines.append(f"Current step: {current.description}")
            lines.append("Execute this step using tool calls (write_file, shell, etc).")
            lines.append("When done, call plan_update to mark it done.")
        elif current and current.status == "pending":
            lines.append("Call plan_update to start the first step, then execute it.")
        elif plan.completed():
            lines.append("All steps completed — call finish to end the task.")
        else:
            lines.append("Use plan_update to mark steps as in_progress, done, or failed.")
        return "\n".join(lines)
