# Coding Agent Harness — 设计规约

> AI4SE 期末项目 A · SPEC
> 日期：2026-07-21
> 技术栈：Python + openai SDK + pytest + transitions

---

## 1. 问题陈述

### 1.1 要解决的问题

当前 LLM 在软件工程场景中面临的核心矛盾：**LLM 擅长"下一步做什么"的决策，但缺乏可靠的工程封装**。一个裸 LLM 在编码场景中会：

- 执行危险操作（删除文件、运行破坏性命令）而无拦截
- 无法感知自身行为的正确性——写完代码后没有机制验证它是否正确
- 在长会话中上下文膨胀，丢失关键信息
- 跨会话"失忆"，每次重新学习项目约定

**Coding Agent Harness** 解决的是：将 LLM 的决策能力封装进一个有状态、可治理、有反馈的系统，使其能稳定、可靠地完成编码任务。

### 1.2 目标用户

- 使用 AI 辅助编码的开发者，需要一个可信任的本地编码助手
- 需要在受控环境中运行编码 agent 的团队（沙箱 + HITL 审批）

### 1.3 为什么值得做

核心等式：**Agent = LLM + Harness**。本项目不是"又一个 AI 编码助手"，而是对 harness 层的工程实践——当 LLM 能完成大部分"思考"时，工程师的价值落在治理、反馈、上下文、安全这层工程上。

---

## 2. 用户故事

1. 作为一个开发者，我向 agent 提交一个编码任务，agent 能自主完成读代码、修改、测试、修正的循环，而不需要我每一步手动干预。
2. 作为一个开发者，当 agent 要执行危险操作（如 `rm -rf`、`git push`）时，系统会拦截并要求我确认，避免意外破坏。
3. 作为一个开发者，agent 修改代码后会自动运行测试，如果测试失败，它会分析失败原因并尝试修正，而不是直接告诉我"我改完了"。
4. 作为一个开发者，我可以在配置文件中定义项目规则（如编程风格、测试要求），agent 会自动遵守这些约定。
5. 作为一个开发者，我可以在跨会话的任务中看到 agent 记住了之前项目的架构决策和失败模式，不需要每次都重新说明。

---

## 3. 功能规约

### 3.1 Agent 主循环（状态机驱动）

**输入**：用户任务描述（文本）
**行为**：11 状态 FSM 驱动，每次迭代经过 `CONTEXT_ORG → LLM_CALL → ACTION_PARSE → GUARDRAIL → [WAIT_APPROVAL] → TOOL_EXEC → [TOOL_ERROR | FEEDBACK] → MEMORY_UPDATE → [STOP | CONTEXT_ORG]`
**输出**：任务结果（成功/失败 + 原因 + 产物）
**边界条件**：最大迭代次数 20 轮；连续 3 次修正失败自动停机；LLM 调用连续失败 3 次停机
**错误处理**：每状态有独立异常捕获，异常进入 TOOL_ERROR 或 STOP

### 3.2 状态机状态定义

| 状态 | 输入 | 行为 | 输出 | 后继状态 |
|------|------|------|------|---------|
| IDLE | 用户任务 | 接收任务，初始化 AgentState | 任务上下文 | CONTEXT_ORG |
| CONTEXT_ORG | 任务 + 历史 + 记忆 + 反馈 | 组装 messages，检查 token 数，超限则摘要 | 完整 messages | LLM_CALL |
| LLM_CALL | messages | 调用 LLMAdapter.generate() | LLM 回复文本 | ACTION_PARSE |
| ACTION_PARSE | LLM 回复 | 格式校验 → schema 校验 → 参数校验 | Action | GUARDRAIL / CONTEXT_ORG |
| GUARDRAIL | Action | 按策略集检查，聚合结果 | GuardrailResult | TOOL_EXEC / WAIT_APPROVAL / CONTEXT_ORG |
| WAIT_APPROVAL | 待审批 Action | 打印详情，等待 y/n/超时 | 审批结果 | TOOL_EXEC / CONTEXT_ORG / STOP |
| TOOL_EXEC | Action | 从 Registry 查找工具，执行 | ToolResult | FEEDBACK / TOOL_ERROR |
| TOOL_ERROR | ToolResult | 区分 retryable/fatal，retryable 自动重试 | 错误处理结果 | 重试 TOOL_EXEC / STOP |
| FEEDBACK | ToolResult | Sensor → Feedback → Classifier → CorrectionPlanner | CorrectionPlan | CONTEXT_ORG / MEMORY_UPDATE |
| MEMORY_UPDATE | 本轮关键信息 | 写入 session 记忆，条件写入 long-term | 更新状态 | CONTEXT_ORG / STOP |
| STOP | 终止原因 | 记录 ExitReason，输出最终结果 | 任务结果 | — |

