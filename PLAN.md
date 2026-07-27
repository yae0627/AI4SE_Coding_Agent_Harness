# AI4SE Coding Agent Harness — 总体实现计划

> 本文档汇总所有阶段的实现任务，包含已完成的 commit hash 引用。截至 2026-07-27 所有阶段均已实现。

---

## Phase 1: Core Types & AgentState

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 1 | 共享类型 | `src/ai4se_agent/types.py`, `tests/core/test_types.py` | 定义 Action, ToolResult, Feedback, GuardrailResult, CorrectionPlan, StopReason 等核心类型 | `fe93074` |
| 2 | AgentState | `src/ai4se_agent/core/agent_state.py`, `tests/core/test_agent_state.py` | AgentState 数据模型：迭代计数、历史记录、重试计数等字段 | `bd3bb5e` |

**验证：** `pytest tests/core/test_types.py tests/core/test_agent_state.py -v`

---

## Phase 2: LLM Adapter & Action Parser

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 3 | LLMAdapter 抽象 | `src/ai4se_agent/llm/`, `tests/llm/test_adapters.py` | LLMAdapter ABC + OpenAIAdapter + MockAdapter | `f662f57` |
| 4 | Action 解析与验证 | `src/ai4se_agent/core/action.py`, `tests/core/test_action.py` | ActionParser (text parsing) + ActionValidator | `13ffdc6` |

**验证：** `pytest tests/llm/ tests/core/test_action.py -v`

---

## Phase 3: Tool System & Guardrails

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 5 | Tool System | `src/ai4se_agent/tools/`, `tests/tools/` | Tool ABC + ToolRegistry + 5 个工具 (read_file, write_file, edit_file, shell, run_test) | `857bffb` |
| 6 | Guardrail System | `src/ai4se_agent/guardrails/`, `tests/guardrails/` | Policy ABC + GuardrailEngine + 4 个策略 (Command, File, Workspace, Git) | `137d5f4` |

**验证：** `pytest tests/tools/ tests/guardrails/ -v`

---

## Phase 4: Memory, Config & Feedback Loop

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 7 | Memory System | `src/ai4se_agent/memory/`, `tests/memory/` | MemoryManager + SessionMemory + PersistentMemory | `79c3bed` |
| 8 | Configuration | `src/ai4se_agent/config/loader.py`, `tests/config/test_loader.py` | ConfigLoader — .env 文件加载和环境变量读取 | `c8b2969` |
| 9 | Feedback Loop | `src/ai4se_agent/feedback/`, `tests/feedback/` | Sensor + FailureClassifier + CorrectionPlanner + FailureDB (SQLite) + FeedbackLoop | `c3818f0` |

**验证：** `pytest tests/memory/ tests/config/ tests/feedback/ -v`

---

## Phase 5: State Machine & CLI Entry

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 10 | State Machine | `src/ai4se_agent/core/state_machine.py`, `tests/core/test_state_machine.py` | 11-state FSM (transitions 库) — IDLE → ... → STOP | `6d3320b` |
| 11 | CLI Entry Point | `src/ai4se_agent/cli.py`, `tests/test_cli.py`, `pyproject.toml` | CLI 入口 + harness builder + pyproject.toml entry point | `820c07a` |
| 12 | Mechanism Demo | `demo/mechanism_demo.py`, `demo/README.md` | 演示 guardrail/feedback/correction/FailureDB/workspace 五个核心行为 | `c0015a9` |

**验证：** `pytest tests/core/test_state_machine.py tests/test_cli.py -v && python demo/mechanism_demo.py`

---

## Phase 6: Bug Fixes & Context Engineering

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 13a | 上下文工程修复 | `src/ai4se_agent/core/action.py`... | ContextBuilder 层引入；修复上下文组织不足的问题 | `f822020` |
| 13b | JSON 修复 + 解析错误反馈 | `src/ai4se_agent/core/action.py`... | JSON unescaped quote 修复 + parse error 反馈回 LLM | `5fc73aa` |
| 13c | Mypy 修复 | 多个文件 | 修复 39 个 mypy 类型错误 | `a9a1a89` |
| 13d | SQLite 文件锁修复 | `src/ai4se_agent/feedback/failure_db.py` | Windows 平台 SQLite 连接显式关闭 | `2720ca1` |
| 13e | Parser 引号剥离 | `src/ai4se_agent/core/action.py` | ActionParser 参数值去引号处理 | `28c9949` |

