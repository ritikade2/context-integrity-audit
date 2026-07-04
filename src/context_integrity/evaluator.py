"""
Evaluator: runs all 7 audit modules on one interaction row and returns
a final IntegrityScore. Also provides evaluate_file() to score an entire
CSV scenario file and return a summary.
"""

import csv
from src.context_integrity.scoring import score_components, IntegrityScore
from src.context_integrity.contract import default_contract
from src.context_integrity.modules.context_staleness import audit as stale_audit
from src.context_integrity.modules.retrieval_boundary import audit as boundary_audit
from src.context_integrity.modules.grounding_fidelity import audit as grounding_audit
from src.context_integrity.modules.lineage_traceability import audit as lineage_audit
from src.context_integrity.modules.schema_consistency import audit as schema_audit
from src.context_integrity.modules.reproducibility import audit as repro_audit
from src.context_integrity.modules.policy_alignment import audit as policy_audit


def evaluate_row(row: dict, contract: dict = None) -> IntegrityScore:
    """
    Run all 7 audit modules on one interaction row and return an IntegrityScore.
    row: one dictionary representing one agent interaction.
    contract: optional custom weights dict. Uses default if not provided.
    """
    if contract is None:
        contract = default_contract()

    # Run retrieval_boundary first — it returns a (Component, bool) tuple
    boundary_component, force_block = boundary_audit(row)

    # Run the remaining 6 modules — each returns a single Component
    staleness_component = stale_audit(row)
    grounding_component = grounding_audit(row)
    lineage_component = lineage_audit(row)
    schema_component = schema_audit(row)
    repro_component = repro_audit(row)
    policy_component = policy_audit(row)

    # Collect all 7 components in contract weight order
    components = [
        staleness_component,
        boundary_component,
        grounding_component,
        lineage_component,
        schema_component,
        repro_component,
        policy_component,
    ]

    return score_components(
        components,
        forced_block=force_block,
    )


def evaluate_file(path: str) -> dict:
    """
    Score every row in a CSV scenario file and return a summary.
    path: path to a scenario CSV file in data/synthetic_logs/
    Returns a dict with average score, verdict counts, and blocked count.
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
            result = evaluate_row(row)
            scores.append(result.score)
            verdict_counts[result.verdict.value] += 1

    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    return {
        "total_rows": len(scores),
        "average_score": avg_score,
        "verdict_counts": verdict_counts,
        "blocked_count": verdict_counts["BLOCKED"],
    }