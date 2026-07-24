# AI4SE_Coding_Agent_Harness — Agent Workflow Conventions

> 本项目使用 Superpowers 框架开发，遵循以下工作规约。

## 1. Superpowers 技能使用顺序

brainstorming → writing-plans → using-git-worktrees → subagent-driven-development / executing-plans → test-driven-development → requesting-code-review → finishing-a-development-branch

## 2. Git 工作流

- **分支策略**：每个功能/模块开一个独立 worktree 或分支，对应一个 PR
- **分支命名**：`feat/<模块名>-<简述>` / `fix/<简述>` / `chore/<简述>`
- **Commit 规范**：遵循 Conventional Commits — `feat:` / `fix:` / `chore:` / `docs:` / `test:`
- **Commit message**：标注 subagent 信息，如 `feat: add validator (subagent: feedback-01)`

## 3. TDD 纪律

- 先写失败测试（红），再写最少代码使其通过（绿），再重构
- 核心机制必须有 mock/stub LLM 的确定性单元测试，不依赖网络和真实 LLM
- 所有测试通过才能标记 task 完成

## 4. AGENT_LOG 自动记录（强制）

**每完成一个 task，必须自动追加一条记录到 AGENT_LOG.md**，不允许事后补记。

### 记录格式

每条记录占比一行：

```
| 2026-07-21 14:30 | #task-03 | llm-adapter | Add LLMAdapter abstraction | - | a1b2c3d |
```

| 列 | 内容 | 自动/手动 |
|----|------|----------|
| 时间 | `YYYY-MM-DD HH:mm` | 自动 |
| Task | `#task-N` + 简短标签 | 手动 |
| 技能 | 触发的 Superpowers 技能名 | 手动 |
| 摘要 | 做了什么、关键决策（≤50 字） | 手动 |
| 人工干预 | 修改了什么、为什么；无干预则 `-` | 手动 |
| Commit | 对应 commit hash（截取前 7 位） | 自动 |

### 自动记录命令

每个 task 完成后，用以下命令追加记录：

```bash
python scripts/log_agent.py "#task-03" "llm-adapter" "Add LLMAdapter abstraction with OpenAI/Mock adapters" "-"
```

该脚本自动读取最新 commit hash 并写入 AGENT_LOG.md。

### 示例记录

```
| 2026-07-14 22:00 | #task-01 | brainstorming | 初始化项目骨架 | - | e9f9422 |
| 2026-07-21 15:00 | #task-02 | brainstorming | 完成 11 状态 FSM 设计 | 采纳 Agent 建议增加 WAIT_APPROVAL 和 TOOL_ERROR 状态 | - |
```

## 5. AGENT_LOG 记录规则

- 每个 task 完成且 commit 后**立即**追加
- Subagent 完成 task 后，在 commit message 中注明 `(subagent: <name>)`，并在 commit 后运行 `log_agent.py`
- 人工干预列必须诚实记录：修改了接口签名、重构了代码、修正了 bug 等
- 决策记录：重要决策（技术选型、架构变更）同时记录在 AGENT_LOG.md 和 SPEC_PROCESS.md 中

## 6. CI/CD 纪律

- 每次 push 后，CI 自动运行 `pytest` 测试
- 所有测试通过才能合并 PR
- CI 配置见 `.github/workflows/ci.yml` 和 `.gitlab-ci.yml`

### 6.1 Push 策略

- **默认不跑 CI**：日常开发 push 使用 `git push --no-verify`，跳过 pre-commit hooks 和 CI pipeline
- 仅在 PR 合并前或最终验收时手动触发 CI 运行

## 7. 阶段完成工作流（强制）

每完成一个 Phase 或一组关联 task 后，按以下顺序执行：

### 7.1 验证

```
pytest tests/ -v
```

确认全部测试通过，记录测试数量。

### 7.2 日志记录

```bash
python scripts/log_agent.py "<phase-tag>" "<skill>" "<summary>" "<intervention>"
```

### 7.3 文档同步

以下三个文件必须在 commit 前更新：

| 文件 | 更新内容 |
|------|---------|
| `AGENT_LOG.md` | 自动追加（§7.2），commit hash 在 commit 后修正 |
| `README.md` | 更新项目状态行（测试数量、Phase 进度） |
| `SPEC_PROCESS.md` | 新增阶段记录：问题 → 决策表 → 实现表格 → 验证结果 |

### 7.4 Commit

```bash
git add <changed-files> README.md SPEC_PROCESS.md AGENT_LOG.md
git commit -m "feat: <phase description>

<bullet points>

<N> tests pass.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### 7.5 Push

```bash
git push origin main --no-verify
```

### 7.6 Commit Hash 修正

Push 后获取最新 hash，修正 AGENT_LOG.md 中该阶段条目的 commit 列，再次 commit：

```bash
git add AGENT_LOG.md && git commit -m "chore: fix AGENT_LOG commit hashes" && git push origin main --no-verify
```

## 8. 包结构规约

```
src/ai4se_agent/
├── __init__.py
├── types.py              # 共享类型
├── cli.py                # CLI 入口
├── config/
│   └── loader.py         # 配置加载
├── core/
│   ├── agent_state.py    # AgentState
│   ├── action.py         # ActionParser + ActionValidator
│   └── state_machine.py  # 11 状态 FSM
├── llm/
│   ├── base.py           # LLMAdapter ABC
│   ├── openai_adapter.py
│   ├── local_adapter.py
│   └── mock_adapter.py
├── tools/
│   ├── base.py           # Tool ABC
│   ├── registry.py
│   ├── read_file.py
│   ├── write_file.py
│   ├── edit_file.py
│   ├── shell.py
│   └── run_test.py
├── guardrails/
│   ├── base.py           # Policy ABC
│   ├── engine.py
│   ├── command_policy.py
│   ├── file_policy.py
│   ├── workspace_policy.py
│   └── git_policy.py
├── feedback/
│   ├── loop.py           # FeedbackLoop 编排器
│   ├── sensor.py         # Sensor ABC + Test/Lint/TypeSensor
│   ├── classifier.py     # FailureClassifier（规则驱动）
│   ├── planner.py        # CorrectionPlanner
│   └── failure_db.py     # FailureDB (SQLite)
└── memory/
    ├── manager.py
    ├── session.py        # 运行时记忆
    └── persistent.py     # 持久化记忆
```

## 9. 凭据安全

- 所有 API Key 通过 `.env` 文件存储，`getpass` 隐藏输入引导
- `.env` 已加入 `.gitignore`，绝不提交 Git
- 绝不写入日志或终端历史

## 10. 测试约定

- 测试文件命名：`test_<模块名>.py`
- 测试目录结构：`tests/` 镜像 `src/` 结构
- mock LLM 放在 `tests/fixtures/` 下
- 运行测试：`pytest` 或 `python -m pytest`
- 每个 task 的测试必须**先写失败测试（红）→ 实现通过（绿）→ 再重构**