# AI4SE_Coding_Agent_Harness

A **Coding Agent Harness** — an engineering system that wraps an LLM into a reliable, feedback-driven coding agent. Built with Python.

**核心等式：Agent = LLM + Harness。** LLM 负责"下一步做什么"的决策，Harness 提供治理、反馈、工具、记忆这层工程封装。

## 项目状态

✅ **Phase 3 完成** — 182 个测试通过。Claude Code 风格终端 UI：彩色紧凑工具行、HITL 面板、蓝色分隔线。

## 架构

```
src/ai4se_agent/
├── types.py              # 共享类型（Action, ToolResult, Feedback, GuardrailResult 等）
├── cli/
│   ├── main.py           # CLI 入口（argparse, --verbose, --trace, --setup）
│   ├── session.py        # SessionManager：交互循环、会话管理
│   ├── renderer.py       # Renderer ABC + TerminalRenderer + NullRenderer（事件驱动）
│   └── commands.py       # 交互命令（/status, /reset, /verbose, /config, /models）
├── config/
│   ├── schema.py         # AppConfig dataclass（provider/model/agent 三级配置）
│   ├── loader.py         # 三级加载（env vars → ./ai4se.toml → ~/.config/ai4se/ → defaults）
│   └── wizard.py         # 首次部署交互式引导 + /v1/models 发现
├── context/
│   ├── prompt_context.py # PromptContext 数据载体
│   ├── prompt_section.py # PromptSection ABC
│   ├── prompt_composer.py# PromptComposer 编排器
│   ├── sections/         # 6 个 Section 组件（SystemRole/Tool/Format/Example/Workspace/Rules）
│   ├── workspace.py      # WorkspaceCollector + WorkspaceSnapshot（TTL 缓存）
│   ├── builder.py        # ContextBuilder：动态组装 LLM 输入
│   └── prompt.py         # build_tool_descriptions() 工具函数
├── core/
│   ├── agent_state.py    # AgentState 数据模型
│   ├── action.py         # ActionParser（JSON + legacy）+ ActionValidator（schema 驱动）
│   ├── events.py         # AgentEvent dataclass（14 事件类型）
│   ├── event_bus.py      # EventBus（subscribe/publish）
│   └── state_machine.py  # 11 状态 FSM 主循环（含 EventBus emit）
├── session/
│   ├── history.py        # ConversationMemory（统一跨轮次对话记忆）
│   └── session.py        # Session + AgentRuntime（Session 持有 ConversationMemory）
├── llm/
│   ├── base.py           # LLMAdapter ABC
│   ├── openai_adapter.py # OpenAI 适配器
│   ├── manager.py        # LLMManager（adapter 工厂 + runtime reload）
│   └── mock_adapter.py   # Mock 适配器（测试用）
├── tools/
│   ├── base.py           # Tool ABC + schema 属性
│   ├── registry.py       # 工具注册表 + list_schemas()
│   ├── read_file.py      # 读文件
│   ├── write_file.py     # 写文件
│   ├── edit_file.py      # 局部编辑
│   ├── shell.py          # Shell 执行
│   └── run_test.py       # 测试运行
├── guardrails/
│   ├── base.py           # Policy ABC
│   ├── engine.py         # 护栏引擎
│   ├── command_policy.py # 危险命令拦截
│   ├── file_policy.py    # 保护路径拦截
│   ├── workspace_policy.py # 路径逃逸拦截
│   └── git_policy.py     # 高风险 git 操作拦截
├── feedback/
│   ├── sensor.py         # Sensor ABC + Test/Lint Sensor
│   ├── classifier.py     # FailureClassifier（规则驱动）
│   ├── planner.py        # CorrectionPlanner
│   ├── failure_db.py     # FailureDB (SQLite)
│   └── loop.py           # FeedbackLoop 编排器
├── memory/
│   ├── manager.py        # MemoryManager 聚合层（ConversationMemory + PersistentMemory + FailureLog）
│   └── persistent.py     # PersistentMemory（项目规则文件存储）
└── observability/
    ├── events.py          # 事件类型 + timestamp/elapsed_ms
    └── tracer.py          # Tracer：record_token, replay_filtered
```

## 状态机

12 状态 FSM（`transitions` 库），事件驱动输出（含 RESPOND 交互状态）：

```
                 IDLE
                   │
            CONTEXT_ORG
                   │
              LLM_CALL ──── LLM_START/END events
                   │
           ACTION_PARSE ──── ACTION_CREATED event
                   │
              GUARDRAIL ──── GUARDRAIL_PASS/DENY, APPROVAL_REQUIRED events
                   │
             TOOL_EXEC ──── TOOL_START/END events
                   │
              FEEDBACK ──── FEEDBACK_COMPLETED event
                   │
          MEMORY_UPDATE ──── MEMORY_WRITE event
                   │
                 STOP ──── AGENT_STOP event
```

## 快速开始

```bash
# 安装依赖
pip install -e ".[dev]"

# 首次运行 — 交互式配置引导
ai4se-agent --setup
# 或直接启动交互模式（自动检测无配置时进入引导）
ai4se-agent
```

### 配置管理

配置存储在 `~/.config/ai4se/config.toml`（Linux/macOS）或 `%APPDATA%/ai4se/config.toml`（Windows），从任意目录运行均可加载。