**验证：** `pytest -q && mypy src/ && ruff check src/`

---

## Phase 7: Observable CLI

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 14a | 可观测性层 — Events + Tracer | `src/ai4se_agent/observability/`, `tests/observability/` | EventType 枚举 + Event 事件层次结构 + Tracer/NullTracer | `2559e4c` |
| 14b | Renderer ABC + TerminalRenderer | `src/ai4se_agent/cli/renderer.py`, `tests/cli/test_renderer.py` | Renderer ABC + NullRenderer + TerminalRenderer (colorama) | `361ce5d` |
| 15a | CLI 层重构 | `src/ai4se_agent/cli/` | SessionManager + interactive() + commands + argparse 入口 | `60cae73` |
| 15b | StateMachine 集成 | `src/ai4se_agent/core/state_machine.py` | Renderer/Tracer 回调注入 StateMachine | `e1e761c` |
| 15c | 构建配置清理 | `pyproject.toml` | entry point 更新 + colorama 依赖 | `9187fd8` |

**验证：** `pytest tests/observability/ tests/cli/ -v`

---

## Phase 8: Action Protocol Migration

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 16a | 类型 + Tool Schema 基础 | `types.py`, `tools/base.py`, `tools/registry.py`, `tests/tools/test_schema.py` | ParseResult 类型；Tool.schema 属性；ToolRegistry.list_schemas()；Action.params→parameters | `12e6327` |
| 16b | Tool Schema 实现 | 5 个工具文件 | 为所有工具添加 OpenAI function-calling 兼容 schema | 同 `812175e` |
| 17a | ActionParser/ActionValidator 重写 | `core/action.py`, `tests/core/test_action_json.py` | JSON 优先 + Legacy 回退；schema 驱动的验证器；类型检查 | `812175e` |
| 17b | ContextBuilder + 动态 Prompt | `context/prompt.py`, `context/builder.py` | 动态系统 prompt：根据 Tool schema 生成 JSON 格式 | 同 `812175e` |
| 17c | finish action + [DONE] 移除 | `core/state_machine.py` | [DONE] sentinel 替换为 finish action（通过验证器） | 同 `812175e` |
| 17d | 集成接线 | `cli/session.py` | ActionValidator 与 ToolRegistry schemas 对接 | 同 `812175e` |

**验证：** `pytest tests/core/test_action_json.py tests/tools/test_schema.py -v`

---

## Phase 9: Context Engineering & Observability

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 18a | PromptContext + PromptSection ABC | `context/prompt_context.py`, `context/prompt_section.py` | PromptContext 数据类 + PromptSection 抽象基类 | `8b54201` |
| 18b | 6 个 Section + PromptComposer | `context/sections/`, `context/prompt_composer.py` | SystemRole/Tool/Format/Example/Workspace/Rules 六个 section + 组合器 | `fafb8eb` |
| 18c | WorkspaceCollector + Snapshot | `context/workspace.py`, `tests/context/test_workspace.py` | WorkspaceSnapshot (frozen) + WorkspaceCollector (TTL 5s 缓存) | `658a47d` |
| 18d | ContextBuilder 集成 | `context/builder.py`, `core/state_machine.py` | PromptComposer 接入 ContextBuilder；MemoryManager.get_rules() | `9399a39` |
| 18e | Renderer 增强 | `cli/renderer.py` | on_token_usage / on_timing 方法；TerminalRenderer 输出截断 | `065115c` |
| 18f | Trace 增强 | `observability/events.py`, `observability/tracer.py` | Event 增加 timestamp/elapsed_ms；Tracer.record_token()/replay_filtered() | 同 `065115c` |

**验证：** `pytest tests/context/ tests/cli/test_renderer.py tests/observability/ -v`

---

## Phase 10: Deployment Optimization

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 19a | 配置模式 | `src/ai4se_agent/config/schema.py` | 配置 schema 定义 | `5593036` |
| 19b | 设置向导 | `src/ai4se_agent/config/wizard.py` | 首次运行设置向导 | `5593036` |
| 19c | LLM 管理器 | `src/ai4se_agent/llm/manager.py` | LLMManager — provider 选择与模型切换 | `5593036` |
| 19d | LocalAdapter | `src/ai4se_agent/llm/local_adapter.py` | OpenAI 兼容的本地模型适配器 | `5593036` |

