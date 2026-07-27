# AI4SE Coding Agent Harness — 综合规约

> AI4SE 期末项目 A · Coding Agent Harness
> 日期：2026-07-27
> 状态：Final
> 提交：246 tests, 121 commits

---

## 1. 问题陈述

### 1.1 要解决的问题

当前 LLM 在软件工程场景中面临的核心矛盾：**LLM 擅长"下一步做什么"的决策，但缺乏可靠的工程封装**。一个裸 LLM 在编码场景中会：

- 执行危险操作（`rm -rf /`、`git push --force`）而无拦截机制
- 无法感知自身行为的正确性 —— 写完代码后没有机制验证它是否通过测试
- 在长会话中上下文膨胀，丢失关键信息
- 跨会话"失忆"，每次重新学习项目约定和架构决策

**Coding Agent Harness** 解决的是：将 LLM 的决策能力封装进一个有状态、可治理、有反馈的系统，使其能稳定、可靠地完成编码任务。

### 1.2 目标用户

- **使用 AI 辅助编码的开发者**，需要一个可信任的本地编码助手，能自主完成读代码、改代码、测试、修正的闭环
- **需要在受控环境中运行编码 Agent 的团队**，要求沙箱化执行（文件路径限制、命令拦截）和 HITL 审批机制

### 1.3 核心等式

**Agent = LLM + Harness**。本项目不是"又一个 AI 编码助手"，而是对 Harness 层的工程实践 —— 当 LLM 能完成大部分"思考"时，工程师的价值落在治理（Guardrail）、反馈（Feedback）、上下文（Context）、记忆（Memory）、安全（Security）这层工程上。

---

## 2. 用户故事

遵循 INVEST 原则（Independent, Negotiable, Valuable, Estimable, Small, Testable）。

| # | 故事 | 角色 | 验收标准 |
|---|------|------|---------|
| 1 | 作为开发者，我向 Agent 提交一个编码任务，Agent 能自主完成读代码、修改、测试、修正的完整循环，不需要我每一步手动干预。 | 终端用户 | 一次 `ai4se-agent "task"` 调用走完 FSM 完整循环，最终 STOP |
| 2 | 作为开发者，当 Agent 要执行危险操作（如 `rm -rf`、`git push`）时，系统会拦截并要求我确认，避免意外破坏。 | 终端用户 | CommandPolicy 拦截 `rm -rf /` 返回 DENY；GitPolicy 拦截 `git push` 返回 REQUIRE_APPROVAL |
| 3 | 作为开发者，Agent 修改代码后会自动运行测试；如果测试失败，它会分析失败原因并尝试修正，而不是直接告诉我"我改完了"。 | 终端用户 | 注入测试失败后，FeedbackLoop 生成 CorrectionPlan，Agent 再次迭代修正直至通过或达到重试上限 |
| 4 | 作为开发者，我可以在配置文件中定义项目规则（如编程风格、测试要求），Agent 通过 RulesSection 自动遵守这些约定。 | 终端用户 | `ai4se.toml` 中的 rules 被注入到 System Prompt 的 RulesSection，Agent 按规则执行 |
| 5 | 作为开发者，我可以在跨会话的任务中看到 Agent 记住了之前项目的架构决策和失败模式，不需要每次都重新说明。 | 终端用户 | PersistentMemory 存储项目规则跨会话持久化；FailureDB 记录失败模式可查询 |
| 6 | 作为评分者，我可以在 CLI 输出中看到 FSM 每一步的状态转移，验证 Agent 的每个机制在正确运作。 | 评分者 | `--verbose` 输出每条 LLM 请求/响应；`--trace` 生成完整 JSON trace 可回放 |

---

## 3. 功能规约

### 3.1 Agent 主循环（12 状态 FSM）

**输入**：用户任务描述（文本）
**行为**：12 状态 FSM 驱动，事件通过 EventBus 广播给 Renderer 和 Tracer
**输出**：任务结果（success/failure + ExitReason + 产物）
**边界条件**：
- 全局最大迭代 40 轮，单步最大 12 轮
- 连续 3 次修正失败自动升级全量重规划
- LLM 调用连续失败 3 次停机
- tool 执行超时：shell 30s，test 120s，LLM 60s
**错误处理**：每状态有独立异常捕获，异常进入 TOOL_ERROR 或 STOP