```toml
[provider]
name = "openai"
api_key = "sk-..."
base_url = "https://api.openai.com/v1"

[model]
active = "gpt-4o"

[agent]
max_iterations = 20
```

### 单次任务模式

```bash
ai4se-agent "你的任务描述"
ai4se-agent --verbose "你的任务描述"      # 详细输出
ai4se-agent --trace "你的任务描述"        # 保存 JSON trace
```

### 交互式会话模式

```bash
ai4se-agent    # 无参数启动交互模式
```

交互模式支持以下命令：

| 命令 | 用途 |
|------|------|
| `你的任务描述` | 提交任务给 agent（跨轮次保留对话历史） |
| `/config` | 查看当前配置 |
| `/config set model active <name>` | 切换模型（即时生效） |
| `/models` | 列出 API 可用模型 |
| `/status` | 查看当前状态和迭代次数 |
| `/verbose` | 切换详细输出模式 |
| `/reset` | 清空当前会话 |
| `exit` / `quit` | 退出交互模式 |

### 输出示例

```
Workspace: C:\Users\...\AI4SE\projects
Model: deepseek-v4-flash
Provider: openai

> write a Python script that prints Fibonacci(20)

[CONTEXT_ORG] Iteration 1
  action: write_file({'path': 'fibo.py', 'content': 'def fib(n):...'})
  guardrail: all -> ALLOW
  result: OK
  feedback: success
[CONTEXT_ORG] Iteration 2
  action: shell({'command': 'python fibo.py'})
  guardrail: all -> ALLOW
  result: OK
  feedback: success
STOP: success | 2 iters | 0 tokens | 0.0s
Result: success (success)
```

## 运行测试

```bash
pytest -v           # 162 个测试
ruff check src/     # Lint 检查
```

## 机制演示

```bash
python demo/mechanism_demo.py
```

演示 5 个核心机制：
1. 护栏拦截危险命令（`rm -rf /`）
2. 反馈闭环检测失败并生成修正计划
3. 增量修正策略（3 次失败后升级）
4. FailureDB 持久化失败模式
5. WorkspacePolicy 拦截路径逃逸

## 重点维度：反馈闭环

```
Sensor (TestSensor / LintSensor)
  → Feedback (success, category, message, source, severity)
  → FailureClassifier (规则驱动，非 LLM)
  → CorrectionPlanner (生成修正建议，不直接修代码)
  → FailureDB (SQLite 持久化失败模式)
```

## 工程亮点

| 维度 | 实现 |
|------|------|
| **Context Engineering** | PromptComposer + 6 Section 组件，WorkspaceContext 动态注入（OS/文件/git/时间） |
| **Action Protocol** | JSON-first 解析器 + legacy 回退 + JSON repair（修复 LLM 转义错误） |
| **Event Bus** | 14 事件类型，FSM → EventBus → Renderer 解耦，subscribe/publish 模式 |
| **Session Layer** | ConversationMemory 跨轮次持久，Session 持有唯一真实来源，AgentRuntime delta sync |
| **配置系统** | TOML 三级加载（env vars → 项目 → 用户 → 默认），setup wizard + /v1/models 发现 |
| **LLM Manager** | adapter 工厂 + runtime model switch，即时生效 |
| **可观测性** | Trace timestamp/elapsed_ms，replay_filtered 结构化回放 |

## 安全边界

- API Key 通过 `~/.config/ai4se/config.toml` 存储
- 危险命令拦截为代码机制（CommandPolicy），非 Prompt 约束
- 文件操作限制在 workspace 内（WorkspacePolicy）
- 路径逃逸检测（`../../` 写出 workspace 被拦截）

## 技术栈

| 维度 | 选择 |
|------|------|
| 语言 | Python 3.10+ |
| LLM 供应商 | OpenAI + 兼容格式（可切换） |
| 状态机 | `transitions` |
| 测试 | pytest |
| Lint | ruff |
| CLI | colorama |
| CI/CD | GitHub Actions + .gitlab-ci.yml |

## 设计文档

| 阶段 | Spec | Plan |
|------|------|------|
| 核心 Harness | [design](docs/superpowers/specs/2026-07-21-coding-agent-harness-design.md) | [plan](docs/superpowers/plans/2026-07-21-coding-agent-harness-plan.md) |
| CLI 表现层 | [design](docs/superpowers/specs/2026-07-22-observable-cli-design.md) | [plan](docs/superpowers/plans/2026-07-22-observable-cli-plan.md) |
| Action Protocol 迁移 | [design](docs/superpowers/specs/2026-07-23-action-protocol-migration-design.md) | [plan](docs/superpowers/plans/2026-07-23-action-protocol-migration-plan.md) |
| Context + Observability | [design](docs/superpowers/specs/2026-07-23-context-observability-design.md) | [plan](docs/superpowers/plans/2026-07-23-context-observability-plan.md) |
| Session + Event Bus | [design](docs/superpowers/specs/2026-07-23-session-event-bus-design.md) | [plan](docs/superpowers/plans/2026-07-23-session-event-bus-plan.md) |

## 项目课程

本项目使用 [Superpowers](https://github.com/obra/superpowers) 框架开发，遵循 `brainstorming → writing-plans → subagent-driven-development → test-driven-development → requesting-code-review → finishing-a-development-branch` 工作流。
