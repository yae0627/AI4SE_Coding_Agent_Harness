# AI4SE_Coding_Agent_Harness

A **Coding Agent Harness** — an engineering system that wraps an LLM into a reliable, feedback-driven coding agent. Built with Python.

**核心等式：Agent = LLM + Harness。** LLM 负责"下一步做什么"的决策，Harness 提供治理、反馈、工具、记忆这层工程封装。

## 项目状态

✅ **Plan 工具完成** — 246 个测试通过。LLM 自主创建和更新计划（plan_create/plan_update），双层迭代计数器（全局40+单步12），/ 命令实时预览，跨平台路径处理。

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

### 安装

```bash
pip install ai4se-agent
```

或从源码安装：

```bash
git clone https://github.com/yae0627/AI4SE_Coding_Agent_Harness.git
cd AI4SE_Coding_Agent_Harness/projects
pip install -e ".[dev]"
```

### 配置 API Key

```bash
# 方式一：环境变量
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选
export OPENAI_MODEL="gpt-4o"

# 方式二：首次运行向导
ai4se-agent --setup

# 方式三：项目 .env 文件
echo "OPENAI_API_KEY=sk-..." > .env
```

### 运行

```bash
ai4se-agent                          # 交互模式
ai4se-agent "your task description"  # 单次任务
ai4se-agent --verbose "task"         # 详细输出
ai4se-agent --trace "task"           # 保存 JSON trace
```

### 运行测试

```bash
pytest tests/ -v     # 246 个测试
```

### 机制演示

```bash
python demo/mechanism_demo.py
```

演示 5 个核心机制：护栏拦截危险命令、反馈闭环检测失败、增量修正策略、FailureDB 持久化、WorkspacePolicy 路径拦截。

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

- **API Key**：通过 `.env` 或系统环境变量加载，`.env` 在 `.gitignore` 中，永不提交 Git
- **危险命令拦截**：代码级策略（CommandPolicy），非 Prompt 约束。`rm -rf /`、`dd`、`mkfs` 等危险命令在工具层被拦截
- **路径沙箱**：PathNormalizer 在运行时校验路径不逃逸工作区
- **Git 操作审批**：`git push`、`git reset --hard` 等高风险操作自动进入 HITL 审批状态
- **首次运行**：检测无配置时自动进入 setup wizard，隐藏输入 API Key

## 已知限制

- **平台**：主要在 Windows 上开发和测试。Linux/macOS 兼容但未经充分测试
- **Shell 命令**：交互模式下使用 cmd.exe（Windows）。Linux/macOS 需调整 SHELL 环境
- **LLM 模型**：deepseek-v4-flash 在复杂多步任务上表现不稳定，建议使用 glm-5.2 或 deepseek-v4-pro
- **终端**：/ 命令预览使用 ANSI 转义序列，需 Windows Terminal 或支持 VT100 的终端
- **Python**：需要 Python 3.10+

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
