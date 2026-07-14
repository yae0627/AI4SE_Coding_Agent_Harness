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

## 4. AGENT_LOG 记录格式

每条记录包含：

```
| 2026-07-14 | #task-01 | brainstorming | 初始化项目骨架 | - | af7f7e7 |
```

| 列 | 内容 |
|----|------|
| 时间 | YYYY-MM-DD HH:mm |
| Task | `#task-N` 编号 |
| 技能 | 触发的 Superpowers 技能名 |
| 摘要 | 做了什么、关键决策 |
| 人工干预 | 修改了什么、为什么 |
| Commit | 对应 commit hash |

## 5. 决策记录

重要决策（技术选型、架构变更）记录在 `AGENT_LOG.md` 和 `SPEC_PROCESS.md` 中。
SPEC_PROCESS.md 记录 brainstorming 阶段的迭代过程。

## 6. 包结构规约

```
src/ai4se_agent/
├── core/        # Agent 主循环（组织上下文 → 调用 LLM → 解析动作 → 分发执行 → 回灌 → 停机）
├── tools/       # 工具注册与分发（文件读写、shell、自定义工具）
├── feedback/    # 反馈闭环（Validator → Classifier → Corrector）— 重点维度
├── guardrails/  # 安全护栏（危险动作识别、HITL 状态机）
├── memory/      # 记忆系统（跨会话存储与检索）
└── config/      # 配置管理（凭据、规则、声明式配置）
```

## 7. 凭据安全

- 所有 API Key 通过操作系统钥匙串或加密文件存储
- 绝不硬编码进源码，绝不提交 Git
- 绝不写入日志或终端历史

## 8. 测试约定

- 测试文件命名：`test_<模块名>.py`
- mock LLM 放在 `tests/fixtures/` 下
- 运行测试：`pytest` 或 `python -m pytest`