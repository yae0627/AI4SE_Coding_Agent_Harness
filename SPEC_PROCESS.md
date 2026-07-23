# SPEC_PROCESS.md

> 记录与 Superpowers 协作生成 spec 与 plan 的过程。
>
> - brainstorming 关键节点
> - 至少 3 轮关键迭代的对话节选与处理决策
> - AI 建议采纳/推翻/修正的记录
> - 冷启动验证结果（第二个 agent 试运行）

## 阶段一：初步构思

### 2026-07-14

- 选定项目类型：A · Coding Agent Harness
- 技术栈：Python + openai SDK + pytest
- 重点维度：反馈闭环（Feedback Loop）
- 分发形态：PyPI

## 阶段二：Brainstorming — 架构设计（2026-07-21）

### 关键决策记录

| 决策点 | 选项 | 最终选择 | 理由 |
|--------|------|---------|------|
| LLM 供应商 | OpenAI / 本地模型 / 两者 | **两者都支持（可切换）** | 灵活，Mock 方便 |
| 反馈闭环深度 | 基础 / 推荐 / 深度 | **深度版：Validator + Classifier + Corrector + 增量修正 + 失败模式学习** | 作为重点维度，需体现工程深度 |
| 护栏机制 | 基础 / 中等 / 深度 | **深度版：HITL 状态机 + 可配置规则 + 范围围栏** | 符合"危险动作拦截必须是代码"的要求 |
| 主循环架构 | 同步循环 / 状态机 / 事件驱动 | **状态机驱动（transitions 库）** | 编码流程有固定闭环，状态机更适合可测试性 |
| 记忆系统 | 会话级 / 键值存储 / 向量语义 | **文件级键值存储 + 摘要索引** | 非重点维度，避免过度工程化，纯 I/O 可测 |
| 工具系统 | 基础三件套 / 增强 / 完整 | **完整版：含 edit_file、run_test 等** | MVP 5 个核心工具，其余为加分 |
| 凭据存储 | Windows Credential / .env / 加密文件 | **.env + 首次引导 + gitignore** | 简单、安全、可审计 |

### 关键迭代：Agent 提出的重要修正

1. **HITL 独立状态化**：Agent 指出 HITL 是一个暂停生命周期状态，不应作为 Guardrail 的分支。采纳 → 新增 `WAIT_APPROVAL` 状态。
2. **TOOL_ERROR 独立状态**：Agent 区分了"代码错误"（进 FEEDBACK）和"工具异常"（进 TOOL_ERROR）。采纳 → 新增 `TOOL_ERROR` 状态。
3. **Feedback Loop 架构边界**：Agent 指出 Corrector 不应直接修代码，而应生成修正建议由 LLM 执行。采纳 → 改名 `CorrectionPlanner`，只生成 `CorrectionPlan`。
4. **Classifier 规则驱动**：Agent 强调第一版 Classifier 必须用代码规则而非 LLM，否则失去确定性。采纳。
5. **Memory 分层**：Agent 建议区分短期（session）和长期（persistent）记忆，避免噪音污染。采纳。
6. **Guardrail 策略分层**：Agent 建议 CommandPolicy / FilePolicy / WorkspacePolicy / GitPolicy / ResourcePolicy 可插拔设计。采纳。
7. **WAIT_APPROVAL 超时策略**：Agent 建议超时后进入 STOP（记录 reason=approval_timeout）而非直接失败。采纳。

### 用户推翻/修正的决策

- **状态机方案**：初始推荐方案 A（简单同步循环），用户选择方案 B（状态机驱动），认为编码流程有固定闭环更适合状态机。
- **Feedback 深度**：初始询问基础版/推荐版/深度版，用户选择深度版含失败模式学习。

### 最终状态集合

11 状态：`IDLE → CONTEXT_ORG → LLM_CALL → ACTION_PARSE → GUARDRAIL → WAIT_APPROVAL → TOOL_EXEC → TOOL_ERROR → FEEDBACK → MEMORY_UPDATE → STOP`

### 产出文件

- `docs/superpowers/specs/2026-07-21-coding-agent-harness-design.md` — SPEC 设计文档
- `docs/superpowers/plans/2026-07-21-coding-agent-harness-plan.md` — PLAN 实现计划