**验证：** `pytest tests/config/ -v && python -m ai4se_agent.config.wizard --help`

---

## Phase 11: Session & Event Bus

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 20a | AgentEvent + EventBus | `core/events.py`, `core/event_bus.py`, `tests/core/test_events.py`, `tests/core/test_event_bus.py` | AgentEvent 数据类 (14 事件类型) + EventBus subscribe/publish | `3f755e7`, `36cf8ed` |
| 20b | MessageHistory | `session/history.py`, `tests/session/test_history.py` | 消息历史管理：add/get_recent/clear/trim | `175c377` |
| 20c | Session + AgentRuntime | `session/session.py`, `tests/session/test_session.py` | Session (持久化历史) + AgentRuntime (per-turn 隔离) | `7f421d4` |
| 20d | StateMachine emit() 集成 | `core/state_machine.py` | 所有 _on_* 方法添加 EventBus emit() 调用 | `d0b6f49` |
| 20e | TerminalRenderer 订阅 | `cli/renderer.py`, `tests/cli/test_renderer.py` | TerminalRenderer 通过 EventBus 订阅事件 | `6d556ed` |
| 20f | CLI Session 接线 | `cli/session.py`, `cli/main.py` | interactive() 改用 Session 驱动，EventBus 贯穿 | `edad2f2` |
| 20g | 完整测试通过 | — | 全部 131+ 测试 + ruff lint 通过 | `ac074b0` |

**验证：** `pytest tests/core/test_events.py tests/core/test_event_bus.py tests/session/ -v`

---

## Phase 12: Memory System Refactoring

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 12.1 | ConversationMemory type 字段 | `session/history.py` | `append()` 增加 `type: str = "text"` 参数，区分 text/action/message | `7d30c28` |
| 12.2 | 同步完整历史到 ConversationMemory | `session/session.py` | AgentRuntime.run() 后将完整 turn 历史同步回 ConversationMemory | `b4ae13d` |
| 12.3 | 从 MemoryManager 移除 session | `memory/manager.py` | MemoryManager 不再拥有 ConversationMemory，由 Session 直接管理 | `4f0cdad` |

**验证：** `pytest tests/session/ tests/memory/ -v`

---

## Phase 13: Respond Action (Phase 2.1)

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 13.1 | 添加 respond action | `core/state_machine.py`, `context/sections/format_section.py` | Respond action 触发 RESPOND FSM 状态；LLM 可用 respond 发送消息给用户 | `25e7af0` |

**验证：** `pytest -q`

---

## Phase 14: Human Interrupt + HITL (Phase 2.2-2.3)

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 14.1 | Human Interrupt | `core/interrupt.py`, `tests/core/test_interrupt.py` | InterruptChannel — 事件驱动的用户中断机制 | `9eb0344` |
| 14.2 | HITL 确认 | `core/state_machine.py`, `cli/renderer.py` | EventBus 驱动的确认流；TerminalRenderer 展示确认提示 | `9eb0344` |
| 14.3 | Ctrl+C 处理 | `cli/session.py` | 中断 agent 执行但保持会话存活 | `fd4f26d` |

**验证：** `pytest tests/core/test_interrupt.py -v`

---

## Phase 15: Terminal UI Phase 3-4

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 15.1 | 结构化终端 UI | `cli/terminal_ui.py`, `cli/viewport.py`, `cli/output_buffer.py`, `tests/cli/test_terminal_ui.py` | 备用屏幕 + 分区域布局 + 输出缓冲区 | `6912cc2`, `9aa6a71` |
| 15.2 | 流式 LLM 输出 | `cli/renderer.py`, `cli/terminal_ui.py` | Streaming LLM output in terminal UI | `9aa6a71` |
| 15.3 | 实时命令预览 | `cli/session.py` | 输入 `/` 时实时显示命令预览（ANSI 重绘） | `b52cc35` |
| 15.4 | 视觉状态指示器 | `cli/renderer.py` | Agent 执行时的黄色状态指示条 | `30b0619` |
| 15.5 | 键盘轮询 | `cli/session.py` | Agent 执行期间通过键盘轮询避免阻塞 input() | `da3a06f` |
| 15.6 | 输入行增强 | `cli/session.py` | 粗体提交、空白行分隔、初始提示 | `acf27f5`, `4a450d1`, `6235fe8` |

