"""
Remediation recommendations for each audit dimension.

Takes an IntegrityScore and returns a list of specific, actionable
fix recommendations for any dimension with a non-zero penalty.
"""

from src.context_integrity.scoring import IntegrityScore


REMEDIATION_MAP = {
    "context_staleness": {
        "low":  "Schedule more frequent source validation. Current refresh "
                "cycle exceeds the 2-day freshness threshold.",
        "high": "Immediately re-sync the source. Agent is operating on "
                "significantly stale context that may produce incorrect outputs.",
    },
    "retrieval_boundary": {
        "low":  "Review agent access configuration. Agent retrieved data "
                "above its authorized classification level.",
        "high": "CRITICAL: Revoke agent access and audit all outputs from "
                "this session. PII data was accessed without authorization.",
    },
    "grounding_fidelity": {
        "low":  "Review agent output for unsupported claims. Output diverges "
                "moderately from retrieved source material.",
        "high": "Do not use this output. Agent output has significant "
                "grounding gaps — claims are not supported by retrieved context.",
    },
    "lineage_traceability": {
        "low":  "Reconstruct lineage documentation before using this output "
                "in any governed reporting or audit context.",
        "high": "Output cannot be used for compliance or audit purposes "
                "until full lineage is documented and verified.",
    },
    "schema_consistency": {
        "low":  "Update agent schema cache to current production version. "
                "Agent is operating on an outdated schema definition.",
        "high": "Halt agent queries until schema is synchronized. Mismatch "
                "between agent schema and production schema will produce "
                "incorrect field mappings and query results.",
    },
    "reproducibility": {
        "low":  "Review agent temperature and sampling settings to reduce "
                "output variance for governed reporting use cases.",
        "high": "Do not use this output in auditable or regulated reporting. "
                "High output variance makes results non-reproducible.",
    },
    "policy_alignment": {
        "low":  "Verify masking configuration for this data classification "
                "level and reprocess the output with masking applied.",
        "high": "VIOLATION: Output contains unmasked sensitive data. "
                "Quarantine output immediately and apply required masking "
                "before any distribution.",
    },
}


def get_recommendations(result: IntegrityScore) -> list[str]:
    """
    Return a list of remediation recommendations for a scored interaction.
    Only dimensions with penalty > 0.05 generate a recommendation.
    Penalty above 0.4 triggers the high-severity recommendation.
    """
    recommendations = []

    for component in result.components:
        if component.penalty <= 0.05:
            continue

        map_entry = REMEDIATION_MAP.get(component.name)
        if not map_entry:
            continue

        if component.penalty > 0.4:
            rec = f"[{component.name.upper()}] {map_entry['high']}"
        else:
            rec = f"[{component.name.upper()}] {map_entry['low']}"

        recommendations.append(rec)

    if not recommendations:
        recommendations.append("No remediation required. All dimensions within acceptable thresholds.")

    return recommendations