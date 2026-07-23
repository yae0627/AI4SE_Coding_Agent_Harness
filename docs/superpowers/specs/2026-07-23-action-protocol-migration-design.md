# Action Protocol Migration — 设计规约

> 日期：2026-07-23
> 属于 AI4SE Coding Agent Harness 项目。A 阶段改造，聚焦 Action Protocol 升级。

## 一、问题陈述

### 1.1 当前问题

当前 Action Protocol 存在以下缺陷：

- **文本格式脆弱**：`action: write_file key=value` 格式依赖 regex 解析，`\n`/`\"` 转义容易出错，空格分隔导致多词参数（如 shell 命令）需要特殊处理
- **`[DONE]` 是哨兵不是 action**：在 `_on_action_parse` 中用字符串包含检测，不走 validate/guardrail 流程，与系统架构不一致
- **工具描述写死**：`prompt.py` 中硬编码 5 个工具的文本描述，新增工具需同步修改
- **ActionValidator 硬编码**：`REQUIRED_PARAMS` 字典与工具实现分离，容易不一致

### 1.2 目标

1. JSON 格式的 Action 协议，解决转义和解析问题
2. `finish` 作为一等 action，经过完整的 validate → guardrail 流程
3. 每个 Tool 自描述 schema，驱动 prompt 生成和验证
4. 向后兼容：保留旧 parser 作为过渡

## 二、设计

### 2.1 Tool Schema

每个 Tool 通过 `schema` property 暴露其接口描述，格式遵循 OpenAI function calling 的 `parameters` 风格：

```python
class Tool(ABC):
    name: str

    @property
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": "Description of what this tool does",
            "parameters": {
                "type": "object",
                "properties": {
                    "param_name": {
                        "type": "string",
                        "description": "What this param does"
                    },
                    ...
                },
                "required": ["param1", "param2"]
            }
        }
```

`ToolRegistry.list_schemas()` 返回所有注册工具的 schema 列表。

### 2.2 JSON Action 格式

LLM 响应格式从文本改为 JSON：

```json
{"action": "write_file", "parameters": {"path": "main.cpp", "content": "#include <iostream>\nint main() {}\n"}}
{"action": "shell", "parameters": {"command": "g++ -o main main.cpp"}}
{"action": "finish", "parameters": {"summary": "Task completed"}}
```

### 2.3 ParseResult

Parser 返回结构化结果而非 `None`：

```python
@dataclass
class ParseResult:
    success: bool
    action: Action | None = None
    error: str | None = None
```

### 2.4 ActionParser 双策略

```python
class ActionParser:
    def __init__(self, fallback: bool = True):
        self._legacy = LegacyActionParser()

    def parse(self, text: str) -> ParseResult:
        # 1. 尝试 JSON 解析（含文本包裹提取）
        result = self._try_json(text)
        if result.success:
            return result
        # 2. 回退到旧 regex 解析
        if self._fallback:
            action = self._legacy.parse(text)
            if action:
                return ParseResult(success=True, action=action)
        return result
```

JSON 提取策略：
- 检测 ` ```json ... ``` ` 或 ` ``` ... ``` ` 代码块
- 否则找第一个 `{` 到最后一个 `}`
- `json.loads()` 解析

### 2.5 ActionValidator schema 驱动

```python
class ActionValidator:
    def __init__(self, schemas: list[dict]):
        self._schemas = {s["name"]: s for s in schemas}

    def validate(self, action: Action) -> list[str]:
        # 1. 检查 action name 是否合法
        # 2. 检查 required 参数是否存在
        # 3. 类型检查（string 类型参数必须是 str）
```

`finish` 注册为合法 action，其 schema 定义：
```python
{
    "name": "finish",
    "description": "Signal task completion",
    "parameters": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Summary of what was done"}
        },
        "required": []
    }
}
```

### 2.6 状态机变更

`_on_action_parse` 中移除 `[DONE]` 检测，改为：

```python
if action.name == "finish":
    self.stop_reason = StopReason.SUCCESS
    self.stop()
    return
```

`finish` 不经过 GuardrailEngine（直接 ALLOW），其余 action 走完整流程。

### 2.7 `Action.params` → `Action.parameters`

所有工具内部和调用方统一使用 `parameters` 字段名。

## 三、数据模型变更

```python
# types.py 新增
@dataclass
class ParseResult:
    success: bool
    action: Optional[Action] = None
    error: Optional[str] = None

# Action 字段改名
@dataclass
class Action:
    name: str
    parameters: dict  # 原 params
```

## 四、影响文件清单

| 文件 | 变更类型 |
|------|----------|
| `src/ai4se_agent/types.py` | 新增 `ParseResult`；`Action.params` → `parameters` |
| `src/ai4se_agent/tools/base.py` | 新增 `schema` property |
| `src/ai4se_agent/tools/read_file.py` | 实现 `schema` |
| `src/ai4se_agent/tools/write_file.py` | 实现 `schema` |
| `src/ai4se_agent/tools/edit_file.py` | 实现 `schema` |
| `src/ai4se_agent/tools/shell.py` | 实现 `schema` |
| `src/ai4se_agent/tools/run_test.py` | 实现 `schema` |
| `src/ai4se_agent/tools/registry.py` | 新增 `list_schemas()` |
| `src/ai4se_agent/core/action.py` | 重写 `ActionParser`(JSON+fallback) + `ActionValidator`(schema 驱动) |
| `src/ai4se_agent/context/prompt.py` | 从 schema 动态生成，JSON 示例 |
| `src/ai4se_agent/context/builder.py` | 接收 `ToolRegistry` 而非 `list[Tool]` |
| `src/ai4se_agent/core/state_machine.py` | `[DONE]` → `finish` action；`params` → `parameters` |
| `src/ai4se_agent/cli/session.py` | 构造 `ActionValidator` 时传入 schemas |
| `src/ai4se_agent/core/state_machine.py` | 构造 `ActionValidator` 时传入 schemas |
| `tests/core/test_action.py` | 更新为 JSON 测试用例 |
| `tests/core/test_state_machine.py` | mock 响应改为 JSON 格式 |
| `tests/tools/*.py` | 新增 schema 测试 |

## 五、验证标准

1. 所有已有 69 个测试保持绿色（含旧 parser 过渡期内）
2. 新增测试覆盖：
   - JSON 解析（含 markdown 代码块包裹）
   - `finish` action 正常触发 STOP
   - `ParseResult` 成功/失败路径
   - schema 类型检查（类型不匹配时返回错误）
   - 旧文本格式通过 fallback 仍能解析
3. 真实 LLM 端到端：写 C++ 文件 → 编译 → 运行能走通

## 六、未决问题

1. `Action.parameters` 改名后，所有工具内部的 `params["key"]` 是否一次性替换？—— 是，全部替换
2. 旧 parser 过渡期保留多久？—— 至少保留到 B 阶段完成
3. Guardrail 中对 `Action.params` 的引用如何处理？—— 一并改为 `parameters`，参数本身内容不变