### 3.3 工具系统

**接口**：
```python
class Tool:
    name: str
    def execute(self, params: dict) -> ToolResult
```

**核心工具（MVP）**：

| 工具 | 参数 | 输出 | 说明 |
|------|------|------|------|
| `read_file` | path, start_line?, end_line? | 文件内容 | 支持行范围读取 |
| `write_file` | path, content | 写入结果 | 整文件写入 |
| `edit_file` | path, old_string, new_string | 编辑结果 | 精确替换，支持增量修正 |
| `shell` | command, timeout?, workdir? | stdout, stderr, exit_code | 带超时控制 |
| `run_test` | test_path?, args? | 测试结果 | 调用 pytest，解析输出 |

**加分工具**：`grep`、`glob`、`git status/diff`

### 3.4 反馈闭环（重点维度）

**架构**：

```
FEEDBACK 状态
    │
    ├── Sensor 层
    │   ├── TestSensor  — 运行测试，解析 pytest 输出
    │   ├── LintSensor  — 运行 ruff，解析 lint 错误
    │   └── TypeSensor  — 运行 mypy，解析类型错误
    │
    ├── Feedback 对象
    │   success, category, message, details, severity, source
    │
    ├── FailureClassifier（规则驱动，非 LLM）
    │   "AssertionError" → logic_error
    │   "lint" → syntax_error
    │   "mypy" → type_error
    │
    ├── CorrectionPlanner
    │   生成 CorrectionPlan(scope, target_files, strategy)
    │   不直接修代码，只给 LLM 提供修正建议
    │
    └── FailureDB（SQLite，异步写入）
        记录失败模式，供后续查询
```

**增量修正策略**：
- `retry_count < 3`：增量修正（只修改失败部分）
- `retry_count >= 3`：升级为全量重规划

### 3.5 护栏系统

**GuardrailEngine**：聚合多 Policy 检查结果

**Policy 集**：
- `CommandPolicy`：危险 shell 命令拦截（`rm -rf /`, `dd`, `wget` 等）
- `FilePolicy`：路径越界保护（`real_path.startswith(workspace)`），禁止写 `.git/` 等
- `WorkspacePolicy`：`../../` 路径逃逸检测
- `GitPolicy`：高风险 git 操作需 HITL（`git push`, `git reset --hard`）
- `ResourcePolicy`：超时、文件大小限制

**GuardrailResult**：
```python
@dataclass
class GuardrailResult:
    verdict: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"]
    reason: str
    policy: str
    severity: int
    metadata: dict
```

### 3.6 记忆系统

**分层设计**：

| 层级 | 存储 | 生命周期 | 内容 |
|------|------|---------|------|
| Runtime | `memory/session/` | 一次会话 | 对话历史、工具结果、失败信息 |
| Persistent | `memory/project_rules/` | 跨会话 | 项目约定、架构决策 |
| Persistent | `memory/session_summaries/` | 跨会话 | 历史会话摘要 |
| Persistent | `memory/failure.db` (SQLite) | 跨会话 | 失败模式记录 |