**验证：** `pytest tests/cli/ -v && python -m ai4se_agent.cli.main`

---

## Phase 16: Action Schema Separation

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 16.1 | ControlSchema 分离 | `core/action_schema.py` | 从 ToolRegistry 中分离 CONTROL_SCHEMAS (finish + respond) | `b387a75` |
| 16.2 | Prompt 集成 | `context/sections/format_section.py` | 在 prompt 中添加 respond action 的说明 | `b387a75` |

**验证：** `pytest tests/ -q`

---

## Phase 17: Communication Channel

4 个子阶段，10 个任务。

### Phase 17.1: 消息协议升级

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 17.1.1 | ParseResult message 字段 | `types.py`, `core/action.py`, `tests/core/test_action_json.py` | ParseResult 增加 `message: Optional[str]`；ActionParser 提取 LLM message | `ba8a3b7` |
| 17.1.2 | LLM_MESSAGE 事件 | `core/state_machine.py`, `tests/core/test_state_machine.py` | StateMachine._on_action_parse 中 emit LLM_MESSAGE 事件 | `50c38f7` |
| 17.1.3 | FormatSection 升级 | `context/sections/format_section.py` | Prompt 更新为 message+action 双字段 JSON 协议 | `91e8a85` |

### Phase 17.2: ask action

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 17.2.1 | ask → WAIT_INPUT | `core/state_machine.py`, `tests/core/test_state_machine.py` | RESPOND 状态替换为 WAIT_INPUT；respond action 保留向后兼容 | `df5600b` |
| 17.2.2 | 控制 schema 更新 | `core/action_schema.py` | respond 替换为 ask 控制 schema | `4a28c28` |

### Phase 17.3: TerminalRenderer LLM_MESSAGE 支持

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 17.3.1 | LLM_MESSAGE handler | `cli/renderer.py`, `tests/cli/test_renderer.py` | TerminalRenderer 添加 _on_llm_message 方法 | `303b585` |
| 17.3.2 | CLI 接线 | `cli/session.py` | SessionManager 中订阅 LLM_MESSAGE 事件 | `3395248` |

### Phase 17.4: ExampleSection 同步

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 17.4.1 | ExampleSection 更新 | `context/sections/example_section.py` | 示例从旧格式更新为 message+action 协议 | `884581c` |

**验证：** `pytest tests/core/test_action_json.py tests/context/test_prompt_section.py tests/cli/ -v`

---

## Phase 18: Cross-platform Path Handling

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 18.1 | 路径归一化器 | `core/sanitizer/path.py`, `tests/core/test_path_normalizer.py` | 4 层路径处理：分隔符统一 / 绝对路径判断 / 路径解析 / workspace 根路径 | `72ff0e0` |
| 18.2 | 工具集成 | `tools/registry.py`, `tests/tools/test_registry_path_normalize.py` | ToolRegistry.execute() 集成路径归一化 | `72ff0e0` |
| 18.3 | Windows 编码修复 | `tools/shell.py` | GBK 编码 subprocess 输出防止 crash | `cfeef96` |
| 18.4 | OS 命令提示 | `context/sections/workspace_section.py` | 根据操作系统提供命令提示（避免 Windows 上执行 Linux 命令） | `06bb137` |

**验证：** `pytest tests/core/test_path_normalizer.py tests/tools/test_registry_path_normalize.py -v`

---

## Phase 19: UX Fixes

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 19.1 | 展示工具输出预览 | `cli/renderer.py` | 成功和失败时均展示 tool output 预览 | `c0e7e89` |
| 19.2 | 消息仅响应处理 | `core/state_machine.py` | message-only response 停止本轮循环而非继续 | `4f85c2b` |
| 19.3 | Ctrl+C 保持会话 | `cli/session.py` | 中断 agent 但不退出 CLI | `fd4f26d` |
| 19.4 | 移除冗余 LLM JSON | `session/session.py`, `core/agent_state.py` | 从 conversation history 中移除原始 LLM JSON | `f19eea3` |
| 19.5 | Tool 重试错误反馈 | `core/state_machine.py` | Tool retry 耗尽时将错误信息传回 LLM | `82c724f`, `0db2bfc` |
| 19.6 | CLI 视觉改进 | `cli/renderer.py` | 重复消息渲染修复 + 视觉设计改进 | `4546d5f` |

**验证：** `pytest -q`

