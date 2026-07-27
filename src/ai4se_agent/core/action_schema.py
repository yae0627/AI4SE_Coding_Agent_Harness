"""Control action schemas — actions handled by FSM, not ToolRegistry.

These are merged into the LLM prompt so the model knows about ask/finish
alongside the dynamically-registered tool schemas.
"""

CONTROL_SCHEMAS = [
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
