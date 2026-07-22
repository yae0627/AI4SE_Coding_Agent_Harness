import argparse
import datetime

from ai4se_agent.cli.renderer import TerminalRenderer
from ai4se_agent.cli.session import SessionManager
from ai4se_agent.observability.tracer import NullTracer, Tracer


def main() -> None:
    parser = argparse.ArgumentParser(description="AI4SE Coding Agent Harness")
    parser.add_argument("task", nargs="*", help="Task description")
    parser.add_argument(
        "--verbose", action="store_true", help="Show detailed output"
    )
    parser.add_argument(
        "--trace", action="store_true", help="Save JSON trace to sessions/"
    )
    args = parser.parse_args()

    renderer = TerminalRenderer(verbose=args.verbose)
    tracer = Tracer() if args.trace else NullTracer()
    session = SessionManager(renderer=renderer, tracer=tracer)

    if args.task:
        session.start()
        task = " ".join(args.task)
        result = session.submit(task)
        print(
            f"Result: {result['status']} ({result['reason']}) "
            f"after {result['iterations']} iterations"
        )
        if args.trace:
            path = (
                f"sessions/session_"
                f"{datetime.datetime.now():%Y%m%d_%H%M%S}.json"
            )
            tracer.save(path)
            print(f"Trace saved: {path}")
    else:
        session.interactive()


if __name__ == "__main__":
    main()
