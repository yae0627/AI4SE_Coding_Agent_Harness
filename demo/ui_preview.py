"""Terminal UI demo — single input loop, no nested polling, native scroll.
python demo/ui_preview.py
"""
import shutil
import threading
import time

C = {
    "reset": "\033[0m", "dim": "\033[2m",
    "green": "\033[32m", "red": "\033[31m",
    "yellow": "\033[33m", "blue": "\033[34m",
    "white_b": "\033[1;37m",
}

def _c(color, text):
    return f"{C.get(color, '')}{text}{C['reset']}"

def p(line=""):
    w = shutil.get_terminal_size().columns
    print(line[:w - 1], flush=True)

# ── Shared state ───────────────────────────────────────────────
stop_flag = threading.Event()
approval: list[str] = []
running = False
turn = 0

def agent_loop(task: str):
    global turn, running
    turn += 1
    stop_flag.clear()

    time.sleep(0.4)
    if stop_flag.is_set(): running = False; return
    p(_c("blue", f"  Received task #{turn}: {task[:50]}"))
    time.sleep(0.2)
    if stop_flag.is_set(): running = False; return
    p(_c("dim", f"  read_file  README.md".ljust(50)) + _c("green", " 0.1s ok"))
    time.sleep(0.3)
    if stop_flag.is_set(): running = False; return
    p(_c("blue", "  This is a simulated agent response."))
    time.sleep(0.2)
    if stop_flag.is_set(): running = False; return
    p(_c("dim", f"  shell  pytest tests/ -q".ljust(50)) + _c("green", " 1.2s ok"))

    if turn % 3 == 0:
        bar = "-" * min(shutil.get_terminal_size().columns - 4, 56)
        p(_c("yellow", f"  {bar}"))
        p(_c("yellow", "  ") + _c("white_b", "APPROVAL REQUIRED"))
        p()
        p("    Policy:  GitPolicy")
        p("    Action:  git push origin main")
        p("    Risk:    push to remote, irreversible")
        p()
        p(_c("yellow", "  /approve to confirm") + "  |  " + _c("yellow", "/reject to deny"))
        p(_c("yellow", f"  {bar}"))
        p()
        while not stop_flag.is_set():
            if approval:
                resp = approval.pop(0)
                p(_c("green", "  approved") if resp == "approve" else _c("red", "  rejected"))
                break
            time.sleep(0.1)
        if stop_flag.is_set():
            running = False
            return

    p(_c("dim", "  stop: success | 3 iters | 1.5s"))
    p()
    running = False

# ── Banner ─────────────────────────────────────────────────────
p()
p(_c("blue", "  ai4se-agent") + _c("dim", "  interactive test"))
p()

# ── Main loop ──────────────────────────────────────────────────
agent_thread: threading.Thread | None = None

while True:
    try:
        line = input().strip()
    except (EOFError, KeyboardInterrupt):
        if running:
            stop_flag.set()
        print()
        break

    # Clean up finished agent thread
    if agent_thread and not agent_thread.is_alive():
        agent_thread.join()
        agent_thread = None
        running = False

    # Agent running → interpret input as command
    if running:
        if line == "/stop":
            stop_flag.set()
            if agent_thread:
                agent_thread.join(timeout=1)
                agent_thread = None
            running = False
            p(_c("red", "  interrupted"))
            p()
        elif line == "/approve":
            approval.append("approve")
        elif line == "/reject":
            approval.append("reject")
        elif line in ("exit", "quit"):
            stop_flag.set()
            break
        elif line:
            p(_c("dim", "  Agent is running. /stop /approve /reject"))
        continue

    # Agent idle → new task
    if not line:
        continue
    if line in ("exit", "quit"):
        break

    p()  # blank line between user input and agent output
    running = True
    approval.clear()
    stop_flag.clear()
    agent_thread = threading.Thread(target=agent_loop, args=(line,), daemon=True)
    agent_thread.start()

p()
p(_c("dim", "Session ended."))
