"""Control action schemas — actions handled by FSM, not ToolRegistry.

These are merged into the LLM prompt so the model knows about respond/finish
alongside the dynamically-registered tool schemas.
"""

CONTROL_SCHEMAS = [
    {
        "name": "respond",
        "_category": "control",
        "description": "Send a message to the user. Use this to explain reasoning, report progress, ask questions, or reply to conversational messages.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The message to send to the user"}
            },
            "required": ["message"]
        }
    },
    {
        "name": "finish",
        "_category": "control",
        "description": "Complete the current task. Call this when all requested work is finished.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Brief summary of what was accomplished"}
            },
            "required": []
        }
    },
]
