# AI4SE 期末项目 · A · Coding Agent Harness — 提交清单

> 姓名：<!-- TODO: 填你的名字 -->  
> 学号：<!-- TODO: 填你的学号 -->  
> 日期：2026-07-27

---

## 仓库与发布

| 项目 | 链接 |
|------|------|
| GitHub 仓库 | https://github.com/yae0627/AI4SE_Coding_Agent_Harness |
| Release (v0.1.0) | https://github.com/yae0627/AI4SE_Coding_Agent_Harness/releases/tag/v0.1.0 |

---

## 交付物

| # | 文件 | 位置 |
|---|------|------|
| 1 | SPEC.md | [SPEC.md](SPEC.md) |
| 2 | PLAN.md | [PLAN.md](PLAN.md) |
| 3 | SPEC_PROCESS.md | [SPEC_PROCESS.md](SPEC_PROCESS.md) |
| 4 | README.md | [README.md](README.md) |
| 5 | AGENT_LOG.md | [AGENT_LOG.md](AGENT_LOG.md) |
| 6 | REFLECTION.md | [REFLECTION.md](REFLECTION.md) |
| 7 | 源代码 | [src/ai4se_agent/](src/ai4se_agent/) |
| 8 | 测试 | [tests/](tests/) — 246 tests, `pytest tests/ -v` |
| 9 | 机制演示 | [demo/mechanism_demo.py](demo/mechanism_demo.py) — `python demo/mechanism_demo.py` |
| 10 | CI 配置 | [.github/workflows/ci.yml](.github/workflows/ci.yml) + [.gitlab-ci.yml](.gitlab-ci.yml) |
| 11 | 分发 (PyPI) | `pip install ai4se-agent` 或下载 [release wheel](https://github.com/yae0627/AI4SE_Coding_Agent_Harness/releases/tag/v0.1.0) |
| 12 | 构建产物 | Release 包含 `.tar.gz` + `.whl` |

---

## 快速验证

```bash
# 安装
pip install ai4se-agent

# 配置 API Key
export OPENAI_API_KEY="sk-..."
ai4se-agent --setup

# 运行
ai4se-agent "write a hello world program"

# 测试
git clone https://github.com/yae0627/AI4SE_Coding_Agent_Harness.git
cd AI4SE_Coding_Agent_Harness/projects
pip install -e ".[dev]"
pytest tests/ -v                     # 246 tests

# 机制演示
python demo/mechanism_demo.py        # 5 demos

# CI 状态
# https://github.com/yae0627/AI4SE_Coding_Agent_Harness/actions
```

---

## 项目数据

| 指标 | 数值 |
|------|------|
| 测试数量 | 246 |
| Commit 数量 | 122 |
| 源码模块 | 12 (cli/config/context/core/feedback/guardrails/llm/memory/observability/sanitizer/session/tools) |
| 状态机状态 | 12 |
| 工具数量 | 5 |
| 护栏策略 | 4 |
| Prompt Section | 7 |
| 事件类型 | 14 |
| 重点维度 | 反馈闭环 (Feedback Loop) |

---

## 备注

- 无 WebUI，仅 CLI，通过 GitHub Release 分发
- API Key 通过 `.env` 或 `~/.config/ai4se/config.toml` 配置，不提交 Git
- Mock LLM 适配器支持脱离真实 API 的确定性单元测试
