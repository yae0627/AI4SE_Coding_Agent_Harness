# src/ai4se_agent/core/action.py
import json
import re
from ai4se_agent.types import Action, ParseResult


class LegacyActionParser:
    """Fallback parser for legacy text format: action: name key=value"""

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


class ActionParser:
    def __init__(self, fallback: bool = True):
        self._fallback = fallback
        self._legacy = LegacyActionParser()

    def _repair_escapes(self, text: str) -> str | None:
        """Fix invalid JSON escape sequences introduced by OS-specific syntax.

        Example: ``C:\\Users\\test`` contains ``\\U`` which is not a valid JSON
        escape.  Valid escapes are ``\" \\ \\/ \\b \\f \\n \\r \\t \\uXXXX``.
        Any backslash followed by a character outside this set is treated as
        a literal backslash by doubling it (``\\`` → ``\\\\``).

        Uses a proper state machine: tracks *in_string* (inside a JSON string
        value) and detects backslash + invalid-escape pairs, doubling the
        backslash so json.loads sees a literal ``\\``.
        """
        _VALID = frozenset('"\\/bfnrtu')
        result: list[str] = []
        i = 0
        in_string = False
        fixed = False

        while i < len(text):
            ch = text[i]

            if ch == '"':
                in_string = not in_string
                result.append(ch)
                i += 1
                continue

            if ch == '\\' and in_string and i + 1 < len(text):
                nxt = text[i + 1]
                if nxt not in _VALID:
                    result.append('\\\\')
                    fixed = True
                    i += 1
                    continue
                # valid escape — pass through unchanged
                result.append(ch)
                result.append(nxt)
                i += 2
                continue

            result.append(ch)
            i += 1

        return ''.join(result) if fixed else None

    def _repair_json(self, text: str) -> str | None:
        """Fix unescaped double quotes inside JSON string values.

        LLMs frequently forget to escape ``"`` inside generated code/content strings.
        This walks the JSON text tracking string boundaries and escapes any ``"``
        that appears inside a string value where the next non-whitespace character
        is not a JSON structural character (``,``, ``}``, ``]``, ``:``).
        """
        result: list[str] = []
        i = 0
        in_string = False
        escape_next = False
        fixed = False

        while i < len(text):
            ch = text[i]

            if escape_next:
                result.append(ch)
                escape_next = False
                i += 1
                continue

            if ch == '\\' and in_string:
                result.append(ch)
                escape_next = True
                i += 1
                continue

            if ch == '"':
                if not in_string:
                    result.append(ch)
                    in_string = True
                else:
                    rest = text[i + 1:]
                    j = 0
                    while j < len(rest) and rest[j] in ' \t\n\r':
                        j += 1
                    if j < len(rest) and rest[j] in ',}]:':
                        result.append(ch)
                        in_string = False
                    else:
                        result.append('\\"')
                        fixed = True
                i += 1
                continue

            result.append(ch)
            i += 1

        if in_string:
            result.append('"')

        return ''.join(result) if fixed else None

    def _try_json(self, text: str) -> ParseResult:
        text = text.strip()
        code_block = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if code_block:
            text = code_block.group(1).strip()
        brace_start = text.find('{')
        brace_end = text.rfind('}')
        if brace_start == -1 or brace_end == -1 or brace_end <= brace_start:
            return ParseResult(success=False, error="No JSON object found")
        text = text[brace_start:brace_end + 1]

        try:
            obj = json.loads(text)
        except json.JSONDecodeError as e:
            # Layer 4a: repair invalid escape sequences (e.g. Windows paths)
            repaired = self._repair_escapes(text)
            if repaired:
                try:
                    obj = json.loads(repaired)
                except json.JSONDecodeError:
                    repaired = None  # fall through to _repair_json

            # Layer 4b: repair unescaped quotes inside strings
            if repaired is None:
                repaired = self._repair_json(text)

            if repaired:
                try:
                    obj = json.loads(repaired)
                except json.JSONDecodeError as e2:
                    return ParseResult(success=False, error=f"Invalid JSON: {e2}")
            else:
                return ParseResult(success=False, error=f"Invalid JSON: {e}")

        # Extract optional message
        message = obj.get("message")

        # Extract optional action
        action = None
        if "action" in obj:
            action_obj = obj["action"]
            if isinstance(action_obj, str):
                # Old format: {"action": "tool_name", "parameters": {...}}
                action = Action(
                    name=action_obj,
                    parameters=obj.get("parameters", {})
                )
            elif isinstance(action_obj, dict):
                # New format: {"action": {"name": "tool_name", "parameters": {...}}}
                action = Action(
                    name=action_obj["name"],
                    parameters=action_obj.get("parameters", {})
                )

        if message is None and action is None:
            return ParseResult(success=False, error="Response must have 'message' and/or 'action' field")

        return ParseResult(success=True, action=action, message=message)

    def parse(self, text: str) -> ParseResult:
        result = self._try_json(text)
        if result.success:
            return result
        if self._fallback:
            action = self._legacy.parse(text)
            if action:
                return ParseResult(success=True, action=action)
        return result


class ActionValidator:
    def __init__(self, schemas: list[dict] | None = None):
        if schemas is None:
            # Backward-compatible hardcoded defaults
            schemas = [
                {
                    "name": "read_file",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"]
                    }
                },
                {
                    "name": "write_file",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                        "required": ["path", "content"]
                    }
                },
                {
                    "name": "edit_file",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}},
                        "required": ["path", "old_string", "new_string"]
                    }
                },
                {
                    "name": "shell",
                    "parameters": {
                        "type": "object",
                        "properties": {"command": {"type": "string"}, "timeout": {"type": "integer"}},
                        "required": ["command"]
                    }
                },
                {
                    "name": "run_test",
                    "parameters": {
                        "type": "object",
                        "properties": {"test_path": {"type": "string"}, "args": {"type": "string"}},
                        "required": []
                    }
                },
            ]
        self._schemas = {s["name"]: s for s in schemas}

    def validate(self, action: Action) -> list[str]:
        errors = []
        schema = self._schemas.get(action.name)
        if not schema:
            errors.append(f"Unknown action: {action.name}")
            return errors
        required = schema["parameters"].get("required", [])
        for param in required:
            if param not in action.parameters:
                errors.append(f"Missing required parameter: {param}")
        for key, value in action.parameters.items():
            prop = schema["parameters"]["properties"].get(key)
            if prop and prop.get("type") == "string" and not isinstance(value, str):
                errors.append(f"Parameter '{key}' should be string, got {type(value).__name__}")
        return errors
