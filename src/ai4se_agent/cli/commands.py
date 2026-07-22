from typing import Any


def handle_command(line: str, session: Any) -> bool:
    cmd = line.strip().lower()
    if cmd == "/status":
        if session.state is not None:
            print(f"State: {session.state.current_state}")
            print(f"Iteration: {session.state.iteration}")
        else:
            print("No active session")
        return True
    if cmd == "/reset":
        session.state = None
        session._harness = None
        print("Session reset")
        return True
    if cmd == "/verbose":
        if hasattr(session, "_renderer") and hasattr(session._renderer, "_verbose"):
            session._renderer._verbose = not session._renderer._verbose
            print(f"Verbose mode: {'on' if session._renderer._verbose else 'off'}")
        return True
    if cmd in ("exit", "quit"):
        return False
    print(f"Unknown command: {line}")
    return True