**加载策略**：启动时只加载 `project_rules` 索引；会话摘要按需检索；failure.db 仅在 FEEDBACK 阶段写入

### 3.7 配置管理

**凭据来源优先级**：
1. 环境变量（`OPENAI_API_KEY`, `LOCAL_MODEL_URL`）
2. `.env` 文件（加入 `.gitignore`）
3. 首次运行引导：`getpass` 隐藏输入 → 写入 `.env`

**LLMAdapter 切换**：
- `OpenAIAdapter`：读 `OPENAI_API_KEY` + `OPENAI_BASE_URL`
- `LocalAdapter`：读 `LOCAL_MODEL_URL` + `LOCAL_MODEL_NAME`
- `MockAdapter`：返回预设响应，用于测试
- 通过 `config.yaml` 指定 `active_provider`

---

## 4. 非功能性需求

### 4.1 性能
- 单次 LLM 调用超时 60s
- 工具执行超时：shell 30s，测试 120s
- 状态机状态转移无感知延迟

### 4.2 安全
- API Key 绝不硬编码，绝不提交 Git，绝不写入日志
- `.env` 在 `.gitignore` 中
- 所有文件操作限制在 workspace 内
- 危险命令拦截为代码机制，非 prompt 约束

### 4.3 可用性
- CLI 界面，清晰的步骤输出
- HITL 时打印完整的危险动作详情
- 退出时显示 ExitReason

### 4.4 可观测性
- 每轮迭代输出当前状态和关键信息
- AgentState 可序列化，用于调试
- AGENT_LOG.md 记录关键节点

---

## 5. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    AgentRuntime                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │                 StateMachine                       │  │
│  │  IDLE → CONTEXT_ORG → LLM_CALL → ACTION_PARSE     │  │
│  │  → GUARDRAIL → [WAIT_APPROVAL] → TOOL_EXEC        │  │
│  │  → [TOOL_ERROR | FEEDBACK] → MEMORY_UPDATE        │  │
│  │  → [STOP | CONTEXT_ORG]                            │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌────────┐ │
│  │ Context  │  │ Guardrail │  │   Tool   │  │ Memory │ │
│  │ Manager  │  │  Engine   │  │ Registry │  │Manager │ │
│  └────┬─────┘  └───────────┘  └──────────┘  └────────┘ │
│       │                                                  │
│  ┌────▼─────┐                                           │
│  │LLMAdapter│                                           │
│  │(OpenAI/  │                                           │
│  │ Local/   │                                           │
│  │ Mock)    │                                           │
│  └──────────┘                                           │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │               FeedbackLoop                         │  │
│  │  Sensor → Feedback → Classifier → Planner          │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 外部依赖
- `openai>=1.0.0` — LLM 调用（OpenAI 兼容格式）
- `transitions` — 状态机引擎
- `pytest>=8.0` — 测试（dev 依赖）
- `ruff` — lint 检查（dev 依赖）
- `mypy` — 类型检查（dev 依赖）

---

## 6. 数据模型

### AgentState
```python
@dataclass
class AgentState:
    current_state: str
    goal: str
    iteration: int
    context: list[dict]        # messages 历史
    history: list[Turn]
    last_action: Action | None
    last_observation: str | None
    error_count: int
    retry_count: int
```

### Action
```python
@dataclass
class Action:
    name: str
    params: dict
```

### ToolResult
```python
@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None
    metadata: dict
```

### Feedback
```python
@dataclass
class Feedback:
    success: bool
    category: str
    message: str
    details: dict
    severity: int
    source: str          # "pytest" | "ruff" | "mypy"
```

### CorrectionPlan
```python
@dataclass
class CorrectionPlan:
    scope: str                # 失败区域定位
    target_files: list[str]
    strategy: str             # 修正建议描述
    retry_count: int
```

### GuardrailResult
```python
@dataclass
class GuardrailResult:
    verdict: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"]
    reason: str
    policy: str
    severity: int
    metadata: dict
```

