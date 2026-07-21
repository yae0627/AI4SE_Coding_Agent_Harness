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
- 待生成：`PLAN.md` — 实现计划（下一阶段）