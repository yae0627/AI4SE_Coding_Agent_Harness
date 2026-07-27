"""Terminal UI: alternate screen, fixed input, scrollable output area.

Uses OutputBuffer + Viewport for state. ANSI escape codes for rendering.
Character-by-character input via msvcrt (Windows) or tty (Unix).
"""
import shutil
import sys
import os

from ai4se_agent.cli.output_buffer import OutputBuffer
from ai4se_agent.cli.viewport import Viewport

# ── ANSI constants ──────────────────────────────────────────────
_ALT_ENTER = "\033[?1049h"
_ALT_LEAVE = "\033[?1049l"
_CLEAR = "\033[2J"
_CLEAR_LINE = "\033[2K"
_HOME = "\033[H"

_RESET = "\033[0m"
_DIM = "\033[2m"
_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_WHITE_B = "\033[1;37m"
_BG_GRAY = "\033[100m"


def _c(code, text):
    return f"{code}{text}{_RESET}"

def _cursor(row, col=0):
    return f"\033[{row};{col}H"

# ── Key constants ───────────────────────────────────────────────
KEY_ENTER = "\r"
KEY_CTRL_C = "\x03"
KEY_BACKSPACE = "\x08"
KEY_ESC = "\x1b"
# Windows arrow/page key prefix
KEY_PREFIX = "\xe0"
KEY_PAGEUP = "I"
KEY_PAGEDOWN = "Q"
KEY_UP = "H"
KEY_DOWN = "P"
KEY_END = "O"