---

## Phase 20: Plan-as-Tool Mechanism

| # | 任务 | 文件 | 描述 | Commit |
|---|------|------|------|--------|
| 20.1 | Plan-as-Tool | `core/state_machine.py`, `context/sections/plan_section.py`, `tests/core/test_plan.py` | 双层级迭代计数器（外层 plan iteration + 内层 step iteration）；plan transition 信号增强 | `f018e45`, `028f778` |
| 20.2 | Prompt 集成 | `context/sections/plan_section.py` | Plan 机制在 system prompt 中的说明 | 同 `f018e45` |

**验证：** `pytest tests/core/test_plan.py -v`

---

## 依赖关系图

```
Phase 1 (Types + AgentState)
  ├── Phase 2 (LLM + Parser)
  ├── Phase 3 (Tools + Guardrails)
  └── Phase 4 (Memory + Config + Feedback)
           │
Phase 1-4 ─┴── Phase 5 (StateMachine + CLI + Demo)
           │
           └── Phase 6 (Bug Fixes + Context Engineering)
                    │
Phase 6 ────────────┤
                    ├── Phase 7 (Observable CLI)
                    ├── Phase 8 (Action Protocol Migration)
                    ├── Phase 9 (Context Engineering & Observability)
                    └── Phase 10 (Deployment Optimization)
                             │
Phase 7-10 ─────────────────┤
                             ├── Phase 11 (Session & Event Bus)
                             ├── Phase 12 (Memory Refactoring)
                             ├── Phase 13 (Respond Action)
                             ├── Phase 14 (HITL + Interrupt)
                             ├── Phase 15 (Terminal UI)
                             └── Phase 16 (Action Schema Separation)
                                      │
Phase 11-16 ──────────────────────────┤
                                      ├── Phase 17 (Communication Channel)
                                      ├── Phase 18 (Cross-platform Path)
                                      ├── Phase 19 (UX Fixes)
                                      └── Phase 20 (Plan-as-Tool)
```

---

## 项目文件结构（最终）

