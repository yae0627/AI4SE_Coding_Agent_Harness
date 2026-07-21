# AI4SE_Coding_Agent_Harness

A **Coding Agent Harness** — an engineering system that wraps an LLM into a reliable, feedback-driven coding agent. Built with Python.

**核心等式：Agent = LLM + Harness。** LLM 负责"下一步做什么"的决策，Harness 提供治理、反馈、工具、记忆这层工程封装。

## 项目状态

✅ **已完成** — 12 个 Task 全部实现，48 个测试通过，mypy 零错误。

## 架构

```
src/ai4se_agent/
├── types.py              # 共享类型（Action, ToolResult, Feedback, GuardrailResult 等）
├── cli.py                # CLI 入口
├── config/
│   └── loader.py         # 配置加载（.env 支持）
├── core/
│   ├── agent_state.py    # AgentState 数据模型
│   ├── action.py         # ActionParser + ActionValidator
│   └── state_machine.py  # 11 状态 FSM 主循环
├── llm/
│   ├── base.py           # LLMAdapter ABC
│   ├── openai_adapter.py # OpenAI 适配器
│   ├── local_adapter.py  # 本地模型适配器（预留）
│   └── mock_adapter.py   # Mock 适配器（测试用）
├── tools/
│   ├── base.py           # Tool ABC
│   ├── registry.py       # 工具注册表
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
│   ├── sensor.py         # Sensor ABC + Test/Lint/TypeSensor
│   ├── classifier.py     # FailureClassifier（规则驱动）
│   ├── planner.py        # CorrectionPlanner
│   ├── failure_db.py     # FailureDB (SQLite)
│   └── loop.py           # FeedbackLoop 编排器
└── memory/
    ├── manager.py        # 记忆管理器
    ├── session.py        # 运行时记忆（deque）
    └── persistent.py     # 持久化记忆（文件存储）
```

## 状态机

11 状态 FSM（`transitions` 库）：

```
IDLE → CONTEXT_ORG → LLM_CALL → ACTION_PARSE → GUARDRAIL → 
WAIT_APPROVAL → TOOL_EXEC → [TOOL_ERROR | FEEDBACK] → 
MEMORY_UPDATE → [STOP | CONTEXT_ORG]
```

## 快速开始

```bash
# 安装依赖
pip install -e ".[dev]"

# 配置 API Key（首次运行）
cp .env.example .env
# 编辑 .env 填入你的 OPENAI_API_KEY

# 运行
ai4se-agent "你的任务描述"

# 或使用 Mock 模式（无需真实 LLM）
set LLM_PROVIDER=mock
ai4se-agent "测试任务"
```

## 运行测试

```bash
pytest -v           # 48 个测试
mypy src/           # 类型检查
ruff check src/     # Lint 检查
```

## 机制演示

```bash
python demo/mechanism_demo.py
```

演示 5 个核心机制：
1. 护栏拦截危险命令（`rm -rf /`）
2. 反馈闭环检测失败并生成修正计划
3. 增量修正策略（3 次失败后升级全量重规划）
4. FailureDB 持久化失败模式
5. WorkspacePolicy 拦截路径逃逸

## 重点维度：反馈闭环

```
Sensor (TestSensor / LintSensor / TypeSensor)
  → Feedback (success, category, message, source, severity)
  → FailureClassifier (规则驱动，非 LLM)
  → CorrectionPlanner (生成修正建议，不直接修代码)
  → FailureDB (SQLite 持久化失败模式)
```

- ✅ 反馈信号是代码机制，不是 Prompt
- ✅ 移除真实 LLM 后可以单测
- ✅ 有客观校验器（pytest / ruff / mypy）
- ✅ 有失败分类（AssertionError → logic_error 等）
- ✅ 有修正策略生成（CorrectionPlan）
- ✅ 能回灌 Agent Loop

## 安全边界

- API Key 通过 `.env` 文件存储，`getpass` 隐藏输入引导
- `.env` 已加入 `.gitignore`，绝不提交 Git
- 危险命令拦截为代码机制（CommandPolicy），非 Prompt 约束
- 文件操作限制在 workspace 内（WorkspacePolicy）
- 路径逃逸检测（`../../` 写出 workspace 被拦截）

## 技术栈

| 维度 | 选择 |
|------|------|
| 语言 | Python 3.10+ |
| LLM 供应商 | OpenAI + 兼容格式本地模型（可切换） |
| 状态机 | `transitions` |
| 测试 | pytest |
| Lint | ruff |
| 类型检查 | mypy |
| CI/CD | GitHub Actions + .gitlab-ci.yml |

## 分发

- PyPI: `pip install ai4se-agent`
- [设计文档](docs/superpowers/specs/2026-07-21-coding-agent-harness-design.md)
- [实现计划](docs/superpowers/plans/2026-07-21-coding-agent-harness-plan.md)

## 项目课程

本项目使用 [Superpowers](https://github.com/obra/superpowers) 框架开发，遵循 `brainstorming → writing-plans → using-git-worktrees → subagent-driven-development → test-driven-development → requesting-code-review → finishing-a-development-branch` 工作流。