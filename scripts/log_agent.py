"""
AGENT_LOG.md 自动记录脚本

用法：
  python scripts/log_agent.py <task_tag> <skill> <summary> <intervention>

示例：
  python scripts/log_agent.py "#task-03" "llm-adapter" "Add LLMAdapter abstraction" "-"

自动获取：
  - 当前时间（YYYY-MM-DD HH:mm）
  - 最新 commit hash（截取前 7 位）
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path


LOG_FILE = Path("AGENT_LOG.md")


def get_latest_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            capture_output=True, text=True, encoding="utf-8", check=True
        )
        return result.stdout.strip().split()[0]
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
        return "-"


def append_log(task: str, skill: str, summary: str, intervention: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit = get_latest_commit()
    line = f"| {timestamp} | {task} | {skill} | {summary} | {intervention} | {commit} |\n"

    if not LOG_FILE.exists():
        LOG_FILE.write_text(
            "# AGENT_LOG.md\n\n"
            "> 自动记录，由 scripts/log_agent.py 追加。\n\n"
            "| 时间 | Task | 技能 | 摘要 | 人工干预 | Commit |\n"
            "|------|------|------|------|----------|--------|\n"
        )

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line)

    print(f"[LOG] Appended: {line.strip()}")


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python scripts/log_agent.py <task> <skill> <summary> <intervention>")
        sys.exit(1)

    append_log(
        task=sys.argv[1],
        skill=sys.argv[2],
        summary=sys.argv[3],
        intervention=sys.argv[4],
    )