#### 状态定义

| 状态 | 输入 | 行为 | 输出 | 后继 |
|------|------|------|------|------|
| **IDLE** | 用户任务 | 接收任务，初始化 AgentState | 任务上下文 | CONTEXT_ORG |
| **CONTEXT_ORG** | 任务 + 历史 + 记忆 + 反馈 | PromptComposer 组装 7 sections，检查 token 数，超限则摘要 | 完整 messages | LLM_CALL |
| **LLM_CALL** | messages | 调用 LLMAdapter.generate()，记录 token 用量 | LLM 回复文本 | ACTION_PARSE |
| **ACTION_PARSE** | LLM 回复 | JSON 解析 → schema 校验 → 参数校验；含 JSON repair 修复 LLM 转义错误 | ParseResult(Action) | GUARDRAIL / CONTEXT_ORG |
| **GUARDRAIL** | Action | 按 4 个 Policy 逐一检查，聚合结果 | GuardrailResult | TOOL_EXEC / WAIT_APPROVAL / CONTEXT_ORG |
| **WAIT_APPROVAL** | 待审批 Action | 打印详情，等待 y/n/超时 | 审批结果 | TOOL_EXEC / CONTEXT_ORG / STOP |
| **WAIT_INPUT** | 交互需求 | 等待用户补充输入 | 用户回复 | CONTEXT_ORG |
| **TOOL_EXEC** | Action | 从 ToolRegistry 查找工具，执行（含 PathNormalizer 路径标准化） | ToolResult | FEEDBACK / TOOL_ERROR |
| **TOOL_ERROR** | ToolResult | 区分 retryable/fatal；retryable 自动重试（最多 3 次） | 错误处理结果 | 重试 TOOL_EXEC / STOP |
| **FEEDBACK** | ToolResult | Sensor → Feedback → Classifier → Planner | CorrectionPlan | CONTEXT_ORG / MEMORY_UPDATE |
| **MEMORY_UPDATE** | 本轮关键信息 | 写入 session 记忆，条件写入 long-term | 更新状态 | CONTEXT_ORG / STOP |
| **STOP** | 终止原因 | 记录 ExitReason，输出最终结果 | 任务结果 | — |

### 3.2 工具系统

5 个核心工具，每个 Tool 通过 `schema` property 自描述接口，驱动 Prompt 生成和 ActionValidator 校验。

| 工具 | 参数 | 行为 | 输出 |
|------|------|------|------|
| `read_file` | path, start_line?, end_line? | 读取文件内容，支持行范围 | 文件内容文本 |
| `write_file` | path, content | 整文件写入（经过 FilePolicy 路径检查） | 写入结果 |
| `edit_file` | path, old_string, new_string | 精确字符串替换，支持增量修正 | 编辑结果 |
| `shell` | command, timeout?, workdir? | 执行 shell 命令（经过 CommandPolicy 检查） | stdout, stderr, exit_code |
| `run_test` | test_path?, args? | 调用 pytest，解析输出 | 测试结果 |

加分工具（Plan-as-tool 机制）：`plan_create`、`plan_update` —— LLM 自主创建和更新执行计划，配合 PlanSection 注入上下文。

### 3.3 护栏系统 (Guardrail)

**GuardrailEngine**：聚合多 Policy 检查结果

**4 个 Guardrail Policy**：

| Policy | 检查内容 | 拦截行为 |
|--------|---------|---------|
| **CommandPolicy** | 危险 shell 命令（`rm -rf /`、`dd`、`wget`、`curl` 等） | DENY |
| **FilePolicy** | 路径越界保护（`real_path.startswith(workspace)`），禁止写 `.git/`、`__pycache__` 等 | DENY |
| **WorkspacePolicy** | `../../` 路径逃逸检测 | DENY |
| **GitPolicy** | 高风险 git 操作（`git push`、`git reset --hard`、`git rebase`） | REQUIRE_APPROVAL |

**GuardrailResult** 三元裁定：`ALLOW` / `DENY` / `REQUIRE_APPROVAL`

### 3.4 Prompt 工程

