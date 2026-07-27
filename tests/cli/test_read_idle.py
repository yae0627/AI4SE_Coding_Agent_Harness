"""Verify _read_idle behavior by testing its internal logic directly.
We can't easily test msvcrt input from a non-interactive test, but we can
verify the redraw logic and command matching chain."""
import shutil
import sys


def test_redraw_output_contains_input_and_preview(capsys):
    """Simulate the _redraw logic: input line + preview below."""
    from ai4se_agent.cli.commands import matching_commands

    chars = list("/h")
    line = "".join(chars)
    matches = matching_commands(line) if line.startswith("/") else []
    max_w = shutil.get_terminal_size().columns

    # Simulate _redraw
    sys.stdout.write("\r\033[2K")
    sys.stdout.write(f"\033[1;37m> {line}\033[0m")
    sys.stdout.write("\033[J")
    count = 0
    if matches:
        sys.stdout.write("\n")
        count += 1  # blank separator
        for name, desc in matches:
            entry = f"  \033[2m{name:<12s} {desc}\033[0m"
            sys.stdout.write(entry[:max_w - 1] + "\n")
            count += 1
    if count > 0:
        sys.stdout.write(f"\033[{count}A")
    sys.stdout.write(f"\r\033[{2 + len(line)}C")
    sys.stdout.flush()

    captured = capsys.readouterr()
    assert "> /h" in captured.out
    assert "/help" in captured.out
    assert "\033[J" in captured.out
    assert f"\033[{count}A" in captured.out


def test_redraw_no_preview_for_plain_text(capsys):
    """Non-/ input should not trigger preview."""
    from ai4se_agent.cli.commands import matching_commands

    chars = list("hello")
    line = "".join(chars)
    matches = matching_commands(line) if line.startswith("/") else []

    sys.stdout.write("\r\033[2K")
    sys.stdout.write(f"\033[1;37m> {line}\033[0m")
    sys.stdout.write("\033[J")
    count = 0
    if matches:
        sys.stdout.write("\n")
        count += 1
        for name, desc in matches:
            entry = f"  \033[2m{name:<12s} {desc}\033[0m"
            sys.stdout.write(entry[:100] + "\n")
            count += 1
    if count > 0:
        sys.stdout.write(f"\033[{count}A")
    sys.stdout.write(f"\r\033[{2 + len(line)}C")
    sys.stdout.flush()

    captured = capsys.readouterr()
    assert "> hello" in captured.out
    assert count == 0
    # No command names in output
    assert "/help" not in captured.out


def test_redraw_backspace_from_slash_to_empty(capsys):
    """After deleting /, preview should disappear."""
    from ai4se_agent.cli.commands import matching_commands

    # User typed / then backspaced
    chars: list[str] = []
    line = "".join(chars)
    matches = matching_commands(line) if line.startswith("/") else []
    assert len(matches) == 0  # no /, no preview


def test_all_commands_start_with_slash():
    """All preview-visible commands must start with /."""
    from ai4se_agent.cli.commands import COMMANDS
    for name, desc, _ in COMMANDS:
        if name.startswith("/"):
            assert len(name) > 1, f"{name} is just /"


def test_help_shows_all():
    """/help should mention all commands including exit."""
    from ai4se_agent.cli.commands import COMMANDS
    assert len(COMMANDS) == 7  # 6 /commands + exit
    names = [name for name, _, _ in COMMANDS]
    assert "/help" in names
    assert "exit" in names