---

## 7. 凭据与分发设计

### 7.1 凭据存储
- 来源：环境变量 → `.env` → 首次运行引导
- `.env` 已加入 `.gitignore`，绝不提交
- 首次运行：`getpass.getpass()` 隐藏输入，写入 `.env`
- 查看状态：`ai4se-agent config status` 显示已配置的 provider（不显示 key 明文）
- 更新：重新运行引导或直接编辑 `.env`

### 7.2 分发形态
- **PyPI 包**：`pip install ai4se-agent`
- 安装后命令：`ai4se-agent run "<task>"` 或交互模式 `ai4se-agent`
- 首次运行自动引导配置 API Key

---

## 8. 技术选型与理由

| 维度 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3.10+ | 课程要求，生态成熟，LLM SDK 支持好 |
| LLM 供应商 | OpenAI + 兼容格式本地模型 | 灵活切换，Mock 方便 |
| 状态机 | `transitions` | 轻量、声明式、可测试，非 agent 框架 |
| 测试 | pytest | 标准选择，覆盖 mock/stub 测试 |
| 分发 | PyPI (setuptools) | 与 pyproject.toml 一致 |
| 凭据 | `.env` + `python-dotenv` | 简单、安全、可审计 |

---

## 9. 验收标准

1. **状态机可运行**：给定一个任务，agent 能完整走完 IDLE → ... → STOP 循环
2. **工具可执行**：`read_file`、`write_file`、`edit_file`、`shell`、`run_test` 均能正常调用
3. **护栏拦截**：`rm -rf /` 等危险命令被 DENY；`../../etc/passwd` 写入被拦截
4. **HITL 可用**：危险 git 操作暂停等待用户输入，超时则终止
5. **反馈闭环演示**：注入一个测试失败，agent 接收反馈后修正代码并通过测试
6. **Mock LLM 测试**：核心机制（护栏、反馈、工具分发）在 mock LLM 下有确定性单元测试
7. **凭据安全**：源码中无硬编码 key，`.env` 在 `.gitignore` 中
8. **一键测试**：`pytest` 通过所有测试

---

## 10. 领域与机制设计

### 10.1 Coding 领域的反馈信号
- 测试结果（`pytest` 退出码和输出）— 最客观、最确定
- Lint 结果（`ruff`）— 代码风格和语法
- 类型检查结果（`mypy`）— 类型安全

### 10.2 危险动作
- 危险 shell 命令（`rm -rf`, `dd`, 格式化等）
- 路径逃逸（`../../` 写出 workspace）
- 高风险 git 操作（`push`, `reset --hard`）
- 资源消耗（无限循环、大文件写入）

### 10.3 所需工具
`read_file`、`write_file`、`edit_file`、`shell`、`run_test`

### 10.4 记忆需求
- 短期：当前会话上下文（滑动窗口）
- 长期：项目约定、架构决策、历史摘要、失败模式

### 10.5 重点维度：反馈闭环
反馈闭环被选为主要贡献维度，原因：
1. 天然由代码构成（Sensor → Classifier → Planner），符合"机制必须是代码"
2. 可完全通过 mock LLM 进行确定性测试
3. 增量修正策略是 Coding Agent 场景的核心工程问题
4. 相比工具分发或记忆，反馈闭环最能体现工程深度

---

## 11. 风险与未决问题

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LLM 输出格式不稳定，Action 解析失败 | 循环卡住 | 严格的 schema 校验 + 重试机制 |
| 长会话上下文膨胀 | 成本高、质量下降 | Token 计数 + 自动摘要 |
| 增量修正定位不准确 | 修正失败 | 3 次增量无效后升级全量重规划 |
| 测试环境差异（用户本地依赖） | 测试执行失败 | 明确的错误分类，区分系统错误和代码错误 |
| transitions 库版本兼容 | 运行时异常 | 锁定版本，测试覆盖状态转移 |