7 个 Prompt Section，由 PromptComposer 编排组合：

| Section | 来源 | 内容 |
|---------|------|------|
| **SystemRoleSection** | 静态 | "You are a coding agent..." 角色定义 |
| **ToolSection** | ToolRegistry.list_schemas() 动态生成 | 工具描述（JSON 格式） |
| **FormatSection** | 静态 | JSON 响应格式 + 转义规则 |
| **ExampleSection** | 静态 | Few-shot 示例（write_file → shell → finish） |
| **WorkspaceSection** | WorkspaceCollector 动态采集 | OS 类型、工作目录、git 分支、文件摘要 |
| **RulesSection** | MemoryManager.get_rules() | 用户定义的项目规则（空则跳过） |
| **PlanSection** | PlanManager | 当前执行计划与进度 |

### 3.5 反馈闭环 (Feedback Loop)

```
FEEDBACK 状态
    │
    ├── Sensor 层
    │   ├── TestSensor  — 运行 pytest，解析输出
    │   └── LintSensor  — 运行 ruff，解析 lint 错误
    │
    ├── Feedback 对象
    │   success, category, message, details, severity, source
    │
    ├── FailureClassifier（规则驱动，非 LLM）
    │   "AssertionError" → logic_error
    │   "SyntaxError"    → syntax_error
    │   "ruff"           → style_error
    │
    ├── CorrectionPlanner
    │   生成 CorrectionPlan(scope, target_files, strategy, retry_count)
    │   不直接修代码，只给 LLM 提供修正建议
    │
    └── FailureDB（SQLite）
        记录失败模式，供后续查询和跨会话学习
```

**增量修正策略**：
- `retry_count < 3`：增量修正（只修改失败部分）
- `retry_count >= 3`：升级为全量重规划

### 3.6 EventBus

14 事件类型，实现 FSM → EventBus → Renderer/Tracer 解耦：

| 类别 | 事件 | 发射时机 |
|------|------|---------|
| Session | `SESSION_START`, `SESSION_END` | Session 生命周期 |
| Agent | `AGENT_START`, `AGENT_STOP` | AgentRuntime 执行边界 |
| LLM | `LLM_START`, `LLM_END` | LLM 调用前后 |
| Action | `ACTION_CREATED` | Action 解析成功 |
| Guardrail | `GUARDRAIL_PASS`, `GUARDRAIL_DENY`, `APPROVAL_REQUIRED` | 护栏检查结果 |
| Tool | `TOOL_START`, `TOOL_END` | 工具执行前后 |
| Feedback | `FEEDBACK_COMPLETED` | 反馈闭环完成 |
| Memory | `MEMORY_WRITE` | 记忆写入 |

### 3.7 记忆系统

| 层级 | 组件 | 存储 | 生命周期 |
|------|------|------|---------|
| 会话级 | ConversationMemory | 内存 | 一次交互会话 |
| 项目级 | PersistentMemory | `memory/project_rules/` 文件 | 跨会话持久 |
| 摘要级 | Session Summaries | `memory/session_summaries/` 文件 | 跨会话持久 |
| 失败模式 | FailureDB | SQLite (`memory/failure.db`) | 跨会话持久 |

### 3.8 配置与凭据管理

**三级配置加载**：环境变量 → `./ai4se.toml`（项目级） → `~/.config/ai4se/config.toml`（用户级） → 默认值

**凭据来源优先级**：
1. 环境变量（`OPENAI_API_KEY`）
2. 用户配置文件 `~/.config/ai4se/config.toml`
3. 首次运行引导（`ai4se-agent --setup` 交互式输入）

**LLMAdapter 切换机制**：
- `OpenAIAdapter`：标准 OpenAI 兼容 API
- `LocalAdapter`：本地模型端点
- `MockAdapter`：预设响应，用于确定性测试
- 运行时通过 `/config set model active <name>` 即时切换（LLMManager runtime reload）

---

## 4. 非功能性需求

### 4.1 性能

| 维度 | 指标 |
|------|------|
| LLM 调用超时 | 60s |
| Shell 工具超时 | 30s |
| 测试工具超时 | 120s |
| 状态转移延迟 | 无感知（纯内存操作） |
| 全局最大迭代 | 40 轮 |
| 单步最大迭代 | 12 轮 |

