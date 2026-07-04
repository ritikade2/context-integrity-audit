"""
Audit Dimension 6: Reproducibility Under Fixed Context

Checks whether the agent is likely to produce consistent output when
given the same retrieved context. Uses output_matches_source as a proxy:
high source alignment = deterministic and reproducible.
Low alignment = agent is adding its own interpretation = outputs may vary.

Penalty is scaled but capped lower than grounding_fidelity because
reproducibility risk is less severe than outright hallucination.
"""

from src.context_integrity.scoring import Component

WEIGHT = 0.10

def audit(row: dict) -> Component:
    """
    Compute the deproducibility penalty for one interaction row.
    row: one dictionary from the CSV, representing one agent interaction.
    Returns a Component with the panelty and a short explanation.
    """
    raw = row.get("output_matches_source", None)

    try:
        match_score = float(raw)
    except (ValueError, TypeError):
        return Component(
            name="reproducibility",
            weight=WEIGHT,
            penalty=0.3,
            detail="output_matches_source missing, reproducibility not measured",
        )
    match_score = max(0.0, min(1.0, match_score))
    
    #scale penalty but cap at 0.8. Because reproducibility is a risk but less severe
    raw_penalty = 1.0 - match_score
    penalty = round(min(raw_penalty, 0.8), 4)

    if penalty <= 0.1:
        detail = f"likely reproducible (match score {match_score:.2f})"
    elif penalty <= 0.4:
        detail = f"moderate reproducibility risk (match score {match_score:.2f})"
    else:
        detail = f"high reproducibility risk (match score {match_score:.2f})"
    
    return Component(
        name="reproducibility",
        weight=WEIGHT,
        penalty=penalty,
        detail=detail,
    )