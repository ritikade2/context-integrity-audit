"""
Command-line interfrace for the Context Integrity Audit Framework
Usage:
    python3 -m context_integrity demo
    python3 -m context_integrity run <path_to_csv>
    python3 -m context_integrity check
"""

import argparse
import os
import sys

from context_integrity.evaluator import evaluate_file, evaluate_row
from context_integrity.remediation import get_recommendations


DEMO_SCENARIOS = [
    "baseline",
    "context_drift",
    "mixed_failure",
    "severe",
]

def _demo(_args) -> int:
    """Run all 4 synthetic scenarios and print a summary table."""
    base_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "synthetic_logs"
    )

    print("Context Integrity Audit Framework - scenario demo")
    print("=" * 60)
    print(f"{'scenario':<20} {'avg score':>10} {'compliant':>10} {'review':>10} {'non-compliant':>14} {'blocked':>8}")
    print("-" * 60)

    for name in DEMO_SCENARIOS:
        path = os.path.join(base_dir, f"scenario_{name}.csv")
        if not os.path.exists(path):
            print(f"{name:<20}  file not found: {path}", file=sys.stderr)
            continue
        result = evaluate_file(path)
        vc = result["verdict_counts"]
        print(
            f"{name:<20} {result['average_score']:>10.1f} "
            f"{vc['COMPLIANT']:>10} {vc['REVIEW_REQUIRED']:>10} "
            f"{vc['NON_COMPLIANT']:>14} {vc['BLOCKED']:>8}"
        )
    print("=" * 60)
    return 0

def _run(args) -> int:
    """Score all rows in a CSV file and print a summary."""
    if not os.path.exists(args.path):
        print(f"error: file not found: {args.path}", file=sys.stderr)
        return 2

    result = evaluate_file(args.path)
    vc = result["verdict_counts"]
    print(f"file: {args.path}")
    print(f"total_rows: {result['total_rows']}")
    print(f"verdicts: COMPLIANT={vc['COMPLIANT']} REVIEW_REQUIRED={vc['REVIEW_REQUIRED']} "
          f"NON_COMPLIANT={vc['NON_COMPLIANT']} BLOCKED={vc['BLOCKED']}")
    return 0

def _check(_args) -> int:
    """Score one hardcoded example interaction and show full report + remediation."""
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

    result = evaluate_row(row)
    print(result.report())
    print()
    print("Remediation recommendations:")
    for rec in get_recommendations(result):
        print(f" {rec}")
    return 0

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Context Integrity Audit Framework for enterprise AI agents.",
    )

    sub = parser.add_subparsers(dest="command")

    demo = sub.add_parser("demo", help="run all 4 synthetic scenarios")
    demo.set_defaults(func=_demo)

    run = sub.add_parser("run", help="score a CSV file")
    run.add_argument("path", help="path to a scenario CSV file")
    run.set_defaults(func=_run)

    check = sub.add_parser("check", help="score one example interaction")
    check.set_defaults(func=_check)

    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())