### 4.2 安全与凭据威胁模型

- API Key 绝不硬编码在源码中，绝不提交 Git，绝不写入日志
- 凭据存储于 `~/.config/ai4se/config.toml`（权限 600），非项目目录
- 所有文件操作限制在 workspace 内（FilePolicy + WorkspacePolicy 双重检查）
- 危险命令拦截为代码机制（CommandPolicy），非 Prompt 约束 —— Prompt 可被注入绕过，代码逻辑不可绕过
- `.gitignore` 中排除 `.env` 和凭据文件
- `ai4se-agent config status` 不显示 key 明文

### 4.3 可用性

- CLI 界面，Emit 事件驱动输出，状态转移可见
- HITL 时打印完整的危险动作详情（命令全文、影响路径等）
- STOP 时显示 ExitReason + 迭代次数 + token 用量 + 耗时
- 交互模式支持 `/status`、`/reset`、`/verbose`、`/config`、`/models` 等命令
- 单次模式 `ai4se-agent "task"` 与交互模式 `ai4se-agent` 双入口

### 4.4 可观测性

- 每轮迭代输出当前状态和关键信息（通过 TerminalRenderer）
- `--verbose` 模式暴露完整上下文、LLM 请求/响应、工具输出全文
- `--trace` 模式生成 JSON trace 文件（含 timestamp/elapsed_ms），支持 `replay_filtered` 结构化回放
- AgentState 可序列化，用于调试
- Tracer 记录 token 用量（prompt/completion）

---

## 5. 系统架构

### 5.1 组件图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              CLI 层                                       │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ main.py  │  │ session.py   │  │ renderer.py  │  │ commands.py      │ │
│  │(argparse)│  │(SessionMgr)  │  │(TerminalRdr) │  │(/status,/reset)  │ │
│  └──────────┘  └──────┬───────┘  └──────┬───────┘  └──────────────────┘ │
│                        │                │                                │
└────────────────────────┼────────────────┼────────────────────────────────┘
                         │                │  EventBus subscribe
                         ▼                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          Session 层                                      │
│  ┌────────────────────┐  ┌────────────────────┐                         │
│  │  Session           │  │  ConversationMemory │                         │
│  │  (跨轮次对话管理)    │  │  (消息历史)          │                         │
│  └────────┬───────────┘  └────────────────────┘                         │
│           │ 每次 send() 创建 AgentRuntime                                │
└───────────┼──────────────────────────────────────────────────────────────┘
            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       AgentRuntime (per-turn)                            │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │                    StateMachine (12 states)                     │     │
│  │  IDLE → CONTEXT_ORG → LLM_CALL → ACTION_PARSE → GUARDRAIL      │     │
│  │  → [WAIT_APPROVAL] → TOOL_EXEC → [TOOL_ERROR|FEEDBACK]         │     │
│  │  → MEMORY_UPDATE → [STOP|CONTEXT_ORG]                           │     │
│  │  emit(AgentEvent)  ────────► EventBus                           │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ Context  │ │Guardrail │ │   Tool   │ │  Memory  │ │FeedbackLoop  │  │
│  │ Builder  │ │ Engine   │ │ Registry │ │ Manager  │ │Sensor→Cls→Pl │  │
│  └────┬─────┘ └──────────┘ └────┬─────┘ └──────────┘ └──────────────┘  │
│       │                         │                                       │
│  ┌────▼─────┐          ┌───────▼────────┐                              │
│  │LLMAdapter│          │ read_file       │                              │
│  │(OpenAI/  │          │ write_file      │                              │
│  │ Local/   │          │ edit_file       │                              │
│  │ Mock)    │          │ shell           │                              │
│  └──────────┘          │ run_test        │                              │
│                        └────────────────┘                              │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.2 数据流