class TerminalUI:
    """Alternate-screen terminal UI with fixed bottom input.

    Layout (height = terminal lines, from bottom up):
        line  H    : guidance
        line  H-1  : blank
        line  H-2  : bottom separator
        line  H-3  : input (wraps to H-4 if long)
        line  H-4  : top separator
        lines 1..H-5: output viewport

    Attributes:
        buffer: OutputBuffer — all output lines
        viewport: Viewport — scroll state
        running: bool — whether agent is executing (affects auto-follow)
    """

    INPUT_HEIGHT = 4  # top sep + input + wrap + guidance

    def __init__(self):
        self.width = shutil.get_terminal_size().columns
        self.height = shutil.get_terminal_size().lines
        self.buffer = OutputBuffer()
        self.viewport = Viewport(height=self._output_height())
        self.running = False
        self._dirty = True

    # ── Screen lifecycle ────────────────────────────────────────
    def enter(self):
        sys.stdout.write(_ALT_ENTER)
        sys.stdout.flush()

    def leave(self):
        sys.stdout.write(_ALT_LEAVE)
        sys.stdout.flush()

    def _output_height(self):
        h = self.height - self.INPUT_HEIGHT
        return max(1, h)

    def _refresh_size(self):
        self.width = shutil.get_terminal_size().columns
        self.height = shutil.get_terminal_size().lines
        self.viewport.height = self._output_height()

    def write_line(self, text: str):
        """Thread-safe: append a line and redraw if auto-following."""
        self.buffer.append(text)
        if self.viewport.follow_mode:
            self._redraw()

    # ── Rendering ───────────────────────────────────────────────
    def _redraw(self):
        self._refresh_size()
        out_h = self._output_height()
        bar_w = self.width - 2
        sep = _c(_BLUE, "-" * bar_w)
        guidance = _c(_DIM, "  PgUp/PgDn scroll  |  Ctrl+C exit")

        start, end = self.viewport.visible_range(len(self.buffer))
        visible = self.buffer.get_all()[start:end]

        lines: list[str] = []
        # Output area
        for i, line in enumerate(visible):
            lines.append(_cursor(i + 1) + _CLEAR_LINE + line[:self.width - 1])
        for i in range(len(visible), out_h):
            lines.append(_cursor(i + 1) + _CLEAR_LINE)

        # Top separator (out_h + 1)
        lines.append(_cursor(out_h + 1) + _CLEAR_LINE + " " + sep[:bar_w])

        # Input area (out_h + 2, out_h + 3)
        lines.append(_cursor(out_h + 2) + _CLEAR_LINE)
        lines.append(_cursor(out_h + 3) + _CLEAR_LINE)

        # Guidance (out_h + 4 = H)
        lines.append(_cursor(out_h + 4) + _CLEAR_LINE + guidance[:self.width - 1])

        sys.stdout.write("".join(lines))
        sys.stdout.flush()

    def _draw_input(self, text: str):
        """Draw prompt + typed text. Wraps to second line if needed."""
        out_h = self._output_height()
        prompt = _c(_BLUE, "> ")
        max_w = self.width - 2
        full = prompt + text

        if len(full) <= max_w:
            sys.stdout.write(_cursor(out_h + 2) + _CLEAR_LINE + " " + full[:max_w])
            sys.stdout.write(_cursor(out_h + 3) + _CLEAR_LINE)
        else:
            line1 = full[:max_w]
            line2 = "   " + full[max_w:max_w * 2 - 3]
            sys.stdout.write(_cursor(out_h + 2) + _CLEAR_LINE + " " + line1[:max_w])
            sys.stdout.write(_cursor(out_h + 3) + _CLEAR_LINE + line2[:max_w])
        sys.stdout.flush()

    # ── Input ───────────────────────────────────────────────────
    def read_input(self) -> str | None:
        """Read user input character by character. Returns the submitted
        string, or None on Ctrl+C / exit. Handles PageUp/Down for scrolling."""
        chars: list[str] = []
        self._draw_input("")

        while True:
            ch = self._getch()
            if ch is None:
                return None

            if ch == KEY_CTRL_C:
                return None

            if ch in (KEY_ENTER, "\n"):
                self._draw_input("")
                return "".join(chars)

            if ch == KEY_BACKSPACE:
                if chars:
                    chars.pop()
                self._draw_input("".join(chars))

            elif ch == KEY_PREFIX:
                ch2 = self._getch()
                if ch2 is None:
                    continue
                if ch2 == KEY_PAGEUP:
                    self.viewport.scroll_up(5)
                    self._redraw()
                    self._draw_input("".join(chars))
                elif ch2 == KEY_PAGEDOWN:
                    self.viewport.scroll_down(5)
                    self._redraw()
                    self._draw_input("".join(chars))
                elif ch2 == KEY_END:
                    self.viewport.reset()
                    self._redraw()
                    self._draw_input("".join(chars))

            elif ch == KEY_ESC:
                # Discard escape sequences we don't handle
                pass

            elif ch.isprintable():
                chars.append(ch)
                self._draw_input("".join(chars))

    def _getch(self) -> str | None:
        """Read a single character. Returns None on EOF."""
        try:
            import msvcrt
            return msvcrt.getwch()
        except ImportError:
            import tty
            import termios
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                return sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

    # ── Convenience ─────────────────────────────────────────────
    def echo_user(self, text: str):
        """Append user input styled as gray-bg white text."""
        self.write_line(_c(_BG_GRAY, _c(_WHITE_B, f"> {text}")))

    def tool_ok(self, tool: str, params: str, elapsed: float):
        self.write_line(
            _c(_DIM, f"  {tool}  {params}".ljust(50))
            + _c(_GREEN, f" {elapsed:.1f}s ok")
        )

    def tool_fail(self, tool: str, params: str, elapsed: float):
        self.write_line(
            _c(_DIM, f"  {tool}  {params}".ljust(50))
            + _c(_RED, f" {elapsed:.1f}s FAIL")
        )

    def respond(self, message: str):
        for line in message.splitlines():
            self.write_line(f"  {line}")

    def hitl_show(self, policy: str, action: str, reason: str):
        bar = "-" * min(self.width - 4, 56)
        self.write_line(_c(_YELLOW, f"  {bar}"))
        self.write_line(_c(_YELLOW, "  ") + _c(_WHITE_B, "APPROVAL REQUIRED"))
        self.write_line("")
        self.write_line(f"    Policy:  {policy}")
        self.write_line(f"    Action:  {action}")
        self.write_line(f"    Risk:    {reason}")
        self.write_line("")
        self.write_line(_c(_YELLOW, "  /approve to confirm") + "  |  " + _c(_YELLOW, "/reject to deny"))
        self.write_line(_c(_YELLOW, f"  {bar}"))

    def stop_summary(self, reason: str, iterations: int):
        self.write_line(_c(_DIM, f"  stop: {reason} | {iterations} iters"))
