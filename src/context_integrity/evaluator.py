"""
Evaluator: runs all 7 audit modules on one interaction row and returns
a final IntegrityScore. Also provides evaluate_file() to score an entire
CSV scenario file and return a summary.

Custom checks can be passed to evaluate_row() and evaluate_file() via the
extra_checks parameter. Each custom check must inherit from BaseCheck and
implement name, default_weight, and audit().
"""

import csv
from datetime import datetime
from dataclasses import replace
from context_integrity.scoring import score_components, IntegrityScore
from context_integrity.contract import default_contract
from context_integrity.base import BaseCheck
from context_integrity.modules.context_staleness import audit as stale_audit
from context_integrity.modules.retrieval_boundary import audit as boundary_audit
from context_integrity.modules.grounding_fidelity import audit as grounding_audit
from context_integrity.modules.lineage_traceability import audit as lineage_audit
from context_integrity.modules.schema_consistency import audit as schema_audit
from context_integrity.modules.reproducibility import audit as repro_audit
from context_integrity.modules.policy_alignment import audit as policy_audit


def evaluate_row(
    row: dict,
    contract: dict = None,
    now: datetime = None,
    extra_checks: list = None,
) -> IntegrityScore:
    """
    Run all audit modules on one interaction row and return an IntegrityScore.
    row: one dictionary representing one agent interaction.
    contract: optional custom weights dict. Uses default if not provided.
    now: optional reference datetime for staleness. Defaults to datetime.now().
    extra_checks: optional list of BaseCheck instances to run alongside the
        default 7 dimensions. Each extra check's weight is taken from its
        default_weight property. Weights across all checks must sum to 1.0
        after normalization — if extra checks are added, the contract weights
        are scaled down proportionally to make room.
    """
    if contract is None:
        contract = default_contract()

    boundary_component, force_block = boundary_audit(row)
    staleness_component = stale_audit(row, now=now)
    grounding_component = grounding_audit(row)
    lineage_component = lineage_audit(row)
    schema_component = schema_audit(row)
    repro_component = repro_audit(row)
    policy_component = policy_audit(row)

    raw_components = [
        staleness_component,
        boundary_component,
        grounding_component,
        lineage_component,
        schema_component,
        repro_component,
        policy_component,
    ]

    # Apply contract weights to default components
    components = [
        replace(c, weight=contract[c.name]) if c.name in contract else c
        for c in raw_components
    ]

    # Run and append any extra custom checks
    if extra_checks:
        extra_components = []
        for check in extra_checks:
            if not isinstance(check, BaseCheck):
                raise ValueError(
                    f"extra_checks must be BaseCheck instances, got {type(check)}"
                )
            extra_components.append(check.audit(row))

        # Renormalize all weights to sum to 1.0
        total_extra_weight = sum(c.weight for c in extra_components)
        scale_factor = 1.0 - total_extra_weight
        if scale_factor <= 0:
            raise ValueError(
                f"extra_checks weights sum to {total_extra_weight:.4f}, "
                "leaving no room for the default checks. Reduce extra check weights."
            )
        components = [
            replace(c, weight=round(c.weight * scale_factor, 10))
            for c in components
        ]
        components = components + extra_components

    total = sum(c.weight for c in components)
    if abs(total - 1.0) > 1e-6:
        raise ValueError(
            f"weights must sum to 1.0 after applying contract and extra checks, "
            f"got {total:.6f}"
        )

    return score_components(
        components,
        forced_block=force_block,
    )


def evaluate_file(
    path: str,
    now: datetime = None,
    extra_checks: list = None,
) -> dict:
    """
    Score every row in a CSV scenario file and return a summary.
    path: path to a scenario CSV file.
    now: optional reference datetime for staleness.
    extra_checks: optional list of BaseCheck instances to run alongside defaults.
    """
    scores = []
    verdict_counts = {
        "COMPLIANT": 0,
        "REVIEW_REQUIRED": 0,
        "NON_COMPLIANT": 0,
        "BLOCKED": 0,
    }

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            result = evaluate_row(row, now=now, extra_checks=extra_checks)
            scores.append(result.score)
            verdict_counts[result.verdict.value] += 1

    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    return {
        "total_rows": len(scores),
        "average_score": avg_score,
        "verdict_counts": verdict_counts,
        "blocked_count": verdict_counts["BLOCKED"],
    }