```
用户输入
    │
    ▼
Session.send(message)
    │
    ├── ConversationMemory.get_recent(20) → 历史上下文
    │
    ▼
AgentRuntime.run()
    │
    ├── ContextBuilder.build()
    │   ├── PromptComposer.compose(PromptContext)
    │   │   ├── SystemRoleSection (static)
    │   │   ├── ToolSection (ToolRegistry.list_schemas())
    │   │   ├── FormatSection (static)
    │   │   ├── ExampleSection (static)
    │   │   ├── WorkspaceSection (WorkspaceCollector.collect())
    │   │   ├── RulesSection (MemoryManager.get_rules())
    │   │   └── PlanSection (PlanManager)
    │   └── → messages 送入 LLM
    │
    ├── LLMAdapter.generate(messages) → response
    │
    ├── ActionParser.parse(response) → Action
    │   └── JSON 解析 → legacy fallback → JSON repair
    │
    ├── GuardrailEngine.check(action) → GuardrailResult
    │   ├── CommandPolicy
    │   ├── FilePolicy
    │   ├── WorkspacePolicy
    │   └── GitPolicy
    │
    ├── ToolRegistry.execute(action) → ToolResult
    │
    ├── FeedbackLoop.process(result) → CorrectionPlan
    │   └── Sensor → Feedback → FailureClassifier → CorrectionPlanner → FailureDB
    │
    └── MemoryManager.update(turn)
        ├── ConversationMemory (session)
        └── PersistentMemory (project rules, if applicable)
```

### 5.3 外部依赖

| 依赖 | 用途 | 版本 |
|------|------|------|
| `openai` | LLM 调用（OpenAI 兼容格式） | >=1.0.0 |
| `transitions` | 状态机引擎 | latest |
| `colorama` | CLI 跨平台颜色输出 | latest |
| `python-dotenv` | 环境变量加载 | latest |
| `pytest` | 测试框架（dev 依赖） | >=8.0 |
| `ruff` | Lint 检查（dev 依赖） | latest |

---

## 6. 数据模型

### AgentState

```python
@dataclass
class AgentState:
    current_state: str          # 当前 FSM 状态名
    goal: str                   # 本轮任务目标
    iteration: int              # 当前迭代轮次
    context: list[dict]         # messages 历史
    history: list[Turn]         # 完整轮次历史
    last_action: Action | None  # 上一步 Action
    last_observation: str | None
    error_count: int            # 连续错误计数
    retry_count: int            # 连续重试计数
    feedback: list[Feedback]    # 活跃反馈
```

### Action

```python
@dataclass
class Action:
    name: str                   # "read_file" | "write_file" | ... | "finish"
    parameters: dict            # {"path": "...", "content": "..."}
```

### ToolResult

```python
@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None
    metadata: dict              # duration, exit_code 等
```

### Feedback

```python
@dataclass
class Feedback:
    success: bool               # 是否成功
    category: str               # "logic_error" | "syntax_error" | "type_error" | "style_error"
    message: str                # 人类可读描述
    details: dict               # 结构化详情（行号、错误类型等）
    severity: int               # 严重级别 1-5
    source: str                 # "pytest" | "ruff" | "mypy"
```

### CorrectionPlan

```python
@dataclass
class CorrectionPlan:
    scope: str                  # 失败区域定位（如 "test_fibonacci"）
    target_files: list[str]     # 需要修改的文件列表
    strategy: str               # 修正建议描述（给 LLM 的提示）
    retry_count: int            # 当前重试次数
```

### GuardrailResult

```python
@dataclass
class GuardrailResult:
    verdict: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"]
    reason: str                 # 裁决原因
    policy: str                 # 触发的 Policy 名称
    severity: int               # 严重级别
    metadata: dict              # 额外信息（命令全文、目标路径等）
```

### AgentEvent（EventBus）

```python
@dataclass
class AgentEvent:
    type: str                   # EventType value
    iteration: int
    state: str                  # 当前 FSM 状态
    timestamp: str              # ISO 8601
    elapsed_ms: float           # 从 tracer start 开始的相对时间
    payload: dict               # 事件专有数据
```

### ParseResult

```python
@dataclass
class ParseResult:
    success: bool
    action: Action | None
    error: str | None
```

### 实体关系约束

```
Session 1──N ConversationMessage  (跨轮次)
AgentRuntime 1──1 AgentState      (每轮新创建)
StateMachine 1──N AgentEvent      (事件流)
ToolRegistry 1──N Tool            (注册模式)
GuardrailEngine 1──N Policy       (策略链)
FailureDB 1──N FailureRecord      (持久化失败模式)
```