## 阶段三：实现 — Subagent-Driven Development（2026-07-21）

### 任务执行概览

12 个 Task 按 PLAN.md 顺序执行，Tasks 2-9 可并行，实际按顺序串行实现以简化 review 流程。

| Task | 模块 | 文件数 | 测试数 | Commit |
|------|------|--------|--------|--------|
| 1 | Shared Types | 2 | 6 | fe93074 |
| 2 | AgentState | 2 | 3 | bd3bb5e |
| 3 | LLMAdapter | 6 | 3 | f662f57 |
| 4 | ActionParser | 2 | 3 | 13ffdc6 |
| 5 | Tool System | 13 | 9 | 857bffb |
| 6 | Guardrail System | 11 | 8 | 137d5f4 |
| 7 | Memory System | 6 | 5 | 79c3bed |
| 8 | Config | 2 | 2 | c8b2969 |
| 9 | Feedback Loop | 10 | 7 | c3818f0 |
| 10 | State Machine | 2 | 1 | 6d3320b |
| 11 | CLI Entry Point | 2 | 1 | 820c07a |
| 12 | Mechanism Demo | 2 | 5 demos | c0015a9 |

### 实现中发现并修复的 Bug

| Bug | 发现环节 | 修复方式 | Commit |
|-----|---------|---------|--------|
| `shell.py` 未使用的 `shlex` 导入 (F401) | Task 5 实现 | 删除 import | 5308950 |
| `memory/` gitignore 规则未锚定，阻塞 src 提交 | Task 7 实现 | 改为 `/memory/` | f7af73b |
| `transitions` 库 `self.state` 与 `model_attribute` 冲突 | Task 10 实现 | 添加 `model_attribute="_fsm_state"` | 6d3320b |
| `stop` 转换仅允许从 MEMORY_UPDATE 状态调用 | Task 10 实现 | 改为通配符 `"*"` | 6d3320b |
| `FailureDB` SQLite 连接未关闭，Windows 文件锁 | Task 12 审查 | 添加 `try/finally: conn.close()` | 2720ca1 |
| FeedbackLoop 接收 `None` 而非 `ToolResult` | 全分支审查 | 存储 `_last_tool_result` 并传递 | 46e4cd1 |
| 39 个 mypy 类型错误 | 最终验证 | 添加 `__getattr__`、`Optional`、`assert` 守卫 | a9a1a89 |

### 最终交付物

- **源代码**: 64 个文件，1432 行新增
- **测试**: 48 个单元测试，全部通过
- **类型检查**: mypy 零错误（38 个源文件）
- **Lint**: ruff 全部通过
- **CI/CD**: GitHub Actions + .gitlab-ci.yml 配置完成
- **机制演示**: 5 个 demo 脚本，覆盖护栏拦截、反馈闭环、增量修正、FailureDB、路径逃逸防护

## 阶段四：真实 API 验证与架构修复（2026-07-22）

### 冷启动验证：接入真实 LLM 暴露 3 个 Bug

接入 `njusehub.info` API（deepseek-v4-flash 模型）进行端到端验证，暴露 3 个关联 Bug：

| Bug | 类型 | 现象 | 根因 |
|-----|------|------|------|
| Bug 3（根因） | 架构设计缺陷 | LLM 收到空 messages `[]` | Context Engineering 层缺失：AgentState 存了 goal 但无机制构造 LLM 输入 |
| Bug 1 | 架构设计缺陷 | `503 model_not_found: gpt-4o` | 模型名硬编码在 OpenAIAdapter，ConfigLoader 无 model 映射 |
| Bug 2 | 逻辑错误 | `MachineError: Can't trigger retry_context from LLM_CALL` | 状态机只建模正常路径，LLM 调用失败时无合法转移 |

### 用户主导的架构分析

用户对 Bug 3 做了根因级定位，指出这不是简单的"忘记填充 context"，而是 **Context Engineering 层的架构缺失**：

