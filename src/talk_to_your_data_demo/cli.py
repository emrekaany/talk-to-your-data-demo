from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from . import __version__
from .service import TalkToYourDataDemo

DEFAULT_QUESTION = "Show monthly revenue by region"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="talk-data-demo",
        description=" ".join(
            (
                "Ask bounded business questions against a fully synthetic,",
                "read-only SQLite dataset.",
            )
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("questions", help="List the supported offline demo questions.")

    demo_parser = subparsers.add_parser("demo", help="Run the default zero-secret demonstration.")
    demo_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    ask_parser = subparsers.add_parser("ask", help="Ask one supported English or Turkish question.")
    ask_parser.add_argument("question")
    ask_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    serve_parser = subparsers.add_parser("serve", help="Start the local-only browser demo.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    return parser


def _print_result(result: object, *, as_json: bool) -> None:
    payload = result.to_dict()  # type: ignore[attr-defined]
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    plan = payload["plan"]
    print(f"Question: {plan['question']}")
    print(f"Plan: {plan['title']}")
    print("\nExact SQL (validated before read-only execution):")
    print(plan["sql"])
    print(f"\nSummary: {payload['summary']}")
    print(f"Rows returned: {len(payload['rows'])}; elapsed: {payload['elapsed_ms']:.3f} ms")

    columns = payload["columns"]
    rows = payload["rows"][:10]
    if rows:
        print("\n" + " | ".join(str(column) for column in columns))
        print("-+-".join("-" * len(str(column)) for column in columns))
        for row in rows:
            print(" | ".join(str(value) for value in row))


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    command = args.command or "demo"
    service = TalkToYourDataDemo()

    if command == "questions":
        for question in service.questions():
            print(f"- {question}")
        return 0
    if command == "serve":
        from .web.server import serve

        serve(host=args.host, port=args.port)
        return 0

    question = DEFAULT_QUESTION if command == "demo" else args.question
    result = service.ask(question)
    _print_result(result, as_json=bool(getattr(args, "json", False)))
    return 0