---

## 7. 凭据与分发设计

### 7.1 凭据存储

- **存储位置**：`~/.config/ai4se/config.toml`（Linux/macOS）或 `%APPDATA%/ai4se/config.toml`（Windows）
- **入口**：环境变量 `OPENAI_API_KEY` → `ai4se.toml`（项目级） → `config.toml`（用户级，最高优先级）
- **首次配置**：`ai4se-agent --setup` 触发交互式引导，`getpass` 隐藏输入，自动调用 `/v1/models` 发现可用模型
- **查看状态**：`ai4se-agent config status` 显示已配置的 provider（不显示 key 明文）
- **更新**：`/config set provider api_key <key>` 或直接编辑 `config.toml`
- **清空**：手动删除 `config.toml` 中 `api_key` 字段

### 7.2 安全约束

- API Key 绝不硬编码在源码中
- 配置文件仅对当前用户可读（建议权限 600）
- 所有凭据路径均在 `.gitignore` 中
- 日志输出中屏蔽 key 信息

### 7.3 分发形态

- **PyPI 包**：`pip install ai4se-agent`
- **安装后命令**：`ai4se-agent run "<task>"` 或 `ai4se-agent` 交互模式
- **首次运行**：自动检测是否配置；未配置时进入引导
- **目标平台**：Windows / Linux / macOS（Python 3.10+）
- **分发方式**：`setuptools` + `pyproject.toml`

---

## 8. 技术选型与理由

| 维度 | 选择 | 理由 |
|------|------|------|
| **语言** | Python 3.10+ | 课程要求；生态成熟；`structural pattern matching`（3.10 新特性）可用于 Action 分发 |
| **LLM 供应商** | OpenAI + 兼容格式 | 灵活切换；MockAdapter 支持确定性测试 |
| **状态机** | `transitions` | 轻量（无外部依赖）、声明式 `from_to`、可测试，非 Agent 框架 |
| **CLI 输出** | `colorama` | 跨平台颜色输出，~50KB 极轻量 |
| **测试框架** | `pytest` | 标准选择，fixture/parametrize 覆盖 mock/stub 场景 |
| **Lint** | `ruff` | 极速（Rust 编写），替代 flake8/isort/black |
| **分发** | PyPI (`setuptools`) | 与 `pyproject.toml` 一致 |
| **配置格式** | TOML | Python 标准库 `tomllib`（3.11+），社区成熟 |
| **CI/CD** | GitHub Actions | 自动运行测试 + lint |
| **事件模型** | 标准库 `dataclass` + `callable` | 零依赖的发布/订阅，无需引入 eventlet/redis 等 |

**未选择的方案与理由**：

| 方案 | 未选择理由 |
|------|-----------|
| `langchain` / `crewAI` | 抽象层级过高，掩盖本项目"从零构建 Harness"的工程学习目标 |
| `rich` | 重量级依赖（~20MB），`colorama` 够用 |
| `FastAPI` Web 后端 | 项目范围限定 CLI，Web 界面为加分项非必须 |
| JavaScript / TypeScript | 课程指定 Python；LLM SDK 对 Python 生态最友好 |

---

## 9. 验收标准

| # | 标准 | 验证方式 | 关联模块 |
|---|------|---------|---------|
| 1 | **FSM 可运行**：给定一个任务，Agent 能完整走完 IDLE → ... → STOP 循环 | `pytest tests/core/test_state_machine.py` | StateMachine |
| 2 | **工具可执行**：5 个核心工具均能正常调用 | `pytest tests/tools/` | ToolRegistry |
| 3 | **护栏拦截**：`rm -rf /` 被 DENY；`../../etc/passwd` 写入被拦截 | `pytest tests/guardrails/` | GuardrailEngine |
| 4 | **HITL 可用**：危险 git 操作暂停等待用户输入，超时终止 | `pytest tests/core/test_approval.py` | WAIT_APPROVAL |
| 5 | **反馈闭环演示**：注入测试失败后 Agent 接收反馈并修正通过 | `python demo/mechanism_demo.py` | FeedbackLoop |
| 6 | **Mock LLM 测试**：核心机制在 Mock LLM 下有确定性单元测试 | `pytest tests/ -k "mock"` | MockAdapter |
| 7 | **凭据安全**：源码中无硬编码 key，config 文件在 `.gitignore` 中 | `grep -r "sk-" src/` 无结果 | 配置管理 |
| 8 | **一键测试**：`pytest -v` 全部 246 个测试通过 | `pytest -v --tb=short` | 全量测试 |
| 9 | **CLI 可用**：`ai4se-agent "task"` 单次模式和 `ai4se-agent` 交互模式均可启动 | 手动验证 | CLI 层 |
| 10 | **Prompt 模块化**：7 个 Section 独立构建、动态组合 | `pytest tests/context/` | PromptComposer |
| 11 | **EventBus 解耦**：FSM 不直接引用 Renderer，通过事件通信 | `pytest tests/core/test_event_bus.py` | EventBus |
| 12 | **跨会话记忆**：ConversationMemory 在交互模式跨轮次保留历史 | `pytest tests/session/test_history.py` | ConversationMemory |