1. **CONTEXT_ORG 职责不清**：同时做状态转移、context 初始化、prompt 管理、调 LLM，职责过重
2. **只初始化一次**：`if not context` 意味着后续反馈无法注入，LLM 不知道上一轮失败原因
3. **工具列表硬编码**：应从 ToolRegistry 动态生成

### 修复方案（用户设计，Agent 执行）

| 层级 | 修改前 | 修改后 |
|------|--------|--------|
| AgentState | `context=[]`（一次性填充） | `history=[]` + `feedback=[]`（分离存储） |
| 上下文构造 | `_on_context_org` 内联拼 prompt | `ContextBuilder.build(state)` 每轮动态生成 |
| 工具列表 | system prompt 硬编码 | 从 `ToolRegistry.list()` 动态生成 |
| 状态机 | 知道 prompt 细节 | 只调 `ContextBuilder`，不碰 prompt |
| 错误路径 | 只有正常路径 | 新增 `llm_error` 转移 `LLM_CALL → CONTEXT_ORG` |
| 模型配置 | 硬编码 `gpt-4o` | `OPENAI_MODEL` 环境变量，无默认值 |

### 新增模块

```
src/ai4se_agent/context/     ← 新增 Context Engineering 层
├── __init__.py
├── builder.py               # ContextBuilder.build(state) → messages
└── prompt.py                # build_system_prompt(tools) → str
```

### 验证结果

- **测试**: 53 个单元测试全部通过（新增 5 个 ContextBuilder 测试）
- **类型检查**: mypy 零错误（42 个源文件）
- **Lint**: ruff 零告警
- **真实 API**: `ai4se-agent "run shell command: dir"` → `Result: success (success) after 2 iterations`

## 阶段五：表现层设计 — Lightweight Observable CLI（2026-07-22）

### 背景

真实 API 验证通过后，用户端表现层仍为最简单的单次任务模式。需要向 OpenCode / Claude Code 风格靠拢，提供交互式会话、过程可视化、可调试性。

### 设计决策

| 决策点 | 选项 | 最终选择 | 理由 |
|--------|------|---------|------|
| 终端 UI 框架 | Rich / 原生 + colorama / 纯文本 | **colorama + 原生 input()** | 评分重点是 Harness 内核，避免重 UI 依赖 |
| 交互模式 | 纯单次 / 交互式 / 混合 | **混合（单次命令 + 交互式会话）** | 兼顾脚本使用和 Demo 演示 |
| 可视化策略 | emoji 标识 / 纯文本状态标记 | **纯文本 `[STATE]` 格式** | 用户要求不引入 emoji |
| 输出层级 | 单层 / 普通 + verbose 模式 | **普通 + `--verbose` 双模式** | 默认简洁，调试时展开 |
| 可观测性 | 仅终端输出 / 事件追踪 | **Tracer + JSON Trace 文件** | 支持回放和调试 |

### 产出文件

- `docs/superpowers/specs/2026-07-22-observable-cli-design.md` — 表现层设计规约
- `docs/superpowers/plans/2026-07-22-observable-cli-plan.md` — 实现计划（5 个 Task）

### 架构摘要

新增两个模块，核心层保持不变：

```
cli/                     ← 表现层
├── renderer.py          ← Renderer ABC + TerminalRenderer + NullRenderer
├── session.py           ← SessionManager：交互循环、会话管理
├── commands.py          ← 交互命令（/status, /reset, /verbose）
└── main.py              ← CLI 入口

observability/           ← 可观测性层
├── events.py            ← 事件类型（STATE_CHANGED, LLM_CALLED, TOOL_EXECUTED 等）
└── tracer.py            ← Tracer：record / save / replay

core/state_machine.py    ← 修改：添加 Renderer/Tracer 回调注入
```

核心原则：StateMachine 不知道表现层细节，通过抽象 Renderer 接口输出事件；CLI 只是订阅者之一。

### 实现结果

5 个 Task 通过 subagent-driven 执行完成：

| Task | 模块 | 新增文件 | 测试数 | Commit |
|------|------|---------|--------|--------|
| 1 | observability/ — Events + Tracer | 6 | 6 | 2559e4c |
| 2 | cli/renderer.py — Renderer ABC | 4 | 3 | 361ce5d |
| 3 | cli/session.py + commands.py + main.py | 6 | 6 | 60cae73 |
| 4 | state_machine.py — Renderer/Tracer 集成 | 2 | 1 | e1e761c |
| 5 | pyproject.toml — 入口点 + colorama | 1 | - | 9187fd8 |

