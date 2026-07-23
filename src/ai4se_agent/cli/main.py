import argparse
import datetime
import sys

from ai4se_agent.cli.renderer import TerminalRenderer
from ai4se_agent.cli.session import SessionManager
from ai4se_agent.config.loader import ConfigLoader
from ai4se_agent.config.wizard import run_setup_wizard
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
    parser.add_argument(
        "--setup", action="store_true", help="Run first-time setup wizard"
    )
    args = parser.parse_args()

    if args.setup:
        config = ConfigLoader()
        run_setup_wizard(config)
        return

    config = ConfigLoader()
    config.load()

    # Non-interactive: no config and no API key → prompt to run setup
    if not args.task and not config.get("provider", "api_key"):
        if sys.stdin.isatty():
            print("No configuration found. Running setup wizard...\n")
            run_setup_wizard(config)
            print("Setup complete. Starting interactive session...\n")
        else:
            print("No configuration found.")
            print("Please run: ai4se-agent --setup")
            print("Or set OPENAI_API_KEY environment variable.")
            return

    renderer = TerminalRenderer(verbose=args.verbose)
    tracer = Tracer() if args.trace else NullTracer()
    session = SessionManager(config=config, renderer=renderer, tracer=tracer)

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