---

## 10. 风险与未决问题

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **LLM 输出格式不稳定**，JSON 解析失败 | 循环卡住，无法继续 | 严格的 schema 校验 + JSON repair（修复常见转义错误）+ legacy fallback 双策略 |
| **长会话上下文膨胀** | Token 成本高、LLM 质量下降 | Token 计数 + 自动摘要 + ConversationMemory 滑动窗口（20 条最近消息） |
| **增量修正定位不准确** | 修正失败，无限循环 | 3 次增量无效后升级全量重规划；全局 40 轮上限兜底 |
| **测试环境差异**（用户本地依赖版本不同） | 测试执行失败被误判为代码错误 | FailureClassifier 区分系统错误和代码错误；明确的错误分类规则 |
| **`transitions` 版本兼容** | 运行时行为异常 | 在 `pyproject.toml` 中锁定大版本，测试覆盖所有状态转移 |
| **并发安全性** | 多进程写入 FailureDB 冲突 | 当前为单用户 CLI；未来可引入文件锁或迁移至独立 DB 连接 |
| **Windows 路径兼容性** | 路径分隔符/大小写导致工具行为不一致 | PathNormalizer 统一路径处理；`WorkspacePolicy` 跨平台路径逃逸检测 |

### 未决问题

1. **Plan-as-tool 的持久化策略**：plan_create/plan_update 的产物是否应写入 PersistentMemory？当前仅存在运行时内存中。
2. **FailureDB 的查询接口**：当前只写入不查询；未来是否需要支持 `/memory failures` 命令查看历史失败模式？
3. **多 Provider 并行**：是否支持同时配置多个 LLM provider 并按任务切换？当前一次只能激活一个。
4. **Session 摘要生成时机**：当前在 Session 结束时生成摘要；是否需要支持手动触发 `/summarize`？

---

## 11. 领域与机制设计

### 11.1 Coding 领域的反馈信号

在软件工程场景中，Agent 行为正确性有三种客观信号：

| 信号 | 工具 | 确定性 | 时效性 |
|------|------|--------|--------|
| **测试结果** | `pytest` (TestSensor) | 最高 —— 通过/失败是二值确定 | 中等 —— 需要编译/运行 |
| **Lint 结果** | `ruff` (LintSensor) | 高 —— 规则明确 | 快 —— 静态分析 |
| **类型检查** | `mypy` (TypeSensor) | 高 —— 类型系统约束 | 快 —— 静态分析 |

测试结果是最客观、最确定的反馈信号，作为 FeedbackLoop 的核心信号源。

### 11.2 危险动作

Agent 在编码场景中可能执行的 4 类危险动作：

| 类别 | 示例 | 拦截层级 |
|------|------|---------|
| **危险 shell 命令** | `rm -rf /`、`dd if=/dev/zero`、`wget malware.sh` | CommandPolicy (DENY) |
| **路径逃逸** | `../../etc/passwd`、`/etc/shadow` | WorkspacePolicy + FilePolicy (DENY) |
| **高风险 git 操作** | `git push`、`git reset --hard`、`git rebase` | GitPolicy (REQUIRE_APPROVAL) |
| **资源消耗** | 无限循环、大文件写入、fork 炸弹 | 超时控制 (ResourcePolicy) |