### 验证结果

- **测试**: 69 个单元测试全部通过（新增 16 个）
- **类型检查**: mypy 零错误（49 个源文件）
- **Lint**: ruff 零告警
- **真实 API**: `ai4se-agent "run shell command: dir"` → 状态转移可见，`Result: success (success) after 2 iterations`

## 阶段四：Action Protocol Migration（2026-07-23）

### 背景

用户发现系统 prompt 存在 6 点架构问题：

| 当前 | 问题 |
|------|------|
| 工具描述写死 | 与 Tool 实现分离，新增工具需同步修改 |
| 文本 action (`action: name key=value`) | 转义脆弱，`\\n`/`\\\"` 解析易出错 |
| `[DONE]` 哨兵 | 不走 validate/guardrail 流程，与架构不一致 |
| Workflow 控制行为靠 prompt | 应靠 FSM + Feedback 代码机制 |
| 一个大 Prompt | 应 ContextBuilder 组合 |
| 静态环境 | 缺少动态 workspace context |

### 决策：分三阶段推进

**A. Action Protocol Migration（优先）**：Tool Schema → JSON Action → finish action
**B. Context Engineering**：Prompt 拆分 → Workflow 优化 → Workspace Context
**C. 可观测性优化**：Renderer / Trace 增强

### 用户修正设计

| 项目 | 原始方案 | 用户修正 |
|------|---------|---------|
| ToolSchema | `@dataclass ToolSchema` | `dict parameters`（OpenAI function calling 格式） |
| Action 字段 | `Action.params` | `Action.parameters` |
| Parser 返回 | `None` | `ParseResult(success, action, error)` |
| JSON 提取 | 直接 `json.loads` | 支持 ` ```json ``` ` 代码块包裹 |
| finish | 特殊处理 | 经过 Validator |
| Validator | 仅检查 required | 增加类型检查 |
| 迁移 | 直接替换 | 保留旧 Parser 作为 fallback |

### 关键迭代：JSON 转义问题

**Agent 诊断**：真实 LLM 在写 C++ 代码时，JSON content 字段中的双引号（如 `cout << " "` ）未转义为 `\"`，导致 `json.loads` 抛出 `JSONDecodeError`。harness 层面缺少 JSON 格式校验/修复机制。

**修复**：添加 JSON repair 逻辑（自动修复常见转义问题）+ 解析错误反馈给 LLM 重试。

### 实现概览

| Task | 模块 | 变更 | 测试数 | Commit |
|------|------|------|--------|--------|
| 1 | types + Tool schema foundation | ParseResult, Tool.schema ABC, list_schemas(), params→parameters | 4 | 12e6327 |
| 2 | Tool schema implementations | 5 个工具实现 schema | 5 | 812175e |
| 3 | ActionParser + ActionValidator | JSON+fallback 解析器, schema 驱动验证器 | 12 | 812175e |
| 4 | ContextBuilder + prompt | 动态生成 system prompt | 4 | 812175e |
| 5 | State machine: finish action | [DONE]→finish | 2 | 812175e |
| 6 | Integration wiring | 全线联通 | - | 812175e |
| fix | JSON repair | 修复未转义引号 + 错误反馈 | - | 5fc73aa |

### 验证结果

- **测试**: 85 个单元测试全部通过（新增 21 个）
- **真实 API**: `ai4se-agent "write a C++ merge sort program"` → 写文件、编译、运行成功

## 阶段六：Context Engineering & Observability（2026-07-23）

### 背景

Action Protocol Migration 完成后，系统 prompt 仍是巨石字符串，Renderer 输出截断过于激进，Trace 缺少时间维度。用户提出两个独立增强 track：

- **B. Context Engineering**：Prompt 拆分 → Workflow 优化 → Workspace Context 动态注入
- **C. Observability**：Renderer token/timing 统计 → Trace timestamp/elapsed_ms → 结构化回放

### 架构决策

