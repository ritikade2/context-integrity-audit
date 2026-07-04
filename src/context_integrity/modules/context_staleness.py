"""
Audit Dimension 1: Context Staleness

Checks whether the information the agent retrieved was current at the time
of the interaction. A source validated within 2 days is considered fresh.
Penalty increases linearly between 2 and 7 days, and maxes out at 7+ days.
"""

from datetime import datetime
from context_integrity.scoring import Component

FRESHNESS_THRESHOLD_DAYS = 2.0
MAX_STALENESS_DAYS = 7.0
WEIGHT = 0.20
REFERENCE_DATE = datetime(2026, 6, 21, 12, 0, 0)


def audit(row: dict, now: datetime = None) -> Component:
    """
    Compute the staleness penalty for one interaction row.
    row: one dictionary from the CSV, representing one agent interaction.
    now: reference datetime to measure staleness against. Defaults to
         datetime.now() for real-world use. Pass REFERENCE_DATE when
         scoring synthetic demo data so results stay reproducible.
    Returns a Component with the penalty and a short explanation.
    """
    if now is None:
        now = datetime.now()

    raw = row.get("source_last_validated", "")

    try:
        validated_at = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return Component(
            name="context_staleness",
            weight=WEIGHT,
            penalty=1.0,
            detail="source_last_validated missing or unparseable",
        )

    age_days = (now - validated_at).total_seconds() / 86400.0

    # Future-dated sources score as fresh rather than negative age
    if age_days < 0:
        return Component(
            name="context_staleness",
            weight=WEIGHT,
            penalty=0.0,
            detail=f"source dated in the future ({abs(age_days):.1f} days ahead), treated as fresh",
        )

    if age_days <= FRESHNESS_THRESHOLD_DAYS:
        penalty = 0.0
        detail = f"fresh ({age_days:.1f} days old)"
    elif age_days >= MAX_STALENESS_DAYS:
        penalty = 1.0
        detail = f"maximally stale ({age_days:.1f} days old, threshold {MAX_STALENESS_DAYS} days)"
    else:
        penalty = (age_days - FRESHNESS_THRESHOLD_DAYS) / (MAX_STALENESS_DAYS - FRESHNESS_THRESHOLD_DAYS)
        penalty = round(penalty, 4)
        detail = f"stale ({age_days:.1f} days old)"

    return Component(
        name="context_staleness",
        weight=WEIGHT,
        penalty=penalty,
        detail=detail,
    )