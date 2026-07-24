"""Terminal UI preview for Phase 3 — run with: python demo/ui_preview.py

Normal terminal mode: all output scrolls natively, no alternate screen.
"""
import shutil
import time


def main():
    width = shutil.get_terminal_size().columns

    C = {
        "reset":     "\033[0m",
        "bold":      "\033[1m",
        "dim":       "\033[2m",
        "green":     "\033[32m",
        "red":       "\033[31m",
        "yellow":    "\033[33m",
        "cyan":      "\033[36m",
        "blue":      "\033[34m",
        "white_b":   "\033[1;37m",
    }

    def c(color, text):
        return f"{C.get(color, '')}{text}{C['reset']}"

    def p(line=""):
        print(line[:width - 1])

    def sep():
        p(c("blue", "-" * min(width, 120)))

    def prompt():
        return c("blue", "> ")

    # ── Banner ──────────────────────────────────────────────
    p()
    p(c("cyan", "  ai4se-agent") + c("dim", "  v0.2.0"))
    p()
    sep()

    # ── User message ────────────────────────────────────────
    p(c("white_b", "> add token expiry check to auth module"))
    p()

    # ── Agent responds ──────────────────────────────────────
    time.sleep(0.5)
    p("  I will check the current auth module implementation")
    p("  and add token expiry validation to /refresh.")
    p()
    time.sleep(0.3)

    # ── Tool: read_file (success) ───────────────────────────
    p(c("dim", "  read_file  auth.py                  ") + c("green", "0.05s ok"))
    p(c("dim", "    347 bytes | 3 endpoints"))
    p()
    time.sleep(0.2)

    # ── Tool: pytest (success) ──────────────────────────────
    p(c("dim", "  shell      pytest tests/auth/ -q     ") + c("green", "0.8s ok"))
    p(c("dim", "    12 passed"))
    p()
    time.sleep(0.3)

    # ── Agent analysis ──────────────────────────────────────
    p("  auth.py has 3 endpoints: /login, /refresh, /logout.")
    p("  /refresh does not validate token exp field.")
    p("  Adding JWT exp check with 401 on expired tokens.")
    p()
    time.sleep(0.3)

    # ── Tool: pytest (failure) ──────────────────────────────
    p(c("dim", "  shell      pytest tests/auth/ -q     ") + c("red", "2.1s FAIL"))
    p(c("red", "    AssertionError: expected 401, got 200"))
    p(c("red", "    test_refresh_expired_token:42"))
    p()
    p("  Test failed. Line 42 expected 401 but got 200.")
    p("  The expired token is not being rejected.")
    p()
    time.sleep(0.3)

    # ── Tool: edit + retest (success) ───────────────────────
    p(c("dim", "  edit_file  auth.py:55-58             ") + c("green", "0.02s ok"))
    p()
    p(c("dim", "  shell      pytest tests/auth/ -q     ") + c("green", "0.6s ok"))
    p(c("dim", "    15 passed"))
    p()
    p("  All tests pass. Token expiry check is now active")
    p("  on /refresh endpoint.")
    p()
    time.sleep(0.3)

    # ── HITL panel ──────────────────────────────────────────
    p(c("dim", "  shell      git push origin main       ") + c("yellow", "HITL"))
    p()

    bar_w = min(width - 4, 56)
    bar = "-" * bar_w
    p(c("yellow", f"  {bar}"))
    p(c("yellow", "  ") + c("white_b", "APPROVAL REQUIRED"))
    p()
    p("    Policy:  GitPolicy")
    p("    Action:  git push origin main")
    p("    Risk:    push to remote, irreversible")
    p()
    p(c("yellow", "  /approve to confirm") + "  |  " + c("yellow", "/reject to deny"))
    p(c("yellow", f"  {bar}"))
    p()

    # ── Input area ──────────────────────────────────────────
    p()
    sep()
    sys_stdin = __import__("sys").stdin
    try:
        input(f"{prompt()}")
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("Preview finished.")