| 决策点 | 选项 | 最终选择 | 理由 |
|--------|------|---------|------|
| Prompt 模块化 | 单文件多函数 / 一文件一段 / **组合模式** | **PromptComposer + 6 Section 组件** | 每个 section 独立测试、独立演进，统一 PromptContext 数据契约 |
| Section 接口 | `build(**kwargs)` / **`build(ctx: PromptContext)`** | **PromptContext 数据载体** | 类型安全，新增 section 不需改 Composer |
| Workspace 采集 | 内联到 ContextBuilder / **独立 WorkspaceCollector** | **独立 Collector + 5s TTL 缓存** | 单一职责，缓存避免每轮重复扫描 |
| Renderer 增强 | 硬编码截断 / **可配置 + ABC 扩展** | **on_token_usage/on_timing + max_output** | 保持向后兼容，NullRenderer 同步更新 |
| 执行方式 | Inline / **Subagent-Driven** | **Subagent-Driven（7 Tasks）** | B+C 独立 track，task 间两阶段 review |

### 关键迭代：用户推翻/修正的决策

- **Section 组合方式**：初始方案为简单"一文件一字符串"，用户要求改为 `PromptSection` ABC + `PromptComposer` 组合模式，统一 `build(ctx: PromptContext)` 协议
- **Renderer 截断**：初始为固定 200/300 字符，用户要求 `max_output` 可配置参数
- **Trace 回放**：初始只有 `replay(path)` 全量回放，用户要求 `replay_filtered(event_type=, min_iteration=)` 结构化过滤
- **Config 部署问题**：用户从仓库根目录运行 `ai4se-agent` 报 API key 缺失——确认为部署问题（CWD 不在 projects/），非代码 bug，不修改 ConfigLoader

### 实现概览

| Task | 模块 | 变更 | 测试数 |
|------|------|------|--------|
| 1 | PromptContext + PromptSection ABC | 新增数据载体 + 抽象协议 | 5 |
| 2 | 6 Section + PromptComposer | SystemRole/Tool/Format/Example/Workspace/Rules + 编排器 | 16 |
| 3 | WorkspaceCollector | OS/文件/git/时间 采集 + TTL 缓存 | 8 |
| 4 | ContextBuilder 集成 | prompt.py 简化、builder.py 重写、MemoryManager.get_rules() | 7 |
| 5 | Renderer 增强 | on_token_usage/on_timing、可配置截断、on_stop 汇总 | 9 |
| 6 | Trace 增强 | Event timestamp/elapsed_ms、Tracer record_token/replay_filtered | 11 |
| 7 | 全量验证 | 端到端测试 + 真实 LLM 验证 | - |

### 最终架构

```
context/
├── prompt_context.py     PromptContext dataclass（数据契约）
├── prompt_section.py     PromptSection ABC（统一协议）
├── prompt_composer.py    PromptComposer（编排器）
├── sections/             6 个 Section 实现
│   ├── system_role.py    "You are a coding agent..."
│   ├── tool_section.py   ctx.tools → 工具列表
│   ├── format_section.py JSON 格式 + 转义规则
│   ├── example_section.py 少样本示例
│   ├── workspace_section.py ctx.workspace → OS/文件/git
│   └── rules_section.py  ctx.rules → 项目规则
├── workspace.py          WorkspaceCollector + WorkspaceSnapshot
├── prompt.py             (简化) 仅 build_tool_descriptions()
└── builder.py            ContextBuilder：组装 PromptComposer + WorkspaceCollector

cli/
└── renderer.py           + on_token_usage / on_timing / max_output

observability/
├── events.py             + timestamp / elapsed_ms
└── tracer.py             + record_token / replay_filtered
```

### 验证结果

- **测试**: 128 个单元测试全部通过（Phase A 后 90 个 + 新增 38 个）
- **真实 API**: `ai4se-agent "write hello2.cpp that prints Hello AI4SE v2 and compile it"` → 写入 → g++ 编译 → `Hello AI4SE v2` ✅
- **Code Review**: 每个 Task 通过 spec compliance + code quality 两阶段 review，发现并修复 ToolSection 防御性 .get()、测试命名等 4 个问题