### 11.3 所需工具

5 个核心工具覆盖编码任务的完整操作链：读文件（`read_file`）→ 改文件（`edit_file`/`write_file`）→ 执行（`shell`）→ 验证（`run_test`）。

### 11.4 记忆需求

| 需求 | 实现 | 生命周期 |
|------|------|---------|
| 本轮上下文 | AgentState.context（messages 列表） | 单次 AgentRuntime |
| 跨轮次对话历史 | ConversationMemory（滑动窗口 20 条） | 一次交互 Session |
| 项目约定规则 | PersistentMemory（文件存储） | 跨 Session |
| 历史会话摘要 | Session Summaries（文件存储） | 跨 Session |
| 失败模式 | FailureDB（SQLite） | 跨 Session |

### 11.5 重点维度：反馈闭环 (Feedback Loop)

**为什么反馈闭环是本项目的核心贡献维度？**

1. **天然由代码构成**：Sensor → Classifier → Planner 三个组件全部是代码逻辑，非 Prompt 文本。这是"机制必须是代码"这一课程要求的最佳体现。

2. **可完全确定性测试**：通过 MockAdapter + MockSensor，反馈闭环可以在不调用真实 LLM 的情况下进行单元测试。246 个测试中反馈闭环相关测试占比最高。

3. **增量修正策略是核心工程问题**：Coding Agent 场景中，"一次改对"是理想，"改-测-改"是现实。修正策略（怎么定位失败、怎么决定增量和全量的切换阈值、怎么避免无效循环）是区分一个玩具 Agent 和生产级 Agent 的关键。

4. **体现工程深度**：相比工具分发（接口实现细节）或记忆（简单的文件读写），反馈闭环涉及 FailureClassifier 的规则设计、CorrectionPlanner 的策略编排、FailureDB 的持久化与查询，以及增量/全量修正的状态管理。

**反馈闭环的架构层级**：

```
ToolResult
    │
    ▼
┌─────────────────────────────────────┐
│           Sensor 层                  │
│  TestSensor:  pytest --tb=short     │
│    → 解析 passed/failed/errors       │
│    → 提取失败测试名、断言信息、行号     │
│  LintSensor:  ruff check .          │
│    → 解析错误代码、文件路径、行号       │
└──────────────┬──────────────────────┘
               │ Feedback
               ▼
┌─────────────────────────────────────┐
│       FailureClassifier             │
│  (规则驱动，零 LLM 调用)              │
│                                     │
│  "AssertionError"    → logic_error  │
│  "SyntaxError"       → syntax_error │
│  "ImportError"       → missing_dep  │
│  "Timeout"           → perf_error   │
│  "ruff E*"           → style_error  │
│  "mypy*"             → type_error   │
└──────────────┬──────────────────────┘
               │ category + severity
               ▼
┌─────────────────────────────────────┐
│        CorrectionPlanner            │
│                                     │
│  retry_count < 3:                   │
│    → 增量修正，定位到具体文件和函数      │
│  retry_count >= 3:                  │
│    → 全量重规划，重新理解需求再实现      │
│                                     │
│  输出: CorrectionPlan               │
│   {scope, target_files, strategy}   │
└──────────────┬──────────────────────┘
               │ CorrectionPlan
               ▼
        ┌─────────────┐
        │  FailureDB  │  ← SQLite 异步写入
        │  (持久化)    │
        └─────────────┘
               │
               ▼
        注入到下一轮 CONTEXT_ORG
        (通过 PromptContext.feedback)
```

**维度对比**：为什么反馈闭环优于其他候选维度

| 维度 | 优势 | 劣势 |
|------|------|------|
| **反馈闭环** | 全部代码机制，可确定性测试，工程深度大 | 实现复杂度较高 |
| 工具分发 | 接口清晰，实现简单 | 本质是 CRUD，工程深度有限 |
| 记忆系统 | 跨会话体验好 | 主要是文件 IO + 检索，代码机制少 |
| 护栏系统 | 安全价值高 | 规则数量和覆盖度决定质量，扩展性有限 |
| CLI 表现层 | 用户体验提升明显 | 表现层逻辑，非核心工程贡献 |