```
src/ai4se_agent/
├── __init__.py
├── types.py                          # 核心类型 (Action, ToolResult, Feedback, etc.)
├── config/
│   ├── __init__.py
│   ├── loader.py                     # ConfigLoader — .env + 环境变量
│   ├── schema.py                     # 配置 schema 定义
│   └── wizard.py                     # 首次运行设置向导
├── core/
│   ├── __init__.py
│   ├── action.py                     # ActionParser (JSON+Legacy) + ActionValidator (schema驱动)
│   ├── action_schema.py              # CONTROL_SCHEMAS (ask, finish)
│   ├── agent_state.py                # AgentState 数据模型
│   ├── event_bus.py                  # EventBus subscribe/publish
│   ├── events.py                     # AgentEvent 数据类 (14 事件类型)
│   ├── interrupt.py                  # InterruptChannel — HITL 机制
│   ├── state_machine.py              # HarnessStateMachine (11-state FSM)
│   └── sanitizer/
│       ├── __init__.py
│       └── path.py                   # 4 层跨平台路径处理
├── llm/
│   ├── __init__.py
│   ├── base.py                       # LLMAdapter ABC
│   ├── manager.py                    # LLMManager — provider 选择
│   ├── mock_adapter.py               # MockAdapter (测试用)
│   ├── openai_adapter.py             # OpenAIAdapter
│   └── local_adapter.py              # LocalAdapter (OpenAI 兼容)
├── tools/
│   ├── __init__.py
│   ├── base.py                       # Tool ABC with schema property
│   ├── registry.py                   # ToolRegistry (register/execute/list_schemas)
│   ├── read_file.py                  # ReadFileTool
│   ├── write_file.py                 # WriteFileTool
│   ├── edit_file.py                  # EditFileTool
│   ├── shell.py                      # ShellTool
│   └── run_test.py                   # RunTestTool
├── guardrails/
│   ├── __init__.py
│   ├── base.py                       # Policy ABC
│   ├── engine.py                     # GuardrailEngine
│   ├── command_policy.py             # 危险命令拦截
│   ├── file_policy.py                # 受保护文件路径
│   ├── workspace_policy.py           # workspace 逃逸防护
│   └── git_policy.py                 # Git 高风险操作（需要审批）
├── feedback/
│   ├── __init__.py
│   ├── sensor.py                     # Sensor ABC + TestSensor + LintSensor + TypeSensor
│   ├── classifier.py                 # FailureClassifier (规则分类)
│   ├── planner.py                    # CorrectionPlanner
│   ├── failure_db.py                 # FailureDB (SQLite)
│   └── loop.py                       # FeedbackLoop orchestrator
├── memory/
│   ├── __init__.py
│   ├── manager.py                    # MemoryManager (仅持久化 + 失败日志)
│   ├── session.py                    # SessionMemory (运行时)
│   └── persistent.py                 # PersistentMemory (project_rules, summaries)
├── context/
│   ├── __init__.py
│   ├── prompt.py                     # build_tool_descriptions()
│   ├── prompt_context.py             # PromptContext 数据类
│   ├── prompt_section.py             # PromptSection ABC
│   ├── prompt_composer.py            # PromptComposer
│   ├── builder.py                    # ContextBuilder (组装 messages)
│   ├── workspace.py                  # WorkspaceCollector + WorkspaceSnapshot
│   └── sections/
│       ├── __init__.py
│       ├── system_role.py            # 系统角色描述
│       ├── tool_section.py           # 工具列表描述
│       ├── format_section.py         # JSON 响应格式 (message+action 协议)
│       ├── example_section.py        # 示例会话
│       ├── workspace_section.py      # 工作区环境信息 (OS/路径/Git)
│       ├── rules_section.py          # 项目规则
│       └── plan_section.py           # Plan-as-Tool 机制说明
├── observability/
│   ├── __init__.py
│   ├── events.py                     # Event 基类 (timestamp/elapsed_ms) + 子类
│   └── tracer.py                     # Tracer + NullTracer (save/replay/replay_filtered)
├── session/
│   ├── __init__.py
│   ├── history.py                    # ConversationMemory (typed messages)
│   └── session.py                    # Session + AgentRuntime
├── cli/
│   ├── __init__.py
│   ├── main.py                       # argparse 入口
│   ├── session.py                    # SessionManager (interactive/submit/commands)
│   ├── renderer.py                   # Renderer ABC + NullRenderer + TerminalRenderer
│   ├── commands.py                   # 交互式命令处理器
│   ├── terminal_ui.py                # 备用屏幕终端 UI
│   ├── viewport.py                   # 视口管理
│   └── output_buffer.py              # 输出缓冲区
└── cli.py                            # [已删除，迁移到 cli/]

tests/
├── __init__.py
├── test_cli.py
├── core/
│   ├── __init__.py
│   ├── test_types.py
│   ├── test_agent_state.py
│   ├── test_action.py
│   ├── test_action_json.py
│   ├── test_events.py
│   ├── test_event_bus.py
│   ├── test_interrupt.py
│   ├── test_path_normalizer.py
│   ├── test_json_repair_escapes.py
│   ├── test_plan.py
│   └── test_state_machine.py
├── llm/
│   ├── __init__.py
│   └── test_adapters.py
├── tools/
│   ├── __init__.py
│   ├── test_registry.py
│   ├── test_registry_path_normalize.py
│   ├── test_schema.py
│   ├── test_read_file.py
│   ├── test_write_file.py
│   ├── test_edit_file.py
│   ├── test_shell.py
│   └── test_run_test.py
├── guardrails/
│   ├── __init__.py
│   ├── test_engine.py
│   ├── test_command_policy.py
│   ├── test_file_policy.py
│   ├── test_workspace_policy.py
│   └── test_git_policy.py
├── feedback/
│   ├── __init__.py
│   ├── test_sensor.py
│   ├── test_classifier.py
│   ├── test_planner.py
│   ├── test_failure_db.py
│   └── test_loop.py
├── memory/
│   ├── __init__.py
│   ├── test_manager.py
│   ├── test_session.py
│   └── test_persistent.py
├── config/
│   ├── __init__.py
│   └── test_loader.py
├── context/
│   ├── __init__.py
│   ├── test_builder.py
│   ├── test_prompt_section.py
│   └── test_workspace.py
├── observability/
│   ├── __init__.py
│   ├── test_events.py
│   └── test_tracer.py
├── session/
│   ├── __init__.py
│   ├── test_history.py
│   └── test_session.py
└── cli/
    ├── __init__.py
    ├── test_renderer.py
    ├── test_session.py
    ├── test_terminal_ui.py
    └── test_read_idle.py
```
