# Task 4: Action Parsing and Validation

**Files:**
- Create: `src/ai4se_agent/core/action.py`
- Create: `tests/core/test_action.py`

**Interfaces:**
- Consumes: `Action` from Task 1
- Produces: `ActionParser.parse(text) -> Action`, `ActionValidator.validate(action) -> list[str]` consumed by state machine

## Step 1: Write the failing test

```python
# tests/core/test_action.py
from ai4se_agent.core.action import ActionParser, ActionValidator
from ai4se_agent.types import Action

def test_parse_valid_action():
    parser = ActionParser()
    action = parser.parse('action: write_file path=test.txt content=hello')
    assert action.name == "write_file"
    assert action.params["path"] == "test.txt"

def test_parse_missing_action():
    parser = ActionParser()
    result = parser.parse("some random text")
    assert result is None

def test_validate_missing_param():
    validator = ActionValidator()
    action = Action(name="write_file", params={})
    errors = validator.validate(action)
    assert "path" in errors[0] or "content" in errors[0]
```

## Step 2: Run test to verify it fails

Run: `pytest tests/core/test_action.py -v`
Expected: FAIL

## Step 3: Write minimal implementation

```python
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
        for pair in re.findall(r'(\w+)=(\S+)', params_str):
            params[pair[0]] = pair[1]
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
```

## Step 4: Run tests

Run: `pytest tests/core/test_action.py -v`
Expected: PASS

## Step 5: Commit

```bash
git add src/ai4se_agent/core/action.py tests/core/test_action.py
git commit -m "feat: add ActionParser and ActionValidator"
```

## Global Constraints

- Python >=3.10
- All core mechanisms must be testable with mock LLM (no network, no real LLM)
- No use of agent orchestration frameworks
- Tests in `tests/` mirroring `src/` structure
- No comments in code unless specified
