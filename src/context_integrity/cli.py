"""
Command-line interface for the Context Integrity Audit Framework.

Usage:
    python3 -m context_integrity.cli demo [--json]
    python3 -m context_integrity.cli run <path_to_csv> [--json]
    python3 -m context_integrity.cli check [--json]

Exit codes:
    0 — all rows COMPLIANT
    1 — one or more rows REVIEW REQUIRED or NON-COMPLIANT
    2 — one or more rows BLOCKED (critical violation)
"""

import argparse
import json
import os
import sys

from context_integrity.evaluator import evaluate_file, evaluate_row
from context_integrity.remediation import get_recommendations
from context_integrity.modules.context_staleness import REFERENCE_DATE


DEMO_SCENARIOS = [
    "baseline",
    "context_drift",
    "mixed_failure",
    "severe",
]


def _exit_code(result: dict) -> int:
    """Return exit code based on verdict counts."""
    if result["blocked_count"] > 0:
        return 2
    vc = result["verdict_counts"]
    if vc["NON_COMPLIANT"] > 0 or vc["REVIEW_REQUIRED"] > 0:
        return 1
    return 0


def _demo(args) -> int:
    base_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "synthetic_logs"
    )

    results = {}
    worst_exit = 0

    for name in DEMO_SCENARIOS:
        path = os.path.join(base_dir, f"scenario_{name}.csv")
        if not os.path.exists(path):
            print(f"error: scenario file not found: {path}", file=sys.stderr)
            continue
        result = evaluate_file(path, now=REFERENCE_DATE)
        results[name] = result
        worst_exit = max(worst_exit, _exit_code(result))

    if args.json:
        print(json.dumps(results, indent=2))
        return worst_exit

    print("Context Integrity Audit Framework - scenario demo")
    print("=" * 60)
    print(f"{'scenario':<20} {'avg score':>10} {'compliant':>10} {'review':>10} {'non-compliant':>14} {'blocked':>8}")
    print("-" * 60)
    for name, result in results.items():
        vc = result["verdict_counts"]
        print(
            f"{name:<20} {result['average_score']:>10.1f} "
            f"{vc['COMPLIANT']:>10} {vc['REVIEW_REQUIRED']:>10} "
            f"{vc['NON_COMPLIANT']:>14} {vc['BLOCKED']:>8}"
        )
    print("=" * 60)
    return worst_exit


def _run(args) -> int:
    if not os.path.exists(args.path):
        print(f"error: file not found: {args.path}", file=sys.stderr)
        return 2

    result = evaluate_file(args.path)
    exit_code = _exit_code(result)

    if args.json:
        print(json.dumps(result, indent=2))
        return exit_code

    vc = result["verdict_counts"]
    print(f"file: {args.path}")
    print(f"total_rows: {result['total_rows']}")
    print(f"average_score: {result['average_score']}")
    print(f"verdicts: COMPLIANT={vc['COMPLIANT']} REVIEW_REQUIRED={vc['REVIEW_REQUIRED']} "
          f"NON_COMPLIANT={vc['NON_COMPLIANT']} BLOCKED={vc['BLOCKED']}")
    return exit_code


def _check(args) -> int:
    row = {
        "source_last_validated": "2026-06-10 12:00:00",
        "source_classification": "PII",
        "agent_access_level": "INTERNAL",
        "output_claims": "Customer John Smith has account balance of $45,231.",
        "retrieved_content": "Account balance data is available for authorized users only.",
        "query": "What is the account balance for customer 8821?",
        "current_schema_version": "v4",
        "agent_schema_version": "v2",
        "lineage_documented": "False",
        "output_matches_source": "0.3",
        "policy_masking_required": "True",
        "policy_masking_applied": "False",
    }

    result = evaluate_row(row, now=REFERENCE_DATE)
    recs = get_recommendations(result)

    if args.json:
        output = result.to_dict()
        output["remediation"] = recs
        print(json.dumps(output, indent=2))
        return 2 if result.verdict.value == "BLOCKED" else 1

    print(result.report())
    print()
    print("Remediation recommendations:")
    for rec in recs:
        print(f"  {rec}")

    return 2 if result.verdict.value == "BLOCKED" else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="context-audit",
        description="Context Integrity Audit Framework for enterprise AI agents.",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="output results as JSON (for CI pipelines and automation)"
    )
    sub = parser.add_subparsers(dest="command")

    demo = sub.add_parser("demo", help="run all 4 synthetic scenarios")
    demo.add_argument("--json", action="store_true", help="output as JSON")
    demo.set_defaults(func=_demo)

    run = sub.add_parser("run", help="score a CSV file")
    run.add_argument("path", help="path to a scenario CSV file")
    run.add_argument("--json", action="store_true", help="output as JSON")
    run.set_defaults(func=_run)

    check = sub.add_parser("check", help="score one example interaction")
    check.add_argument("--json", action="store_true", help="output as JSON")
    check.set_defaults(func=_check)

    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())