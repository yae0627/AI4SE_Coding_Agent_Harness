# PyForge

A **Coding Agent Harness** — an engineering system that wraps an LLM into a reliable, feedback-driven coding agent. Built with Python.

## 项目状态

🚧 初期搭建中 —— 见 `docs/superpowers/specs/` 获取设计文档。

## 快速开始

```bash
# 安装
pip install pyforge

# 运行
pyforge run
```

## 目录结构

```
src/pyforge/
├── core/        # Agent 主循环
├── tools/       # 工具系统（文件读写、shell 等）
├── feedback/    # 反馈闭环（重点维度）
├── guardrails/  # 安全护栏
├── memory/      # 记忆系统
└── config/      # 配置管理
```

## 安全边界

凭据通过操作系统钥匙串或加密文件存储，绝不硬编码进源码。

## 分发

- PyPI: `pip install pyforge`
- [更多文档](docs/)