# Lightweight Observable CLI — 表现层设计

> AI4SE Coding Agent Harness · 用户端表现层
> 日期：2026-07-22
> 基于：方案 A（轻量交互式）+ 方案 B 的可视化子集

---

## 1. 设计目标

表现层的核心价值不是"终端 UI 有多漂亮"，而是：

1. **可观察性** — 让评分者看到 Agent Loop 真正在运行，每个状态转移可见
2. **可调试性** — 支持 `--verbose` 模式，暴露完整上下文、LLM 响应、工具结果
3. **Demo 展示效果** — 状态机、Guardrail、Feedback Loop 等机制一目了然

---

## 2. 架构

```
cli/                    ← 新增表现层
├── __init__.py
├── main.py             ← CLI 入口（argparse）
├── session.py          ← SessionManager：交互循环、会话管理
├── renderer.py         ← Renderer 抽象 + TerminalRenderer 实现
└── commands.py         ← 交互命令（/status, /memory, /reset, /verbose）

observability/          ← 新增可观测性层
├── __init__.py
├── tracer.py           ← EventBus + TraceWriter
└── events.py           ← 事件类型定义

core/                   ← 内核层不变
├── state_machine.py
├── agent_state.py
└── ...
```

核心原则：

```
SessionManager
    │
    ├── Renderer        ← 输出渲染（可切换 human/simple/json 实现）
    ├── Tracer          ← 事件记录（JSON trace）
    │
    ▼
HarnessStateMachine     ← 内核层，不知道表现层存在
```

---

## 3. Renderer 抽象

StateMachine 不直接 `print()`，通过 Renderer 回调输出。

```python
class Renderer(ABC):
    def on_state_change(self, old_state: str, new_state: str, iteration: int, **context) -> None: ...
    def on_llm_call(self, model: str, messages: list[dict], response: str) -> None: ...
    def on_action(self, action: Action, guardrail_result: GuardrailResult | None) -> None: ...
    def on_tool_exec(self, tool: str, result: ToolResult) -> None: ...
    def on_feedback(self, feedback: str, plan: CorrectionPlan | None) -> None: ...
    def on_stop(self, reason: StopReason, iteration: int) -> None: ...
```

### TerminalRenderer（默认实现）

状态语义化：

```
══════════════════════ Iteration 1/12 ══════════════════════

[CONTEXT_ORG]
   loaded project rules
   retrieved 3 memories

[LLM_CALL]
   model: deepseek-v4-flash
   tokens: 1240

[ACTION_PARSE]
   action: shell("pytest")

[GUARDRAIL]
   CommandPolicy → ALLOW

[TOOL_EXEC]
   shell: pytest

[FEEDBACK]
   tests: 12 passed

══════════════════════ STOP: success ══════════════════════
```

### JsonRenderer（用于 trace 记录）

```json
{"event": "state_change", "iteration": 1, "from": "IDLE", "to": "CONTEXT_ORG", "timestamp": "..."}
```

---

## 4. SessionManager

```python
class SessionManager:
    def __init__(self, renderer: Renderer, tracer: Tracer):
        ...

    def start(self):
        """加载配置，创建会话，显示欢迎信息"""
        pass

    def submit(self, task: str) -> dict:
        """单次任务：构建 harness → 运行 → 返回结果"""
        pass

    def interactive(self):
        """交互式会话循环"""
        pass

    def exit(self):
        """保存摘要，写入 trace"""
        pass
```

### 交互命令

| 命令 | 用途 |
|------|------|
| `/status` | 查看当前状态、迭代次数 |
| `/memory` | 查看记忆内容 |
| `/reset` | 清空当前会话 |
| `/verbose` | 切换详细模式 |
| `exit` / `Ctrl+C` | 退出 |

---

## 5. 显示模式

### 普通模式（默认）

```
ai4se-agent
```

只显示状态转移和关键结果，适合日常使用。

### Debug 模式

```
ai4se-agent --verbose
```

额外显示：

- 完整 system prompt
- 用户输入
- LLM 原始响应
- 工具输出全文
- ActionParser 解析结果

