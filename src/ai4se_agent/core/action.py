# src/ai4se_agent/core/action.py
import re
from ai4se_agent.types import Action


class ActionParser:
    def parse(self, text: str) -> Action | None:
        match = re.match(r'action:\s*(\w+)(.*)', text.strip())
        if not match:
            return None
        name = match.group(1)
        params_str = match.group(2).strip()
        params = {}
        for pair in re.findall(r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|(.+?)(?=\s+\w+=|$))', params_str):
            value = (pair[1] or pair[2] or pair[3]).strip()
            if value:
                params[pair[0]] = value
        return Action(name=name, params=params)


class ActionValidator:
    REQUIRED_PARAMS = {
        "read_file": ["path"],
        "write_file": ["path", "content"],
        "edit_file": ["path", "old_string", "new_string"],
        "shell": ["command"],
        "run_test": [],
    }

    def validate(self, action: Action) -> list[str]:
        errors = []
        required = self.REQUIRED_PARAMS.get(action.name, [])
        for param in required:
            if param not in action.params:
                errors.append(f"Missing required param: {param}")
        return errors
