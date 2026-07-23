# src/ai4se_agent/core/action.py
import re
from ai4se_agent.types import Action


class ActionParser:
    def parse(self, text: str) -> Action | None:
        match = re.match(r'action:\s*(\w+)(.*)', text.strip())
        if not match:
            return None
        name = match.group(1)
        rest = match.group(2).strip()

        params = {}
        pos = 0
        while pos < len(rest):
            while pos < len(rest) and rest[pos] in ' \t':
                pos += 1
            key_match = re.match(r'(\w+)=', rest[pos:])
            if not key_match:
                break
            key = key_match.group(1)
            pos += key_match.end()
            if pos < len(rest) and rest[pos] == '"':
                pos += 1
                value = []
                while pos < len(rest):
                    if rest[pos] == '\\' and pos + 1 < len(rest) and rest[pos + 1] == '"':
                        value.append('"')
                        pos += 2
                    elif rest[pos] == '\\' and pos + 1 < len(rest) and rest[pos + 1] == 'n':
                        value.append('\n')
                        pos += 2
                    elif rest[pos] == '\\' and pos + 1 < len(rest) and rest[pos + 1] == 't':
                        value.append('\t')
                        pos += 2
                    elif rest[pos] == '\\' and pos + 1 < len(rest) and rest[pos + 1] == 'r':
                        value.append('\r')
                        pos += 2
                    elif rest[pos] == '"':
                        pos += 1
                        break
                    else:
                        value.append(rest[pos])
                        pos += 1
                params[key] = ''.join(value)
            elif pos < len(rest) and rest[pos] == "'":
                pos += 1
                value = []
                while pos < len(rest):
                    if rest[pos] == '\\' and pos + 1 < len(rest) and rest[pos + 1] == "'":
                        value.append("'")
                        pos += 2
                    elif rest[pos] == "'":
                        pos += 1
                        break
                    else:
                        value.append(rest[pos])
                        pos += 1
                params[key] = ''.join(value)
            else:
                next_key = re.search(r'\s+\w+=', rest[pos:])
                if next_key:
                    end = pos + next_key.start()
                    value = rest[pos:end].strip()
                    pos = end
                else:
                    value = rest[pos:].strip()
                    pos = len(rest)
                value = value.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
                params[key] = value

        return Action(name=name, parameters=params)


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
            if param not in action.parameters:
                errors.append(f"Missing required param: {param}")
        return errors