### Trace 模式

```
ai4se-agent --trace
```

所有事件写入 `sessions/session_<timestamp>.json`，可用于回放和调试。

---

## 6. EventBus 与 Tracer

```python
@dataclass
class Event:
    type: Literal["STATE_CHANGED", "LLM_CALLED", "ACTION_PARSED",
                   "GUARDRAIL_CHECKED", "TOOL_EXECUTED", "FEEDBACK_RECEIVED"]
    iteration: int
    data: dict
    timestamp: str


class Tracer:
    def record(self, event: Event) -> None: ...
    def save(self, path: str) -> None: ...
    def replay(self, path: str) -> list[Event]: ...
```

Tracer 与 Renderer 是并列订阅者，StateMachine 通过同一个回调同时通知两者。

---

## 7. 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 输出颜色 | `colorama` | 轻量（~50KB），跨平台，`pip install colorama` |
| 输入循环 | `input()` + `sys.stdin` | 零依赖，交互命令用前缀 `/` 区分 |
| 事件序列化 | `json` 标准库 | 零依赖，trace 文件可读 |
| 终端宽度 | `shutil.get_terminal_size()` | 标准库，分隔线自适应 |

不引入 `rich`、`prompt_toolkit` 等重量级依赖。

---

## 8. 与现有代码的集成方式

### StateMachine 修改

```python
class HarnessStateMachine:
    def __init__(self, ..., renderer: Renderer | None = None, tracer: Tracer | None = None):
        self._renderer = renderer or NullRenderer()
        self._tracer = tracer or NullTracer()
```

关键回调点：

| 位置 | 回调 |
|------|------|
| `_on_context_org` 开始 | `renderer.on_state_change("CONTEXT_ORG")` |
| `_on_llm_call` 前后 | `renderer.on_llm_call(...)` |
| `_on_action_parse` 解析后 | `renderer.on_action(...)` |
| `_on_guardrail` 检查后 | `renderer.on_action(action, guardrail_result)` |
| `_on_tool_exec` 执行后 | `renderer.on_tool_exec(...)` |
| `_on_feedback` 收到后 | `renderer.on_feedback(...)` |
| `stop` 触发 | `renderer.on_stop(...)` |

### CLI 入口

```python
# cli/main.py
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("task", nargs="*")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()

    renderer = TerminalRenderer(verbose=args.verbose)
    tracer = Tracer() if args.trace else NullTracer()
    session = SessionManager(renderer=renderer, tracer=tracer)

    if args.task:
        session.submit(" ".join(args.task))
    else:
        session.interactive()
```

---

## 9. 文件变更清单

| 操作 | 文件 |
|------|------|
| 新建 | `src/ai4se_agent/cli/__init__.py` |
| 新建 | `src/ai4se_agent/cli/main.py` |
| 新建 | `src/ai4se_agent/cli/session.py` |
| 新建 | `src/ai4se_agent/cli/renderer.py` |
| 新建 | `src/ai4se_agent/cli/commands.py` |
| 新建 | `src/ai4se_agent/observability/__init__.py` |
| 新建 | `src/ai4se_agent/observability/tracer.py` |
| 新建 | `src/ai4se_agent/observability/events.py` |
| 修改 | `src/ai4se_agent/core/state_machine.py` — 添加 Renderer/Tracer 回调 |
| 删除 | `src/ai4se_agent/cli.py` — 迁移到 cli/main.py |
| 修改 | `pyproject.toml` — 入口点 `ai4se_agent.cli:main` → `ai4se_agent.cli.main:main` |

---

## 10. 验收标准

1. `ai4se-agent` 进入交互模式，显示欢迎信息和状态指示
2. `ai4se-agent "task"` 单次模式正常执行，状态转移可见
3. `--verbose` 模式显示完整 LLM 请求/响应
4. `--trace` 模式生成 JSON trace 文件
5. 交互命令 `/status`、`/memory`、`/reset`、`/verbose` 可用
6. Renderer 可替换为 NullRenderer 不影响测试
7. 现有 53 个测试全部通过