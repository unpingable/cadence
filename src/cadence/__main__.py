"""CLI entry point: python -m cadence lint <path>"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cadence.contract import load_contracts
from cadence.lint import lint, load_query_specs, Severity
from cadence.receipt import emit_receipt


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cadence",
        description="Temporal admissibility checker for data analytics",
    )
    sub = parser.add_subparsers(dest="command")

    lint_parser = sub.add_parser("lint", help="Check queries against temporal contracts")
    lint_parser.add_argument("path", type=Path, help="Directory with contracts and query specs")
    lint_parser.add_argument("--receipt", action="store_true", help="Emit receipts as JSON")

    args = parser.parse_args()

    if args.command != "lint":
        parser.print_help()
        return 1

    path = args.path
    if not path.is_dir():
        print(f"Error: {path} is not a directory", file=sys.stderr)
        return 1

    contracts = load_contracts(path)
    contract_map = {c.name: c for c in contracts}

    specs = load_query_specs(path)
    if not specs:
        print(f"No query specs (*.query.json) found in {path}", file=sys.stderr)
        return 1

    exit_code = 0
    for spec in specs:
        violations = lint(spec, contract_map)
        has_errors = any(v.severity == Severity.ERROR for v in violations)

        if violations:
            print(f"\n--- {spec.name} ---")
            for v in violations:
                marker = "E" if v.severity == Severity.ERROR else "W" if v.severity == Severity.WARNING else "I"
                print(f"  [{marker}] {v.rule}: {v.message}")

        if args.receipt:
            resolved = [contract_map[s] for s in spec.sources if s in contract_map]
            receipt = emit_receipt(spec.name, resolved, violations)
            print(f"\n{receipt.to_json()}")

        if has_errors:
            exit_code = 1

    if exit_code == 0 and not any(lint(s, contract_map) for s in specs):
        print("All queries temporally admissible.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
