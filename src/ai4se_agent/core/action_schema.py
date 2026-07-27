"""Control action schemas — actions handled by FSM, not ToolRegistry.

These are merged into the LLM prompt so the model knows about ask/finish
alongside the dynamically-registered tool schemas.
"""

CONTROL_SCHEMAS = [
    {
        "name": "plan_create",
        "_category": "control",
        "description": "Create a step-by-step plan for a complex task. Break the task into clear, actionable steps. Call this at the start of a multi-step task.",
        "parameters": {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ordered list of step descriptions"
                }
            },
            "required": ["steps"]
        }
    },
    {
        "name": "plan_update",
        "_category": "control",
        "description": "Update a plan step's status. Call this when starting a step or after completing/failing one.",
        "parameters": {
            "type": "object",
            "properties": {
                "step_index": {"type": "integer", "description": "0-based index of the step to update"},
                "status": {
                    "type": "string",
                    "enum": ["in_progress", "done", "failed"],
                    "description": "New status for the step"
                }
            },
            "required": ["step_index", "status"]
        }
    },
    {
        "name": "ask",
        "_category": "control",
        "description": "Ask the user a question and wait for their response. Use this when you need clarification, a decision, or additional information before proceeding.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The question to ask the user"}
            },
            "required": ["question"]
        }
    },
    {
        "name": "finish",
        "_category": "control",
        "description": "Complete the current task. Use the message field to summarize what was accomplished.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
]
